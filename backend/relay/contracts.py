from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class MappingDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    file: str
    header: str
    field: Literal['employee_id', 'first_name', 'last_name', 'email', 'date_of_birth', 'department', 'employment_status', 'account_status'] | None
    reason: str = Field(default='Consultant selected mapping', max_length=500)

class RecordDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['correct', 'approve', 'reject']
    data: dict[str, str] = Field(default_factory=dict)
    reason: str = Field(default='Consultant reviewed source context', max_length=500)

class TargetRecord(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    employee_id: str
    first_name: str
    last_name: str
    email: str
    department: str = ''
    date_of_birth: str
    employment_status: str
    account_status: str = ''

class TargetRequest(BaseModel):
    runId: str
    recordId: str
    data: TargetRecord
    simulateFailures: int = Field(default=0, ge=0, le=3)
