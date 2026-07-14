from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import RecordStatusEnum, RoleEnum


class PersonBase(BaseModel):
    code: str = Field(min_length=3, max_length=50)
    role: RoleEnum
    full_name: str = Field(min_length=3, max_length=255)
    document_id: str | None = Field(default=None, max_length=50)
    faculty: str | None = Field(default=None, max_length=255)
    contact_info: str | None = Field(default=None, max_length=255)
    status: RecordStatusEnum = RecordStatusEnum.ACTIVE
    is_active: bool = True


class PersonCreate(PersonBase):
    pass


class PersonResponse(PersonBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
