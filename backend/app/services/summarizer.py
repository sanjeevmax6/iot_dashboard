from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log_entry import LogEntry
from app.models.machine import Machine


async def get_machine_summaries(db: AsyncSession) -> list[dict]:
    """
    Aggregate per-machine stats from the DB.
    Returns a list of plain dicts — one per machine — ready to pass to the agent.
    """
    machines = await db.scalars(select(Machine).order_by(Machine.machine_id))
    machine_list = list(machines)

    if not machine_list:
        return []

    summaries = []
    for machine in machine_list:
        mid = machine.machine_id

        # Status counts
        rows = await db.execute(
            select(LogEntry.status, func.count().label("cnt"))
            .where(LogEntry.machine_id == mid)
            .group_by(LogEntry.status)
        )
        counts = {row.status: row.cnt for row in rows}
        total = sum(counts.values())

        if total == 0:
            continue

        # Sensor aggregates
        agg = await db.execute(
            select(
                func.avg(LogEntry.temperature).label("avg_temp"),
                func.max(LogEntry.temperature).label("max_temp"),
                func.avg(LogEntry.vibration).label("avg_vib"),
                func.max(LogEntry.vibration).label("max_vib"),
                func.max(LogEntry.timestamp).label("last_seen"),
            ).where(LogEntry.machine_id == mid)
        )
        row = agg.one()

        error_count = counts.get("ERROR", 0)
        warning_count = counts.get("WARNING", 0)

        summaries.append(
            {
                "machine_id": mid,
                "total_readings": total,
                "error_count": error_count,
                "warning_count": warning_count,
                "operational_count": counts.get("OPERATIONAL", 0),
                "error_rate": round(error_count / total, 4),
                "warning_rate": round(warning_count / total, 4),
                "avg_temperature": round(row.avg_temp, 2),
                "max_temperature": round(row.max_temp, 2),
                "avg_vibration": round(row.avg_vib, 4),
                "max_vibration": round(row.max_vib, 4),
                "last_seen": row.last_seen.isoformat() if row.last_seen else None,
            }
        )

    return summaries
