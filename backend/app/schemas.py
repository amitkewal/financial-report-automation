from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import CheckStatus, FundType, ReportStatus, Role


# ---------- Auth ----------

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: Role = Role.PREPARER


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ClientAccessGrant(BaseModel):
    user_id: int
    client_id: int


# ---------- Client ----------

class ClientCreate(BaseModel):
    name: str
    onshore_team: Optional[str] = None
    offshore_team: Optional[str] = None
    storage_link: Optional[str] = None
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    notes: Optional[str] = None


class ClientUpdate(ClientCreate):
    pass


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    onshore_team: Optional[str]
    offshore_team: Optional[str]
    storage_link: Optional[str]
    primary_contact_name: Optional[str]
    primary_contact_email: Optional[str]
    notes: Optional[str]
    created_at: datetime


# ---------- Fund ----------

class FundCreate(BaseModel):
    legal_name: str
    short_code: str
    fund_type: FundType = FundType.OTHER
    fiscal_year_end: Optional[str] = None
    currency: str = "USD"


class FundUpdate(FundCreate):
    pass


class FundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_id: int
    legal_name: str
    short_code: str
    fund_type: FundType
    fiscal_year_end: Optional[str]
    currency: str
    created_at: datetime


# ---------- Mapping Config ----------

class MappingConfigCreate(BaseModel):
    config_json: dict[str, Any]
    status: str = "draft"


class MappingConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fund_id: int
    version: int
    status: str
    config_json: dict[str, Any]
    created_at: datetime


class InferMappingResponse(BaseModel):
    suggested_config: dict[str, Any]
    sheet_names: list[str]
    warnings: list[str]


# ---------- Template ----------

class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fund_id: int
    version: int
    filename: str
    is_active: bool
    created_at: datetime


# ---------- Period ----------

class PeriodCreate(BaseModel):
    period_label: str
    period_end_date: Optional[str] = None


class PeriodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fund_id: int
    period_label: str
    period_end_date: Optional[str]
    created_at: datetime


# ---------- Workbook / Validation ----------

class WorkbookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fund_id: int
    period_id: int
    filename: str
    mapping_config_id: Optional[int]
    uploaded_at: datetime


class ValidationCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    statement: Optional[str]
    status: CheckStatus
    expected_value: Optional[float]
    actual_value: Optional[float]
    difference: Optional[float]
    message: Optional[str]
    is_overridden: bool
    override_comment: Optional[str]


class OverrideCheckRequest(BaseModel):
    comment: str


# ---------- Report Run ----------

class ReportRunCreate(BaseModel):
    workbook_id: int
    template_id: int


class ReportRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fund_id: int
    period_id: int
    workbook_id: int
    template_id: int
    status: ReportStatus
    draft_docx_path: Optional[str]
    final_docx_path: Optional[str]
    final_pdf_path: Optional[str]
    created_at: datetime
    updated_at: datetime


class ApprovalActionRequest(BaseModel):
    comment: Optional[str] = None


class ApprovalLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_id: Optional[int]
    action: str
    comment: Optional[str]
    created_at: datetime
