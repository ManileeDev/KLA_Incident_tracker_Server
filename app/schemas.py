from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from .constants import IncidentStatus, Severity


class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: Optional[str] = None
    severity: Severity
    reported_by: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be empty")
        if len(value) > 200:
            raise ValueError("title must be 200 characters or fewer")
        return value

    @field_validator("reported_by")
    @classmethod
    def validate_reported_by(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reported_by must not be empty")
        return value


class IncidentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[Severity] = None
    reported_by: Optional[str] = None
    assigned_to: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_update_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("title must not be empty")
        if len(value) > 200:
            raise ValueError("title must be 200 characters or fewer")
        return value

    @field_validator("reported_by", "assigned_to")
    @classmethod
    def validate_update_user(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("user fields must not be empty")
        return value


class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: IncidentStatus
    changed_by: str = "system"

    @field_validator("changed_by")
    @classmethod
    def validate_changed_by(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("changed_by must not be empty")
        return value


class SignInRequest(BaseModel):
    username: str
    password: str


class SignUpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    display_name: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("username must not be empty")
        if len(value) > 100:
            raise ValueError("username must be 100 characters or fewer")
        return value

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("display_name must not be empty")
        if len(value) > 150:
            raise ValueError("display_name must be 150 characters or fewer")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value:
            raise ValueError("password must not be empty")
        return value
