from datetime import datetime

from pydantic import BaseModel


class MachineOut(BaseModel):
    machine_id: str
    total_logs: int
    error_count: int
    warning_count: int
    operational_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
