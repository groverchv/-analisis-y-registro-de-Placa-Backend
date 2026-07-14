from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models import AuthRoleEnum, RecordStatusEnum


class UserRegisterRequest(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    code: str = Field(min_length=3, max_length=50)
    faculty: str = Field(min_length=2, max_length=255)
    contact_info: str = Field(min_length=5, max_length=255)
    role: AuthRoleEnum = AuthRoleEnum.OPERATOR


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class AuthUserResponse(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    role: AuthRoleEnum
    status: RecordStatusEnum
    is_active: bool
    university_person_id: UUID | None = None
    code: str | None = None
    faculty: str | None = None
    contact_info: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    email: EmailStr
    code: str = Field(min_length=3, max_length=50)
    faculty: str = Field(min_length=2, max_length=255)
    contact_info: str = Field(min_length=5, max_length=255)
    password: str | None = Field(default=None, min_length=6, max_length=128)


class AuthResponse(BaseModel):
    token: str
    user: AuthUserResponse
