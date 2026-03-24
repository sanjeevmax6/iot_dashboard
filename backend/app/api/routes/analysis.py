from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.graph import run_analysis
from agent.schemas import AnalysisOutput
from app.api.deps import get_db
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logger import get_logger
from app.models.analysis_result import AnalysisResult
from app.schemas.analysis import AnalysisResultOut, AnalysisRunResponse
from app.services.summarizer import get_machine_summaries

logger = get_logger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


def _serialize(record: AnalysisResult) -> AnalysisResultOut:
    parsed: AnalysisOutput | None = None
    if record.result_json:
        parsed = AnalysisOutput.model_validate_json(record.result_json)

    return AnalysisResultOut(
        id=record.id,
        status=record.status,
        retry_count=record.retry_count,
        model_used=record.model_used,
        provider=record.provider,
        error_message=record.error_message,
        top_at_risk_machines=parsed.top_at_risk_machines if parsed else None,
        fleet_summary=parsed.fleet_summary if parsed else None,
        created_at=record.created_at,
        completed_at=record.completed_at,
    )


async def _run_analysis_task(job_id: int) -> None:
    """Background task: runs entirely in its own DB session."""
    logger.info("Analysis background task is starting, job_id is %d", job_id)
    async with AsyncSessionLocal() as db:
        record = await db.get(AnalysisResult, job_id)
        record.status = "running"
        await db.commit()

        try:
            summaries = await get_machine_summaries(db)
            if not summaries:
                raise ValueError("No log data found. Ingest a CSV before running analysis.")

            logger.info("Running analysis on %d machines, job_id is %d", len(summaries), job_id)
            state = await run_analysis(summaries)

            if state["error_state"]:
                logger.error("Analysis job %d failed, error is %s", job_id, state["error_state"])
                record.status = "error"
                record.error_message = state["error_state"]
            else:
                result: AnalysisOutput = state["parsed_result"]
                record.status = "complete"
                record.result_json = result.model_dump_json()
                record.retry_count = state["retry_count"]
                record.model_used = (
                    settings.openai_model
                    if settings.llm_provider == "openai"
                    else settings.bedrock_model_id
                )
                record.provider = settings.llm_provider
                logger.info("Analysis job %d is complete, provider is %s, retries were %d", job_id, settings.llm_provider, state["retry_count"])

            record.completed_at = datetime.now(timezone.utc)
            await db.commit()

        except Exception as exc:
            logger.exception("Analysis background task raised an unexpected error, job_id is %d, error is %s", job_id, exc)
            record.status = "error"
            record.error_message = str(exc)
            record.completed_at = datetime.now(timezone.utc)
            await db.commit()


@router.post("/run", response_model=AnalysisRunResponse, status_code=202)
async def run_analysis_endpoint(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    record = AnalysisResult(status="pending")
    db.add(record)
    await db.commit()
    await db.refresh(record)

    background_tasks.add_task(_run_analysis_task, record.id)
    return AnalysisRunResponse(job_id=record.id, status="pending")


@router.get("/status/{job_id}", response_model=AnalysisResultOut)
async def get_status(job_id: int, db: AsyncSession = Depends(get_db)):
    record = await db.get(AnalysisResult, job_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Analysis job {job_id} not found.")
    return _serialize(record)


@router.get("/latest", response_model=AnalysisResultOut)
async def get_latest(db: AsyncSession = Depends(get_db)):
    record = await db.scalar(
        select(AnalysisResult)
        .where(AnalysisResult.status == "complete")
        .order_by(AnalysisResult.completed_at.desc())
    )
    if not record:
        raise HTTPException(status_code=404, detail="No completed analysis found.")
    return _serialize(record)
