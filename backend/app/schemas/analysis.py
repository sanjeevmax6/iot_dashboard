from datetime import datetime

from pydantic import BaseModel

from agent.schemas import MachineRisk  # noqa: F401 — re-exported for API consumers


class AnalysisResultOut(BaseModel):
    id: int
    status: str
    retry_count: int
    model_used: str | None
    provider: str | None
    error_message: str | None
    top_at_risk_machines: list[MachineRisk] | None
    fleet_summary: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class AnalysisRunResponse(BaseModel):
    job_id: int
    status: str
