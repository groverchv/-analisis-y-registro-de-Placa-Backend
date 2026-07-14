from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import RecordStatusEnum, VehicleTypeEnum
from app.schemas.person import PersonCreate, PersonResponse


class VehicleOwnerPayload(PersonCreate):
    pass


class VehicleBase(BaseModel):
    license_plate: str = Field(min_length=5, max_length=20)
    brand: str = Field(min_length=2, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    color: str = Field(min_length=1, max_length=100)
    vehicle_photo_path: str | None = None
    vehicle_type: VehicleTypeEnum = VehicleTypeEnum.CAR
    year: str | None = Field(default=None, max_length=20)
    observation: str | None = None
    status: RecordStatusEnum = RecordStatusEnum.ACTIVE


class VehicleCreate(VehicleBase):
    owner_id: UUID | None = None
    registered_by_user_id: UUID | None = None
    owner: VehicleOwnerPayload | None = None


class VehicleResponse(VehicleBase):
    id: UUID
    owner_id: UUID
    registered_by_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    owner: PersonResponse | None = None

    model_config = ConfigDict(from_attributes=True)
