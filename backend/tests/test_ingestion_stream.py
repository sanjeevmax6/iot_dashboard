import pytest

from app.services.ingestion import ingest_csv_stream

VALID_CSV = b"""timestamp,machine_id,temperature,vibration,status
2026-03-01T00:00:00,MCH-01,75.0,0.5,OPERATIONAL
2026-03-01T00:05:00,MCH-01,76.0,0.6,WARNING
2026-03-01T00:10:00,MCH-02,80.0,0.8,ERROR
"""

INVALID_CSV = b"col1,col2\n1,2\n"


@pytest.mark.asyncio
async def test_stream_valid_csv_starts_and_completes(db_session):
    events = [e async for e in ingest_csv_stream(VALID_CSV, db_session)]
    types = [e["type"] for e in events]
    assert types[0] == "start"
    assert types[-1] == "complete"


@pytest.mark.asyncio
async def test_stream_complete_event_has_correct_counts(db_session):
    events = [e async for e in ingest_csv_stream(VALID_CSV, db_session)]
    complete = next(e for e in events if e["type"] == "complete")
    assert complete["inserted"] == 3
    assert complete["skipped"] == 0
    assert complete["total_rows"] == 3
    assert sorted(complete["machines_found"]) == ["MCH-01", "MCH-02"]


@pytest.mark.asyncio
async def test_stream_start_event_has_total(db_session):
    events = [e async for e in ingest_csv_stream(VALID_CSV, db_session)]
    start = next(e for e in events if e["type"] == "start")
    assert start["total"] == 3


@pytest.mark.asyncio
async def test_stream_invalid_csv_yields_single_error(db_session):
    events = [e async for e in ingest_csv_stream(INVALID_CSV, db_session)]
    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "missing" in events[0]["message"].lower() or "column" in events[0]["message"].lower()


@pytest.mark.asyncio
async def test_stream_skips_duplicates_on_reingest(db_session):
    # First ingest
    _ = [e async for e in ingest_csv_stream(VALID_CSV, db_session)]
    # Re-ingest same data
    events = [e async for e in ingest_csv_stream(VALID_CSV, db_session)]
    complete = next(e for e in events if e["type"] == "complete")
    assert complete["skipped"] == 3
    assert complete["inserted"] == 0


@pytest.mark.asyncio
async def test_stream_progress_events_emitted_for_large_csv(db_session):
    # STREAM_PROGRESS_EVERY = 50, so need >50 rows to get a mid-stream progress event
    header = b"timestamp,machine_id,temperature,vibration,status\n"
    rows = b""
    for i in range(52):
        rows += f"2026-03-01T{i // 60:02d}:{i % 60:02d}:00,MCH-01,70.0,0.5,OPERATIONAL\n".encode()

    events = [e async for e in ingest_csv_stream(header + rows, db_session)]
    progress_events = [e for e in events if e["type"] == "progress"]
    assert len(progress_events) >= 1
    first_progress = progress_events[0]
    assert "processed" in first_progress
    assert "total" in first_progress
    assert "inserted" in first_progress
    assert "skipped" in first_progress


@pytest.mark.asyncio
async def test_stream_ingest_endpoint_returns_sse(client):
    resp = await client.post(
        "/api/logs/ingest/stream",
        files={"file": ("data.csv", VALID_CSV, "text/csv")},
    )
    assert resp.status_code == 200
    assert '"type": "start"' in resp.text
    assert '"type": "complete"' in resp.text


@pytest.mark.asyncio
async def test_stream_ingest_endpoint_rejects_non_csv(client):
    resp = await client.post(
        "/api/logs/ingest/stream",
        files={"file": ("data.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400
