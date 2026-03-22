from datetime import datetime

from pydantic import BaseModel


class LogEntryOut(BaseModel):
    id: int
    timestamp: datetime
    machine_id: str
    temperature: float
    vibration: float
    status: str

    model_config = {"from_attributes": True}


class LogsPage(BaseModel):
    items: list[LogEntryOut]
    total: int
    page: int
    page_size: int
    pages: int
