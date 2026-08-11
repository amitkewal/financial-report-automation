import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Role(str, enum.Enum):
    ADMIN = "admin"
    PREPARER = "preparer"
    REVIEWER = "reviewer"


class FundType(str, enum.Enum):
    PE = "private_equity"
    RE = "real_estate"
    DEBT = "debt"
    HEDGE = "hedge_fund"
    OTHER = "other"


class ReportStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"
    DRAFT_GENERATED = "draft_generated"
    IN_REVIEW = "in_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    FINAL_PUBLISHED = "final_published"


class CheckStatus(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIPPED = "skipped"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(Role), nullable=False, default=Role.PREPARER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    client_access = relationship("UserClientAccess", back_populates="user", cascade="all, delete-orphan")


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    onshore_team = Column(String(255), nullable=True)
    offshore_team = Column(String(255), nullable=True)
    storage_link = Column(String(500), nullable=True)
    primary_contact_name = Column(String(255), nullable=True)
    primary_contact_email = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    funds = relationship("Fund", back_populates="client", cascade="all, delete-orphan")
    user_access = relationship("UserClientAccess", back_populates="client", cascade="all, delete-orphan")


class UserClientAccess(Base):
    __tablename__ = "user_client_access"
    __table_args__ = (UniqueConstraint("user_id", "client_id", name="uq_user_client"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    granted_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="client_access")
    client = relationship("Client", back_populates="user_access")


class Fund(Base):
    __tablename__ = "funds"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    legal_name = Column(String(255), nullable=False)
    short_code = Column(String(50), nullable=False)
    fund_type = Column(Enum(FundType), nullable=False, default=FundType.OTHER)
    fiscal_year_end = Column(String(20), nullable=True)  # e.g. "12-31"
    currency = Column(String(10), nullable=False, default="USD")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    client = relationship("Client", back_populates="funds")
    mapping_configs = relationship("MappingConfig", back_populates="fund", cascade="all, delete-orphan")
    templates = relationship("Template", back_populates="fund", cascade="all, delete-orphan")
    periods = relationship("Period", back_populates="fund", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("client_id", "short_code", name="uq_fund_shortcode_per_client"),)


class MappingConfig(Base):
    """A versioned, per-fund JSON configuration describing which statements
    exist for this fund, where their line items/tables live in the source
    workbook, and which cross-checks apply. See excel_engine.mapping_schema
    for the structure of `config_json`.
    """

    __tablename__ = "mapping_configs"

    id = Column(Integer, primary_key=True)
    fund_id = Column(Integer, ForeignKey("funds.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="draft")  # draft | confirmed
    config_json = Column(JSON, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    fund = relationship("Fund", back_populates="mapping_configs")


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True)
    fund_id = Column(Integer, ForeignKey("funds.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    filename = Column(String(500), nullable=False)
    storage_path = Column(String(1000), nullable=False)
    is_active = Column(Boolean, default=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    fund = relationship("Fund", back_populates="templates")


class Period(Base):
    __tablename__ = "periods"
    __table_args__ = (UniqueConstraint("fund_id", "period_label", name="uq_period_per_fund"),)

    id = Column(Integer, primary_key=True)
    fund_id = Column(Integer, ForeignKey("funds.id"), nullable=False)
    period_label = Column(String(50), nullable=False)  # e.g. "2025-12-31" or "2025-Q4"
    period_end_date = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    fund = relationship("Fund", back_populates="periods")
    workbooks = relationship("UploadedWorkbook", back_populates="period", cascade="all, delete-orphan")
    report_runs = relationship("ReportRun", back_populates="period", cascade="all, delete-orphan")


class UploadedWorkbook(Base):
    __tablename__ = "uploaded_workbooks"

    id = Column(Integer, primary_key=True)
    fund_id = Column(Integer, ForeignKey("funds.id"), nullable=False)
    period_id = Column(Integer, ForeignKey("periods.id"), nullable=False)
    mapping_config_id = Column(Integer, ForeignKey("mapping_configs.id"), nullable=True)
    filename = Column(String(500), nullable=False)
    storage_path = Column(String(1000), nullable=False)
    extracted_data_json = Column(JSON, nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), default=utcnow)

    period = relationship("Period", back_populates="workbooks")
    validation_checks = relationship("ValidationCheck", back_populates="workbook", cascade="all, delete-orphan")


class ValidationCheck(Base):
    __tablename__ = "validation_checks"

    id = Column(Integer, primary_key=True)
    workbook_id = Column(Integer, ForeignKey("uploaded_workbooks.id"), nullable=False)
    name = Column(String(255), nullable=False)
    statement = Column(String(100), nullable=True)
    status = Column(Enum(CheckStatus), nullable=False)
    expected_value = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    difference = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    is_overridden = Column(Boolean, default=False)
    override_comment = Column(Text, nullable=True)
    override_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    workbook = relationship("UploadedWorkbook", back_populates="validation_checks")


class ReportRun(Base):
    __tablename__ = "report_runs"

    id = Column(Integer, primary_key=True)
    fund_id = Column(Integer, ForeignKey("funds.id"), nullable=False)
    period_id = Column(Integer, ForeignKey("periods.id"), nullable=False)
    workbook_id = Column(Integer, ForeignKey("uploaded_workbooks.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False)
    status = Column(Enum(ReportStatus), nullable=False, default=ReportStatus.UPLOADED)
    draft_docx_path = Column(String(1000), nullable=True)
    final_docx_path = Column(String(1000), nullable=True)
    final_pdf_path = Column(String(1000), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    period = relationship("Period", back_populates="report_runs")
    approval_logs = relationship("ApprovalLog", back_populates="report_run", cascade="all, delete-orphan")


class ApprovalLog(Base):
    __tablename__ = "approval_logs"

    id = Column(Integer, primary_key=True)
    report_run_id = Column(Integer, ForeignKey("report_runs.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)  # submit_review | approve | reject | override_check | publish
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    report_run = relationship("ReportRun", back_populates="approval_logs")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(Integer, nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
