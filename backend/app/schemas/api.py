import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def reject_sensitive_number(value: str | None) -> str | None:
    if value and re.search(r"(?<!\d)\d{12}(?!\d)", value):
        raise ValueError("For your privacy, remove 12-digit identity numbers before continuing.")
    return value


class ProfileFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: str | None = None
    district: str | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    gender: str | None = None
    land_acres: float | None = Field(default=None, ge=0)
    land_ownership: Literal["owner", "tenant", "landless"] | None = None
    income_band: str | None = None
    category: Literal["General", "OBC", "SC", "ST"] | None = None
    has_bank_account: bool | None = None
    is_woman: bool | None = None
    crops: list[str] | None = None
    family_size: int | None = Field(default=None, ge=1, le=30)
    occupation: str | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_private_numbers(cls, value):
        if isinstance(value, dict):
            for item in value.values():
                candidates = item if isinstance(item, list) else [item]
                for candidate in candidates:
                    if isinstance(candidate, str):
                        reject_sensitive_number(candidate)
        return value


class ProfileExtractRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    language: Literal["en", "hi", "mr"] = "en"

    @field_validator("text")
    @classmethod
    def protect_private_ids(cls, value: str) -> str:
        reject_sensitive_number(value)
        return value


class ProfileCreate(ProfileFields):
    user_id: int | None = None
    language: Literal["en", "hi", "mr"] = "en"
    raw_text: str | None = Field(default=None, max_length=4000)

    @field_validator("raw_text")
    @classmethod
    def protect_raw_text(cls, value: str | None) -> str | None:
        return reject_sensitive_number(value)


class ChecklistUpdate(BaseModel):
    user_id: int
    doc_name: str = Field(min_length=1, max_length=200)
    is_ready: bool


class ApplicationCreate(BaseModel):
    user_id: int
    scheme_id: int
    status: Literal["Not started", "Documents ready", "Applied", "Under review", "Approved", "Rejected"] = "Not started"
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("notes")
    @classmethod
    def protect_notes(cls, value: str | None) -> str | None:
        return reject_sensitive_number(value)


class ApplicationUpdate(BaseModel):
    status: Literal["Not started", "Documents ready", "Applied", "Under review", "Approved", "Rejected"] | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("notes")
    @classmethod
    def protect_notes(cls, value: str | None) -> str | None:
        return reject_sensitive_number(value)


class ReminderCreate(BaseModel):
    user_id: int
    scheme_id: int
    application_id: int | None = None
    remind_on: date
    message: str = Field(min_length=1, max_length=500)

    @field_validator("message")
    @classmethod
    def protect_message(cls, value: str) -> str:
        reject_sensitive_number(value)
        return value


class AdminLogin(BaseModel):
    email: str
    password: str


class SchemeWrite(BaseModel):
    name_en: str
    name_mr: str = ""
    name_hi: str = ""
    description_en: str = ""
    description_mr: str = ""
    description_hi: str = ""
    department: str = ""
    level: Literal["central", "state"] = "central"
    benefit_summary: str = ""
    official_url: str
    source_name: str
    last_verified_date: date
    deadline_date: date | None = None
    is_active: bool = True


class RuleWrite(BaseModel):
    field: str
    operator: Literal["eq", "neq", "lt", "lte", "gt", "gte", "in", "contains", "exists"]
    value_json: object = None
    weight: int = 1
    explanation_en: str = ""
    explanation_mr: str = ""
    explanation_hi: str = ""


class DocumentWrite(BaseModel):
    doc_name_en: str
    doc_name_mr: str = ""
    doc_name_hi: str = ""
    where_to_get: str = ""
    is_mandatory: bool = True


class StepWrite(BaseModel):
    step_no: int = Field(ge=1)
    text_en: str
    text_mr: str = ""
    text_hi: str = ""
    link_nullable: str | None = None