from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Literal

class CreateProfile(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    pin: str = Field(min_length=6, max_length=8, pattern=r"^\d+$")
    email: str = Field(default="", max_length=254)
    timezone: str = "Asia/Kolkata"

class Login(BaseModel):
    profile_code: str = Field(min_length=6, max_length=12)
    pin: str = Field(min_length=6, max_length=8, pattern=r"^\d{6,8}$")

class InviteCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(default="", max_length=254)
    role: Literal["caregiver", "family"]

class JoinInvite(BaseModel):
    invite_code: str = Field(min_length=6, max_length=12)
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(default="", max_length=254)
    pin: str = Field(min_length=6, max_length=8, pattern=r"^\d+$")

class MedicationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    strength: str = Field(default="", max_length=60)
    instructions: str = Field(default="", max_length=240)
    route: Literal["Oral", "Topical", "Inhaled", "Injection", "Other"] = "Oral"
    times: list[str] = Field(min_length=1, max_length=8)
    start_date: str
    end_date: str = ""
    prescriber: str = Field(default="", max_length=100)
    @field_validator("times")
    @classmethod
    def valid_times(cls, values):
        import re
        for v in values:
            if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", v): raise ValueError("Times must use 24-hour HH:MM format")
        if len(values) != len(set(values)):
            raise ValueError("Schedule times must be unique.")
        return sorted(values)
    @field_validator("start_date", "end_date")
    @classmethod
    def valid_dates(cls, v):
        if v:
            from datetime import date
            date.fromisoformat(v)
        return v

class DoseAction(BaseModel):
    action: Literal["taken", "skipped"]
    note: str = Field(default="", max_length=240)

class AppointmentCreate(BaseModel):
    clinician: str = Field(min_length=2, max_length=100)
    location: str = Field(default="", max_length=140)
    starts_at: datetime
    notes: str = Field(default="", max_length=240)

class CareTaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=300)
    category: Literal["appointment", "transport", "supplies", "follow_up", "other"] = "other"
    due_at: datetime | None = None
    assigned_to: int | None = None


class TaskCoachRequest(BaseModel):
    category: Literal["appointment", "transport", "supplies", "follow_up", "other"]
    consent: bool = False
