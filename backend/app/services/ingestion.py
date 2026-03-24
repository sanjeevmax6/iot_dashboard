# Handles the logic behing the csv upload feat and populates our DB & Setup
import csv
import io
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.models.log_entry import LogEntry
from app.models.machine import Machine

logger = get_logger(__name__)

REQUIRED_COLUMNS = {"timestamp", "machine_id", "temperature", "vibration", "status"}
VALID_STATUSES = {"OPERATIONAL", "WARNING", "ERROR"}
STREAM_PROGRESS_EVERY = 50


class IngestionError(Exception):
    pass


def _parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise IngestionError("CSV file is empty or has no header row.")

    missing = REQUIRED_COLUMNS - {f.strip() for f in reader.fieldnames}
    if missing:
        raise IngestionError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

    rows = list(reader)
    if not rows:
        raise IngestionError("CSV has a header but no data rows.")

    parsed: list[dict] = []
    for i, row in enumerate(rows, start=2):
        try:
            machine_id = row["machine_id"].strip()
            status = row["status"].strip().upper()
            temperature = float(row["temperature"])
            vibration = float(row["vibration"])
            timestamp = datetime.fromisoformat(row["timestamp"].strip())
        except (ValueError, KeyError) as exc:
            raise IngestionError(f"Invalid data on row {i}: {exc}") from exc

        if status not in VALID_STATUSES:
            raise IngestionError(f"Row {i}: unknown status '{status}'. Must be one of {VALID_STATUSES}.")

        parsed.append({
            "timestamp": timestamp,
            "machine_id": machine_id,
            "temperature": temperature,
            "vibration": vibration,
            "status": status,
        })

    return parsed


async def _upsert_machines(machine_ids: set[str], db: AsyncSession) -> None:
    for machine_id in machine_ids:
        exists = await db.scalar(select(Machine).where(Machine.machine_id == machine_id))
        if not exists:
            db.add(Machine(machine_id=machine_id))
    await db.flush()


async def ingest_csv(content: bytes, db: AsyncSession) -> dict:
    parsed_rows = _parse_csv(content)
    machine_ids = {r["machine_id"] for r in parsed_rows}
    logger.info("Ingestion is starting, parsed %d rows across %d machines", len(parsed_rows), len(machine_ids))
    await _upsert_machines(machine_ids, db)

    inserted = 0
    skipped = 0
    for row in parsed_rows:
        duplicate = await db.scalar(
            select(LogEntry).where(
                LogEntry.machine_id == row["machine_id"],
                LogEntry.timestamp == row["timestamp"],
            )
        )
        if duplicate:
            skipped += 1
            continue
        db.add(LogEntry(**row))
        inserted += 1

    await db.commit()
    logger.info("Ingestion is complete, inserted %d rows, skipped %d duplicates", inserted, skipped)
    return {
        "inserted": inserted,
        "skipped": skipped,
        "machines_found": sorted(machine_ids),
        "total_rows": len(parsed_rows),
    }


async def ingest_csv_stream(
    content: bytes, db: AsyncSession
) -> AsyncGenerator[dict[str, Any], None]:
    """Async generator yielding SSE-style progress dicts."""
    try:
        parsed_rows = _parse_csv(content)
    except IngestionError as exc:
        logger.error("CSV parsing failed, error is %s", exc)
        yield {"type": "error", "message": str(exc)}
        return

    total = len(parsed_rows)
    machine_ids = {r["machine_id"] for r in parsed_rows}
    logger.info("Streaming ingestion is starting, parsed %d rows across %d machines", total, len(machine_ids))
    await _upsert_machines(machine_ids, db)

    yield {"type": "start", "total": total}

    inserted = 0
    skipped = 0
    for i, row in enumerate(parsed_rows, start=1):
        duplicate = await db.scalar(
            select(LogEntry).where(
                LogEntry.machine_id == row["machine_id"],
                LogEntry.timestamp == row["timestamp"],
            )
        )
        if duplicate:
            skipped += 1
        else:
            db.add(LogEntry(**row))
            inserted += 1

        if i % STREAM_PROGRESS_EVERY == 0 or i == total:
            yield {
                "type": "progress",
                "processed": i,
                "total": total,
                "machine_id": row["machine_id"],
                "timestamp": row["timestamp"].isoformat(),
                "inserted": inserted,
                "skipped": skipped,
            }

    await db.commit()
    logger.info("Streaming ingestion is complete, inserted %d rows, skipped %d duplicates", inserted, skipped)
    yield {
        "type": "complete",
        "inserted": inserted,
        "skipped": skipped,
        "machines_found": sorted(machine_ids),
        "total_rows": total,
    }
