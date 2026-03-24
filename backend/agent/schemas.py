from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MachineRisk(BaseModel):
    """Risk assessment for a single IoT machine."""

    machine_id: str = Field(description="Unique identifier of the machine")
    risk_level: Literal["high", "medium", "low"] = Field(description="Severity of the risk: high, medium, or low")
    risk_score: float = Field(ge=0.0, le=1.0, description="Numeric risk score between 0.0 (no risk) and 1.0 (critical)")
    reason: str = Field(description="Explanation of why this machine is at risk")
    affected_sensors: list[str] = Field(description="List of sensor names contributing to the risk")
    recommended_action: str = Field(description="Suggested maintenance or operational action")


class AnalysisOutput(BaseModel):
    """Structured output of the IoT fleet risk analysis."""

    top_at_risk_machines: list[MachineRisk] = Field(description="Ranked list of machines most at risk")
    fleet_summary: str = Field(description="Overall summary of fleet health and key findings")

    @field_validator("top_at_risk_machines")
    @classmethod
    def must_have_results(cls, v: list[MachineRisk]) -> list[MachineRisk]:
        if len(v) == 0:
            raise ValueError("top_at_risk_machines cannot be empty")
        return v
