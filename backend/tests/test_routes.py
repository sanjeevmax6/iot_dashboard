from unittest.mock import patch

import pytest

from agent.schemas import AnalysisOutput, MachineRisk

VALID_CSV = b"""timestamp,machine_id,temperature,vibration,status
2026-03-01T00:00:00,MCH-01,75.0,0.5,OPERATIONAL
2026-03-01T00:05:00,MCH-01,76.0,0.6,WARNING
2026-03-01T00:10:00,MCH-02,80.0,0.8,ERROR
"""


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ingest_returns_counts(client):
    resp = await client.post(
        "/api/logs/ingest",
        files={"file": ("data.csv", VALID_CSV, "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["inserted"] == 3
    assert body["total_rows"] == 3


@pytest.mark.asyncio
async def test_ingest_rejects_non_csv(client):
    resp = await client.post(
        "/api/logs/ingest",
        files={"file": ("data.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_ingest_rejects_bad_csv(client):
    resp = await client.post(
        "/api/logs/ingest",
        files={"file": ("data.csv", b"col1,col2\n1,2\n", "text/csv")},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_logs_empty(client):
    resp = await client.get("/api/logs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_get_logs_after_ingest(client):
    await client.post("/api/logs/ingest", files={"file": ("data.csv", VALID_CSV, "text/csv")})
    resp = await client.get("/api/logs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3


@pytest.mark.asyncio
async def test_get_logs_filter_by_machine(client):
    await client.post("/api/logs/ingest", files={"file": ("data.csv", VALID_CSV, "text/csv")})
    resp = await client.get("/api/logs?machine_id=MCH-01")
    assert resp.json()["total"] == 2


@pytest.mark.asyncio
async def test_get_logs_filter_by_status(client):
    await client.post("/api/logs/ingest", files={"file": ("data.csv", VALID_CSV, "text/csv")})
    resp = await client.get("/api/logs?status=error")
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_get_logs_pagination(client):
    await client.post("/api/logs/ingest", files={"file": ("data.csv", VALID_CSV, "text/csv")})
    resp = await client.get("/api/logs?page=1&page_size=2")
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["pages"] == 2


@pytest.mark.asyncio
async def test_get_machines_empty(client):
    resp = await client.get("/api/machines")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_machines_after_ingest(client):
    await client.post("/api/logs/ingest", files={"file": ("data.csv", VALID_CSV, "text/csv")})
    resp = await client.get("/api/machines")
    body = resp.json()
    assert len(body) == 2
    mch1 = next(m for m in body if m["machine_id"] == "MCH-01")
    assert mch1["total_logs"] == 2
    assert mch1["warning_count"] == 1
    assert mch1["error_count"] == 0


@pytest.mark.asyncio
async def test_get_machine_by_id(client):
    await client.post("/api/logs/ingest", files={"file": ("data.csv", VALID_CSV, "text/csv")})
    resp = await client.get("/api/machines/MCH-02")
    body = resp.json()
    assert body["machine_id"] == "MCH-02"
    assert body["error_count"] == 1


@pytest.mark.asyncio
async def test_get_machine_not_found(client):
    resp = await client.get("/api/machines/MCH-99")
    assert resp.status_code == 404


# ── Analysis routes ────────────────────────────────────────────────────────────

MOCK_ANALYSIS_OUTPUT = AnalysisOutput(
    top_at_risk_machines=[
        MachineRisk(machine_id="MCH-01", risk_level="high", risk_score=0.9,
                    reason="errors", affected_sensors=["temperature"], recommended_action="Inspect"),
        MachineRisk(machine_id="MCH-02", risk_level="medium", risk_score=0.5,
                    reason="warnings", affected_sensors=["vibration"], recommended_action="Monitor"),
    ],
    fleet_summary="Fleet needs attention.",
)


def _mock_run_analysis(output: AnalysisOutput):
    async def _inner(_summaries):
        return {
            "machine_summaries": _summaries,
            "valid_machine_ids": [m.machine_id for m in output.top_at_risk_machines],
            "parsed_result": output,
            "validation_errors": [],
            "retry_count": 1,
            "error_state": None,
        }
    return _inner


@pytest.mark.asyncio
async def test_run_analysis_returns_job_id(client):
    await client.post("/api/logs/ingest", files={"file": ("data.csv", VALID_CSV, "text/csv")})
    # Patch the background task so it doesn't open a separate DB session
    async def _noop(job_id): pass
    with patch("app.api.routes.analysis._run_analysis_task", side_effect=_noop):
        resp = await client.post("/api/analysis/run")
    assert resp.status_code == 202
    assert "job_id" in resp.json()



@pytest.mark.asyncio
async def test_get_status_not_found(client):
    resp = await client.get("/api/analysis/status/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_latest_no_results(client):
    resp = await client.get("/api/analysis/latest")
    assert resp.status_code == 404


