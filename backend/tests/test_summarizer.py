import pytest

from app.services.ingestion import ingest_csv
from app.services.summarizer import get_machine_summaries

SAMPLE_CSV = b"""timestamp,machine_id,temperature,vibration,status
2026-03-01T00:00:00,MCH-01,75.0,0.5,OPERATIONAL
2026-03-01T00:05:00,MCH-01,90.0,0.9,WARNING
2026-03-01T00:10:00,MCH-01,102.0,1.2,ERROR
2026-03-01T00:00:00,MCH-02,60.0,0.2,OPERATIONAL
2026-03-01T00:05:00,MCH-02,62.0,0.3,OPERATIONAL
"""


@pytest.mark.asyncio
async def test_empty_db_returns_empty_list(db_session):
    result = await get_machine_summaries(db_session)
    assert result == []


@pytest.mark.asyncio
async def test_summaries_contain_correct_counts(db_session):
    await ingest_csv(SAMPLE_CSV, db_session)
    summaries = await get_machine_summaries(db_session)

    assert len(summaries) == 2
    mch1 = next(s for s in summaries if s["machine_id"] == "MCH-01")
    assert mch1["total_readings"] == 3
    assert mch1["error_count"] == 1
    assert mch1["warning_count"] == 1
    assert mch1["operational_count"] == 1


@pytest.mark.asyncio
async def test_summaries_contain_sensor_aggregates(db_session):
    await ingest_csv(SAMPLE_CSV, db_session)
    summaries = await get_machine_summaries(db_session)

    mch1 = next(s for s in summaries if s["machine_id"] == "MCH-01")
    assert mch1["max_temperature"] == 102.0
    assert mch1["max_vibration"] == 1.2
    assert mch1["avg_temperature"] == pytest.approx(89.0, rel=1e-2)


@pytest.mark.asyncio
async def test_summaries_contain_rates(db_session):
    await ingest_csv(SAMPLE_CSV, db_session)
    summaries = await get_machine_summaries(db_session)

    mch1 = next(s for s in summaries if s["machine_id"] == "MCH-01")
    assert mch1["error_rate"] == pytest.approx(1 / 3, rel=1e-2)
    assert mch1["warning_rate"] == pytest.approx(1 / 3, rel=1e-2)


@pytest.mark.asyncio
async def test_summaries_ordered_by_machine_id(db_session):
    await ingest_csv(SAMPLE_CSV, db_session)
    summaries = await get_machine_summaries(db_session)
    ids = [s["machine_id"] for s in summaries]
    assert ids == sorted(ids)
