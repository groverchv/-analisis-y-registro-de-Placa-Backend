import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Enum, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base

# Para SQLite necesitamos un generador de UUID como string si SQLite no soporta nativo,
# pero SQLAlchemy maneja esto transparentemente con el dialecto adecuado.
# Usaremos sqlalchemy.types.Uuid en SQLAlchemy 2.0
from sqlalchemy.types import Uuid

class RoleEnum(str, enum.Enum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    ADMIN = "ADMIN"

class UniversityPerson(Base):
    __tablename__ = "university_persons"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    code = Column(String, unique=True, index=True, nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)
    full_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    # Relación uno a muchos: Una persona puede tener varios vehículos
    vehicles = relationship("Vehicle", back_populates="owner")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    license_plate = Column(String, unique=True, index=True, nullable=False)
    owner_id = Column(Uuid, ForeignKey("university_persons.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relación inversa
    owner = relationship("UniversityPerson", back_populates="vehicles")
