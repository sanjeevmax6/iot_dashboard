import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.chat import REFUSAL_MESSAGE, classify_intent, narrate_analysis, stream_chat
from agent.schemas import AnalysisOutput
from app.api.deps import get_db
from app.core.config import settings
from app.models.analysis_result import AnalysisResult
from app.services.summarizer import get_machine_summaries

router = APIRouter(prefix="/analysis", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str
    trigger_analysis: bool = False
    requested_count: int | None = None  # None = use settings default; 0 = flexible (no count enforcement)


@router.post("/chat/stream")
async def chat_stream(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Load latest completed analysis for context (may be None)
    record = await db.scalar(
        select(AnalysisResult)
        .where(AnalysisResult.status == "complete")
        .order_by(AnalysisResult.completed_at.desc())
    )
    analysis: AnalysisOutput | None = None
    summaries: list[dict] = []
    if record and record.result_json:
        analysis = AnalysisOutput.model_validate_json(record.result_json)
        summaries = await get_machine_summaries(db)

    async def generate():
        if body.trigger_analysis:
            from agent.graph import run_analysis
            from app.core.database import AsyncSessionLocal
            from app.services.summarizer import get_machine_summaries

            async with AsyncSessionLocal() as analysis_db:
                summaries_fresh = await get_machine_summaries(analysis_db)
                if not summaries_fresh:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'No log data found. Ingest a CSV first.'})}\n\n"
                    return

                # requested_count=None → use settings.top_at_risk_count (default)
                # requested_count=0   → flexible mode, no count enforcement
                # requested_count=N   → enforce exactly N
                if body.requested_count is None:
                    top_n: int | None = settings.top_at_risk_count
                elif body.requested_count == 0:
                    top_n = None
                else:
                    top_n = body.requested_count
                state = await run_analysis(summaries_fresh, top_n=top_n)

                if state["error_state"]:
                    yield f"data: {json.dumps({'type': 'error', 'message': state['error_state']})}\n\n"
                    return

                nonlocal analysis
                analysis = state["parsed_result"]
                if analysis is None:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Analysis returned no structured output.'})}\n\n"
                    return

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

            async for event in narrate_analysis(body.session_id, analysis, summaries_fresh):
                yield f"data: {json.dumps(event)}\n\n"
        else:
            if not await classify_intent(body.message):
                yield f"data: {json.dumps({'type': 'done', 'message': REFUSAL_MESSAGE})}\n\n"
                return
            async for event in stream_chat(body.session_id, body.message, analysis, summaries):
                yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
