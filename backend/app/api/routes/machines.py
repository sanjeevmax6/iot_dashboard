from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.log_entry import LogEntry
from app.models.machine import Machine
from app.schemas.machine import MachineOut

router = APIRouter(prefix="/machines", tags=["machines"])


async def _machine_stats(machine_id: str, db: AsyncSession) -> MachineOut:
    machine = await db.scalar(select(Machine).where(Machine.machine_id == machine_id))
    if not machine:
        raise HTTPException(status_code=404, detail=f"Machine '{machine_id}' not found.")

    rows = await db.execute(
        select(LogEntry.status, func.count().label("cnt"))
        .where(LogEntry.machine_id == machine_id)
        .group_by(LogEntry.status)
    )
    counts = {row.status: row.cnt for row in rows}

    return MachineOut(
        machine_id=machine.machine_id,
        total_logs=sum(counts.values()),
        error_count=counts.get("ERROR", 0),
        warning_count=counts.get("WARNING", 0),
        operational_count=counts.get("OPERATIONAL", 0),
        created_at=machine.created_at,
    )


# Listing ll unique machines
@router.get("", response_model=list[MachineOut])
async def list_machines(db: AsyncSession = Depends(get_db)):
    machines = await db.scalars(select(Machine).order_by(Machine.machine_id))
    return [await _machine_stats(m.machine_id, db) for m in machines]


# To get machine status: "Operational" or "Error"
@router.get("/{machine_id}", response_model=MachineOut)
async def get_machine(machine_id: str, db: AsyncSession = Depends(get_db)):
    return await _machine_stats(machine_id, db)
