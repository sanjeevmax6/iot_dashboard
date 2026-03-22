import pytest

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
