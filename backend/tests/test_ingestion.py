import pytest

from app.services.ingestion import IngestionError, ingest_csv

VALID_CSV = b"""timestamp,machine_id,temperature,vibration,status
2026-03-01T00:00:00,MCH-01,75.0,0.5,OPERATIONAL
2026-03-01T00:05:00,MCH-01,76.0,0.6,WARNING
2026-03-01T00:10:00,MCH-02,80.0,0.8,ERROR
"""


@pytest.mark.asyncio
async def test_valid_csv_inserts_rows(db_session):
    result = await ingest_csv(VALID_CSV, db_session)
    assert result["inserted"] == 3
    assert result["skipped"] == 0
    assert set(result["machines_found"]) == {"MCH-01", "MCH-02"}


@pytest.mark.asyncio
async def test_idempotent_reingest_skips_duplicates(db_session):
    await ingest_csv(VALID_CSV, db_session)
    result = await ingest_csv(VALID_CSV, db_session)
    assert result["inserted"] == 0
    assert result["skipped"] == 3


@pytest.mark.asyncio
async def test_missing_column_raises(db_session):
    bad_csv = b"timestamp,machine_id,temperature\n2026-03-01T00:00:00,MCH-01,75.0\n"
    with pytest.raises(IngestionError, match="missing required columns"):
        await ingest_csv(bad_csv, db_session)


@pytest.mark.asyncio
async def test_empty_file_raises(db_session):
    with pytest.raises(IngestionError):
        await ingest_csv(b"", db_session)


@pytest.mark.asyncio
async def test_header_only_raises(db_session):
    with pytest.raises(IngestionError, match="no data rows"):
        await ingest_csv(b"timestamp,machine_id,temperature,vibration,status\n", db_session)


@pytest.mark.asyncio
async def test_invalid_temperature_raises(db_session):
    bad_csv = b"timestamp,machine_id,temperature,vibration,status\n2026-03-01T00:00:00,MCH-01,not_a_float,0.5,OPERATIONAL\n"
    with pytest.raises(IngestionError, match="row 2"):
        await ingest_csv(bad_csv, db_session)


@pytest.mark.asyncio
async def test_invalid_status_raises(db_session):
    bad_csv = b"timestamp,machine_id,temperature,vibration,status\n2026-03-01T00:00:00,MCH-01,75.0,0.5,UNKNOWN\n"
    with pytest.raises(IngestionError, match="unknown status"):
        await ingest_csv(bad_csv, db_session)
