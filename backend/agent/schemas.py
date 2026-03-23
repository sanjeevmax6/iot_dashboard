from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MachineRisk(BaseModel):
    machine_id: str
    risk_level: Literal["high", "medium", "low"]
    risk_score: float = Field(ge=0.0, le=1.0)
    reason: str
    affected_sensors: list[str]
    recommended_action: str


class AnalysisOutput(BaseModel):
    top_at_risk_machines: list[MachineRisk]
    fleet_summary: str

    @field_validator("top_at_risk_machines")
    @classmethod
    def must_have_results(cls, v: list[MachineRisk]) -> list[MachineRisk]:
        if len(v) == 0:
            raise ValueError("top_at_risk_machines cannot be empty")
        return v
