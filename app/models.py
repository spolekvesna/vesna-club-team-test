from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Boolean, Date, DateTime, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Worker(Base):
    __tablename__ = "workers"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="worker", index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

class Client(Base):
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(120), index=True)
    last_name: Mapped[str] = mapped_column(String(120), index=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    entry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contact: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fewer_opportunities: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    document_status: Mapped[str] = mapped_column(String(30), default="unknown")
    drive_ref: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

class CatalogCategory(Base):
    __tablename__ = "catalog_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

class CatalogItem(Base):
    __tablename__ = "catalog_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    category_key: Mapped[str] = mapped_column(String(80), index=True)
    parent_item_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    __table_args__ = (Index("ix_catalog_category_parent", "category_key", "parent_item_id"),)

class IndividualService(Base):
    __tablename__ = "individual_services"
    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"), index=True)
    service_date: Mapped[date] = mapped_column(Date, index=True)
    minutes: Mapped[int] = mapped_column(Integer)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="RESTRICT"), index=True)
    ka: Mapped[str] = mapped_column(String(20), default="KA3", index=True)
    subactivity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    area_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    activity_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    form_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    place_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    method_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    language_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    outcome_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    next_step_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    follow_up_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    progress_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    referral_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    catalog_snapshot_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    eligible_project: Mapped[bool] = mapped_column(Boolean, default=True)
    attendance_sheet_ref: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    transcribed_from_sheet: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    client = relationship("Client")
    worker = relationship("Worker")

class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    event_date: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ka: Mapped[str] = mapped_column(String(20), index=True)
    subactivity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    attendance_sheet_ref: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    created_by = relationship("Worker")

class EventWorker(Base):
    __tablename__ = "event_workers"
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="RESTRICT"), primary_key=True)

class EventParticipant(Base):
    __tablename__ = "event_participants"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"), nullable=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    participant_kind: Mapped[str] = mapped_column(String(30), default="project", index=True)
    attendance_status: Mapped[str] = mapped_column(String(30), default="present")
    eligible_project: Mapped[bool] = mapped_column(Boolean, default=True)
    transcribed_from_sheet: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint("event_id", "client_id", name="uq_event_client"),)
    event = relationship("Event")
    client = relationship("Client")

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    drive_ref: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    inserted_date: Mapped[date] = mapped_column(Date)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="RESTRICT"))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    client = relationship("Client")
    worker = relationship("Worker")

class DailyNote(Base):
    __tablename__ = "daily_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    note_date: Mapped[date] = mapped_column(Date, index=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="RESTRICT"), index=True)
    summary: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    worker = relationship("Worker")

class IndicatorRecord(Base):
    __tablename__ = "indicator_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    indicator_code: Mapped[str] = mapped_column(String(20), index=True)
    client_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"), nullable=True, index=True)
    record_date: Mapped[date] = mapped_column(Date, index=True)
    source_type: Mapped[str] = mapped_column(String(30), index=True)
    source_id: Mapped[str] = mapped_column(String(80), index=True)
    eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    transcribed_from_sheet: Mapped[bool] = mapped_column(Boolean, default=False)
    attendance_sheet_ref: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    __table_args__ = (UniqueConstraint("indicator_code", "client_id", "source_type", "source_id", name="uq_indicator_source_client"),)

class ProjectOutput(Base):
    __tablename__ = "project_outputs"
    id: Mapped[int] = mapped_column(primary_key=True)
    output_date: Mapped[date] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(255))
    output_type: Mapped[str] = mapped_column(String(100), default="document")
    reference: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="RESTRICT"))

class AnonymousFeedbackAggregate(Base):
    __tablename__ = "anonymous_feedback_aggregates"
    id: Mapped[int] = mapped_column(primary_key=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    denominator: Mapped[int] = mapped_column(Integer)
    positive_count: Mapped[int] = mapped_column(Integer)
    methodology: Mapped[str] = mapped_column(Text)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="RESTRICT"))

class WebAnalyticsAggregate(Base):
    __tablename__ = "web_analytics_aggregates"
    id: Mapped[int] = mapped_column(primary_key=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(120))
    visits: Mapped[int] = mapped_column(Integer)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="RESTRICT"))

class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workers.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(40), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str] = mapped_column(String(120), index=True)
    before_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    after_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    remote_ip: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

class BackupRun(Base):
    __tablename__ = "backup_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    kind: Mapped[str] = mapped_column(String(30), default="backup")
    status: Mapped[str] = mapped_column(String(30), default="running", index=True)
    path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    file_path: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(30), default="preview")
    preview_json: Mapped[str] = mapped_column(Text)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
