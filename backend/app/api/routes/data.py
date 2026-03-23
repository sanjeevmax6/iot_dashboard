from fastapi import APIRouter, Depends
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.analysis_result import AnalysisResult
from app.models.log_entry import LogEntry
from app.models.machine import Machine

router = APIRouter(prefix="/data", tags=["data"])


@router.delete("")
async def clear_all_data(db: AsyncSession = Depends(get_db)):
    await db.execute(delete(LogEntry))
    await db.execute(delete(AnalysisResult))
    await db.execute(delete(Machine))
    await db.commit()
    return {"cleared": True}
