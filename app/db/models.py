import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.types import Uuid

from app.db.session import Base


class RoleEnum(str, enum.Enum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    ADMIN = "ADMIN"


class RecordStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class AuthRoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"


class VehicleTypeEnum(str, enum.Enum):
    CAR = "CAR"
    MOTORCYCLE = "MOTORCYCLE"
    VAN = "VAN"
    TRUCK = "TRUCK"
    OTHER = "OTHER"


class ScanStatusEnum(str, enum.Enum):
    DETECTED = "DETECTED"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    ERROR = "ERROR"
    MANUAL = "MANUAL"


class NotificationTypeEnum(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ALERT = "ALERT"


class UniversityPerson(Base):
    __tablename__ = "university_persons"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    code = Column(String, unique=True, index=True, nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)
    full_name = Column(String, nullable=False)
    document_id = Column(String, nullable=True)
    faculty = Column(String, nullable=True)
    contact_info = Column(String, nullable=True)
    status = Column(Enum(RecordStatusEnum), default=RecordStatusEnum.ACTIVE, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    vehicles = relationship("Vehicle", back_populates="owner")
    auth_users = relationship("AuthUser", back_populates="university_person")


class AuthUser(Base):
    __tablename__ = "auth_users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(AuthRoleEnum), default=AuthRoleEnum.OPERATOR, nullable=False)
    status = Column(Enum(RecordStatusEnum), default=RecordStatusEnum.ACTIVE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    university_person_id = Column(Uuid, ForeignKey("university_persons.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    university_person = relationship("UniversityPerson", back_populates="auth_users")
    registered_vehicles = relationship("Vehicle", back_populates="registered_by_user")
    plate_scans = relationship("PlateScan", back_populates="scanned_by_user")
    notifications = relationship("Notification", back_populates="user")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    license_plate = Column(String, unique=True, index=True, nullable=False)
    brand = Column(String, nullable=False)
    model = Column(String, nullable=False)
    color = Column(String, nullable=False)
    vehicle_photo_path = Column(String, nullable=True)
    vehicle_type = Column(Enum(VehicleTypeEnum), default=VehicleTypeEnum.CAR, nullable=False)
    year = Column(String, nullable=True)
    observation = Column(Text, nullable=True)
    status = Column(Enum(RecordStatusEnum), default=RecordStatusEnum.ACTIVE, nullable=False)
    owner_id = Column(Uuid, ForeignKey("university_persons.id"), nullable=False)
    registered_by_user_id = Column(Uuid, ForeignKey("auth_users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner = relationship("UniversityPerson", back_populates="vehicles")
    registered_by_user = relationship("AuthUser", back_populates="registered_vehicles")
    scans = relationship("PlateScan", back_populates="vehicle")


class PlateScan(Base):
    __tablename__ = "plate_scans"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    image_path = Column(String, nullable=True)
    detected_plate = Column(String, nullable=True)
    normalized_plate = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    scan_status = Column(Enum(ScanStatusEnum), nullable=False)
    manual_correction = Column(String, nullable=True)
    vehicle_id = Column(Uuid, ForeignKey("vehicles.id"), nullable=True)
    scanned_by_user_id = Column(Uuid, ForeignKey("auth_users.id"), nullable=True)
    observations = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    vehicle = relationship("Vehicle", back_populates="scans")
    scanned_by_user = relationship("AuthUser", back_populates="plate_scans")
    notifications = relationship("Notification", back_populates="plate_scan")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    title_message = Column(String, nullable=False)
    notification_type = Column(Enum(NotificationTypeEnum), default=NotificationTypeEnum.INFO, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    user_id = Column(Uuid, ForeignKey("auth_users.id"), nullable=False)
    plate_scan_id = Column(Uuid, ForeignKey("plate_scans.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("AuthUser", back_populates="notifications")
    plate_scan = relationship("PlateScan", back_populates="notifications")
