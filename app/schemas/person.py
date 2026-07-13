from pydantic import BaseModel, ConfigDict
from uuid import UUID
from app.db.models import RoleEnum

class PersonBase(BaseModel):
    code: str
    role: RoleEnum
    full_name: str
    is_active: bool = True

class PersonCreate(PersonBase):
    pass

class PersonResponse(PersonBase):
    id: UUID
    
    model_config = ConfigDict(from_attributes=True)
