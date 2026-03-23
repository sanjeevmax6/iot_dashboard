from datetime import datetime, timezone

import pytest

from agent.schemas import AnalysisOutput, MachineRisk
from app.models.analysis_result import AnalysisResult

VALID_CSV = b"""timestamp,machine_id,temperature,vibration,status
2026-03-01T00:00:00,MCH-01,75.0,0.5,OPERATIONAL
2026-03-01T00:05:00,MCH-02,80.0,0.8,ERROR
"""

MOCK_ANALYSIS = AnalysisOutput(
    top_at_risk_machines=[
        MachineRisk(
            machine_id="MCH-01",
            risk_level="high",
            risk_score=0.9,
            reason="errors",
            affected_sensors=["temperature"],
            recommended_action="Inspect",
        )
    ],
    fleet_summary="Needs attention.",
)


@pytest.mark.asyncio
async def test_clear_empty_db_returns_cleared(client):
    resp = await client.delete("/api/data")
    assert resp.status_code == 200
    assert resp.json() == {"cleared": True}


@pytest.mark.asyncio
async def test_clear_removes_logs(client):
    await client.post("/api/logs/ingest", files={"file": ("data.csv", VALID_CSV, "text/csv")})
    assert (await client.get("/api/logs")).json()["total"] == 2

    await client.delete("/api/data")

    assert (await client.get("/api/logs")).json()["total"] == 0


@pytest.mark.asyncio
async def test_clear_removes_machines(client):
    await client.post("/api/logs/ingest", files={"file": ("data.csv", VALID_CSV, "text/csv")})
    assert len((await client.get("/api/machines")).json()) == 2

    await client.delete("/api/data")

    assert (await client.get("/api/machines")).json() == []


@pytest.mark.asyncio
async def test_clear_removes_analysis_results(client, db_session):
    record = AnalysisResult(
        status="complete",
        result_json=MOCK_ANALYSIS.model_dump_json(),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(record)
    await db_session.commit()

    assert (await client.get("/api/analysis/latest")).status_code == 200

    await client.delete("/api/data")

    assert (await client.get("/api/analysis/latest")).status_code == 404


@pytest.mark.asyncio
async def test_clear_is_idempotent(client):
    await client.delete("/api/data")
    resp = await client.delete("/api/data")
    assert resp.status_code == 200
    assert resp.json() == {"cleared": True}
