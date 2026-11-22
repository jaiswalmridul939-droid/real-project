from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_optional: Mapped[str | None] = mapped_column(String(120))
    language: Mapped[str] = mapped_column(String(5), default="en")
    phone_optional: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    state: Mapped[str | None] = mapped_column(String(100))
    district: Mapped[str | None] = mapped_column(String(100))
    age: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(String(30))
    land_acres: Mapped[float | None] = mapped_column(Float)
    land_ownership: Mapped[str | None] = mapped_column(String(20))
    income_band: Mapped[str | None] = mapped_column(String(40))
    category: Mapped[str | None] = mapped_column(String(20))
    has_bank_account: Mapped[bool | None] = mapped_column(Boolean)
    is_woman: Mapped[bool | None] = mapped_column(Boolean)
    crops: Mapped[list[str] | None] = mapped_column(JSON)
    family_size: Mapped[int | None] = mapped_column(Integer)
    occupation: Mapped[str | None] = mapped_column(String(100))
    raw_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Scheme(Base):
    __tablename__ = "schemes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_en: Mapped[str] = mapped_column(String(200))
    name_mr: Mapped[str] = mapped_column(String(200), default="")
    name_hi: Mapped[str] = mapped_column(String(200), default="")
    description_en: Mapped[str] = mapped_column(Text, default="")
    description_mr: Mapped[str] = mapped_column(Text, default="")
    description_hi: Mapped[str] = mapped_column(Text, default="")
    department: Mapped[str] = mapped_column(String(200), default="")
    level: Mapped[str] = mapped_column(String(20), default="central")
    benefit_summary: Mapped[str] = mapped_column(Text, default="")
    official_url: Mapped[str] = mapped_column(String(500))
    source_name: Mapped[str] = mapped_column(String(200), default="")
    last_verified_date: Mapped[date] = mapped_column(Date)
    deadline_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


class SchemeRule(Base):
    __tablename__ = "scheme_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    scheme_id: Mapped[int] = mapped_column(ForeignKey("schemes.id", ondelete="CASCADE"), index=True)
    field: Mapped[str] = mapped_column(String(80))
    operator: Mapped[str] = mapped_column(String(30))
    value_json: Mapped[object] = mapped_column(JSON)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    explanation_en: Mapped[str] = mapped_column(Text, default="")
    explanation_mr: Mapped[str] = mapped_column(Text, default="")
    explanation_hi: Mapped[str] = mapped_column(Text, default="")


class SchemeDocument(Base):
    __tablename__ = "scheme_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    scheme_id: Mapped[int] = mapped_column(ForeignKey("schemes.id", ondelete="CASCADE"), index=True)
    doc_name_en: Mapped[str] = mapped_column(String(200))
    doc_name_mr: Mapped[str] = mapped_column(String(200), default="")
    doc_name_hi: Mapped[str] = mapped_column(String(200), default="")
    where_to_get: Mapped[str] = mapped_column(Text, default="")
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)


class SchemeStep(Base):
    __tablename__ = "scheme_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    scheme_id: Mapped[int] = mapped_column(ForeignKey("schemes.id", ondelete="CASCADE"), index=True)
    step_no: Mapped[int] = mapped_column(Integer)
    text_en: Mapped[str] = mapped_column(Text)
    text_mr: Mapped[str] = mapped_column(Text, default="")
    text_hi: Mapped[str] = mapped_column(Text, default="")
    link_nullable: Mapped[str | None] = mapped_column(String(500))


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    scheme_id: Mapped[int] = mapped_column(ForeignKey("schemes.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(40))
    reasoning_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scheme_id: Mapped[int] = mapped_column(ForeignKey("schemes.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="Not started")
    notes: Mapped[str | None] = mapped_column(Text)
    applied_on: Mapped[date | None] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocumentChecklist(Base):
    __tablename__ = "document_checklist"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    doc_name: Mapped[str] = mapped_column(String(200))
    is_ready: Mapped[bool] = mapped_column(Boolean, default=False)


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"))
    scheme_id: Mapped[int] = mapped_column(ForeignKey("schemes.id", ondelete="CASCADE"), index=True)
    remind_on: Mapped[date] = mapped_column(Date)
    message: Mapped[str] = mapped_column(Text)
    sent_flag: Mapped[bool] = mapped_column(Boolean, default=False)


class MockMessage(Base):
    __tablename__ = "mock_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    channel: Mapped[str] = mapped_column(String(20))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SchemeAuditLog(Base):
    __tablename__ = "scheme_audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    scheme_id: Mapped[int | None] = mapped_column(ForeignKey("schemes.id", ondelete="SET NULL"), index=True)
    changed_by: Mapped[str] = mapped_column(String(200))
    change_json: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))