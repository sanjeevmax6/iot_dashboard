import json
import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.log_entry import LogEntry
from app.schemas.log_entry import LogsPage
from app.services.ingestion import IngestionError, ingest_csv, ingest_csv_stream

router = APIRouter(prefix="/logs", tags=["logs"])


@router.post("/ingest/stream")
async def ingest_logs_stream(file: UploadFile, db: AsyncSession = Depends(get_db)):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    content = await file.read()

    async def generate():
        async for event in ingest_csv_stream(content, db):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/ingest", status_code=status.HTTP_200_OK)
async def ingest_logs(file: UploadFile, db: AsyncSession = Depends(get_db)):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    content = await file.read()
    try:
        result = await ingest_csv(content, db)
    except IngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return result


@router.get("", response_model=LogsPage)
async def get_logs(
    machine_id: str | None = Query(None),
    status: str | None = Query(None),
    from_ts: datetime | None = Query(None, alias="from"),
    to_ts: datetime | None = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(LogEntry).order_by(LogEntry.timestamp.desc())

    if machine_id:
        query = query.where(LogEntry.machine_id == machine_id)
    if status:
        query = query.where(LogEntry.status == status.upper())
    if from_ts:
        query = query.where(LogEntry.timestamp >= from_ts)
    if to_ts:
        query = query.where(LogEntry.timestamp <= to_ts)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    offset = (page - 1) * page_size
    items_result = await db.scalars(query.offset(offset).limit(page_size))
    items = list(items_result)

    return LogsPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )
