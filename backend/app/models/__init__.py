import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Float, ForeignKey, Enum, Text, JSON
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class ImportStatus(str, enum.Enum):
    RECEIVED = "Recebido"
    VALIDATING = "Validando"
    QUEUED = "Na Fila"
    PROCESSING = "Em Processamento"
    AWAITING_REVIEW = "Aguardando Revisão"
    COMPLETED = "Concluído"
    FAILED = "Falha"
    REJECTED = "Rejeitado"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class Company(Base):
    """A client company whose payroll spreadsheets are imported.

    The CNPJ is the stable identity — display names vary between export
    templates ("Suporte" vs "Suporte Serviços Ltda"), while the CNPJ printed
    in the filename does not."""
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    cnpj = Column(String(14), unique=True, index=True, nullable=True)
    name = Column(String, unique=True, nullable=False)
    # "NORMAL" or "SIMPLES_NACIONAL" — see app/services/provisions.py.
    # Defaults to Regime Normal, the costlier assumption, so a company nobody
    # has configured yet is never reported as cheaper than it is.
    tax_regime = Column(String, nullable=False, default="NORMAL", server_default="NORMAL")
    created_at = Column(DateTime, default=datetime.utcnow)

    imports = relationship("ImportJob", back_populates="company")


class ImportJob(Base):
    __tablename__ = "imports"
    id = Column(Integer, primary_key=True, index=True)
    filename_metadata = Column(String, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    # What the resolver read off the filename/spreadsheet, kept for auditing
    # even when the company was later corrected by hand.
    company_name_raw = Column(String, nullable=True)
    minio_object_key = Column(String, nullable=False, unique=True)
    file_hash = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    status = Column(Enum(ImportStatus), default=ImportStatus.RECEIVED, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    attempt_count = Column(Integer, default=0)
    
    company = relationship("Company", back_populates="imports")
    parser_runs = relationship("ParserRun", back_populates="import_job")
    snapshots = relationship("Snapshot", back_populates="import_job")

class ParserRun(Base):
    __tablename__ = "parser_runs"
    id = Column(Integer, primary_key=True, index=True)
    import_id = Column(Integer, ForeignKey("imports.id"))
    parser_version = Column(String, nullable=False)
    status = Column(String, nullable=False)  # SUCCESS, FAILED
    confidence_score = Column(Float, nullable=True)
    confidence_factors = Column(JSON, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_details = Column(Text, nullable=True)

    import_job = relationship("ImportJob", back_populates="parser_runs")
    findings = relationship("DataQualityFinding", back_populates="parser_run")

class Snapshot(Base):
    __tablename__ = "snapshots"
    id = Column(Integer, primary_key=True, index=True)
    import_id = Column(Integer, ForeignKey("imports.id"))
    reference_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, nullable=False)  # ACTIVE, ARCHIVED

    import_job = relationship("ImportJob", back_populates="snapshots")
    employees = relationship("EmployeeRecord", back_populates="snapshot")
    metrics = relationship("MetricResult", back_populates="snapshot")

class EmployeeRecord(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"))
    original_row = Column(Integer, nullable=False)
    code = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    job_title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    admission_date = Column(DateTime, nullable=True)
    salary = Column(Float, nullable=True)  # Using Float for MVP, could use Numeric
    raw_data = Column(JSON, nullable=True)

    snapshot = relationship("Snapshot", back_populates="employees")

class DataQualityFinding(Base):
    __tablename__ = "data_quality_findings"
    id = Column(Integer, primary_key=True, index=True)
    import_id = Column(Integer, ForeignKey("imports.id"))
    parser_run_id = Column(Integer, ForeignKey("parser_runs.id"))
    severity = Column(String, nullable=False)  # CRITICAL, ERROR, WARNING, INFO
    field_name = Column(String, nullable=True)
    original_row = Column(Integer, nullable=True)
    issue_description = Column(String, nullable=False)

    parser_run = relationship("ParserRun", back_populates="findings")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class MetricResult(Base):
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"))
    metric_id = Column(String, nullable=False)  # e.g., 'active_headcount'
    metric_value = Column(Float, nullable=False)
    calculated_at = Column(DateTime, default=datetime.utcnow)

    snapshot = relationship("Snapshot", back_populates="metrics")

class EmployeeNote(Base):
    __tablename__ = "employee_notes"
    id = Column(Integer, primary_key=True, index=True)
    # `company` (the display name) is kept for backwards compatibility with
    # notes written before companies became first-class; `company_id` is the
    # key new notes are stored under.
    company = Column(String, nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    code = Column(String, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
