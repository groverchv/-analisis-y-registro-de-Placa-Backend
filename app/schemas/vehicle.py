from pydantic import BaseModel, ConfigDict, field_validator
from uuid import UUID
from datetime import datetime
from app.ai.validators import normalize_plate_text, validate_bolivian_plate
from app.schemas.person import PersonResponse

class VehicleBase(BaseModel):
    license_plate: str
    owner_id: UUID

    @field_validator("license_plate")
    @classmethod
    def validate_license_plate(cls, value: str) -> str:
        normalized = normalize_plate_text(value)
        if not validate_bolivian_plate(normalized):
            raise ValueError("La placa debe tener el formato boliviano NNNNLLL.")
        return normalized

class VehicleCreate(VehicleBase):
    pass

class VehicleResponse(VehicleBase):
    id: UUID
    created_at: datetime
    
    # Podemos incluir al owner en la respuesta opcionalmente
    owner: PersonResponse | None = None
    
    model_config = ConfigDict(from_attributes=True)
