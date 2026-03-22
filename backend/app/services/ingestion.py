# Handles the logic behing the csv upload feat and populates our DB & Setup
import csv
import io
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log_entry import LogEntry
from app.models.machine import Machine

REQUIRED_COLUMNS = {"timestamp", "machine_id", "temperature", "vibration", "status"}
VALID_STATUSES = {"OPERATIONAL", "WARNING", "ERROR"}


class IngestionError(Exception):
    pass


async def ingest_csv(content: bytes, db: AsyncSession) -> dict:
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

    # Collect unique machine IDs from this file
    machine_ids: set[str] = set()
    parsed_rows: list[dict] = []

    for i, row in enumerate(rows, start=2):  # line 2 = first data row
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

        machine_ids.add(machine_id)
        parsed_rows.append(
            {
                "timestamp": timestamp,
                "machine_id": machine_id,
                "temperature": temperature,
                "vibration": vibration,
                "status": status,
            }
        )

    # Upsert machines
    for machine_id in machine_ids:
        exists = await db.scalar(select(Machine).where(Machine.machine_id == machine_id))
        if not exists:
            db.add(Machine(machine_id=machine_id))

    await db.flush()

    # Bulk insert log entries (skip exact timestamp+machine_id duplicates)
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

    return {
        "inserted": inserted,
        "skipped": skipped,
        "machines_found": sorted(machine_ids),
        "total_rows": len(parsed_rows),
    }
