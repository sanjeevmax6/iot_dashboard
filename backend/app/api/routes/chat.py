import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.chat import narrate_analysis, stream_chat
from agent.schemas import AnalysisOutput
from app.api.deps import get_db
from app.core.config import settings
from app.models.analysis_result import AnalysisResult

router = APIRouter(prefix="/analysis", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str
    trigger_analysis: bool = False


@router.post("/chat/stream")
async def chat_stream(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Load latest completed analysis for context (may be None)
    record = await db.scalar(
        select(AnalysisResult)
        .where(AnalysisResult.status == "complete")
        .order_by(AnalysisResult.completed_at.desc())
    )
    analysis: AnalysisOutput | None = None
    if record and record.result_json:
        analysis = AnalysisOutput.model_validate_json(record.result_json)

    async def generate():
        if body.trigger_analysis:
            from agent.graph import run_analysis
            from app.core.database import AsyncSessionLocal
            from app.services.summarizer import get_machine_summaries

            async with AsyncSessionLocal() as analysis_db:
                summaries = await get_machine_summaries(analysis_db)
                if not summaries:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'No log data found. Ingest a CSV first.'})}\n\n"
                    return

                state = await run_analysis(summaries)

                if state["error_state"]:
                    yield f"data: {json.dumps({'type': 'error', 'message': state['error_state']})}\n\n"
                    return

                nonlocal analysis
                analysis = state["parsed_result"]

                # Persist to DB so useLatestAnalysis can pick it up
                db_record = AnalysisResult(
                    status="complete",
                    result_json=analysis.model_dump_json(),
                    retry_count=state["retry_count"],
                    model_used=(
                        settings.openai_model
                        if settings.llm_provider == "openai"
                        else settings.bedrock_model_id
                    ),
                    provider=settings.llm_provider,
                    completed_at=datetime.now(timezone.utc),
                )
                analysis_db.add(db_record)
                await analysis_db.commit()

            async for event in narrate_analysis(body.session_id, analysis):
                yield f"data: {json.dumps(event)}\n\n"
        else:
            async for event in stream_chat(body.session_id, body.message, analysis):
                yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
