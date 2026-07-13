from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from app.schemas.person import PersonResponse

class VehicleBase(BaseModel):
    license_plate: str
    owner_id: UUID

class VehicleCreate(VehicleBase):
    pass

class VehicleResponse(VehicleBase):
    id: UUID
    created_at: datetime
    
    # Podemos incluir al owner en la respuesta opcionalmente
    owner: PersonResponse | None = None
    
    model_config = ConfigDict(from_attributes=True)
