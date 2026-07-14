import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.models import RecordStatusEnum, UniversityPerson, Vehicle
from app.db.session import get_db
from app.schemas.vehicle import VehicleCreate, VehicleResponse

router = APIRouter()

UPLOADS_DIR = Path(__file__).resolve().parents[3] / "uploads" / "vehicles"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


async def resolve_owner(vehicle_in: VehicleCreate, db: AsyncSession) -> UniversityPerson:
    if vehicle_in.owner_id:
        result = await db.execute(
            select(UniversityPerson).where(UniversityPerson.id == vehicle_in.owner_id)
        )
        owner = result.scalars().first()
        if not owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La persona especificada (owner_id) no existe.",
            )
        return owner

    if not vehicle_in.owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes enviar owner_id o los datos completos del propietario.",
        )

    owner_data = vehicle_in.owner
    result = await db.execute(
        select(UniversityPerson).where(UniversityPerson.code == owner_data.code.strip())
    )
    owner = result.scalars().first()

    if owner:
        owner.full_name = owner_data.full_name.strip()
        owner.role = owner_data.role
        owner.document_id = owner_data.document_id
        owner.faculty = owner_data.faculty
        owner.contact_info = owner_data.contact_info
        owner.status = owner_data.status
        owner.is_active = owner_data.is_active
        return owner

    owner = UniversityPerson(
        code=owner_data.code.strip(),
        full_name=owner_data.full_name.strip(),
        role=owner_data.role,
        document_id=owner_data.document_id,
        faculty=owner_data.faculty,
        contact_info=owner_data.contact_info,
        status=owner_data.status,
        is_active=owner_data.is_active,
    )
    db.add(owner)
    await db.flush()
    return owner


async def save_vehicle_photo(photo: UploadFile | None) -> str | None:
    if not photo or not photo.filename:
        return None

    extension = Path(photo.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4()}{extension}"
    target_path = UPLOADS_DIR / filename
    target_path.write_bytes(await photo.read())
    return f"/uploads/vehicles/{filename}"


async def get_vehicle_with_owner(vehicle_id, db: AsyncSession):
    result = await db.execute(
        select(Vehicle)
        .options(selectinload(Vehicle.owner))
        .where(Vehicle.id == vehicle_id)
    )
    return result.scalars().first()


def apply_vehicle_changes(vehicle: Vehicle, vehicle_in: VehicleCreate):
    vehicle.license_plate = vehicle_in.license_plate.upper().strip()
    vehicle.brand = vehicle_in.brand.strip()
    vehicle.model = vehicle_in.model.strip()
    vehicle.color = vehicle_in.color.strip()
    vehicle.vehicle_type = vehicle_in.vehicle_type
    vehicle.year = vehicle_in.year.strip() if vehicle_in.year else None
    vehicle.observation = vehicle_in.observation.strip() if vehicle_in.observation else None
    vehicle.status = vehicle_in.status
    if vehicle_in.vehicle_photo_path is not None:
      vehicle.vehicle_photo_path = vehicle_in.vehicle_photo_path
    vehicle.registered_by_user_id = vehicle_in.registered_by_user_id


@router.get("/", response_model=list[VehicleResponse])
async def list_vehicles(
    registered_by_user_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Vehicle).options(selectinload(Vehicle.owner)).order_by(Vehicle.created_at.desc())
    if registered_by_user_id:
        query = query.where(Vehicle.registered_by_user_id == registered_by_user_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/by-plate/{plate}", response_model=VehicleResponse)
async def get_vehicle_by_plate(plate: str, db: AsyncSession = Depends(get_db)):
    plate = plate.upper().strip()
    result = await db.execute(
        select(Vehicle)
        .options(selectinload(Vehicle.owner))
        .where(Vehicle.license_plate == plate)
    )
    vehicle = result.scalars().first()

    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehiculo no registrado en la facultad.",
        )
    return vehicle


@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle_detail(vehicle_id: str, db: AsyncSession = Depends(get_db)):
    vehicle = await get_vehicle_with_owner(vehicle_id, db)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehiculo no encontrado.",
        )
    return vehicle


@router.post("/", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(vehicle_in: VehicleCreate, db: AsyncSession = Depends(get_db)):
    owner = await resolve_owner(vehicle_in, db)

    if not owner.is_active or owner.status == RecordStatusEnum.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se pueden registrar vehiculos a nombre de una persona inactiva.",
        )

    new_vehicle = Vehicle(owner_id=owner.id)
    apply_vehicle_changes(new_vehicle, vehicle_in)
    db.add(new_vehicle)

    try:
        await db.commit()
        await db.refresh(new_vehicle)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta placa ya se encuentra registrada en el sistema.",
        )

    return await get_vehicle_with_owner(new_vehicle.id, db)


@router.post("/with-photo", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle_with_photo(
    vehicle_data: str = Form(...),
    photo: UploadFile | None = File(default=None),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = json.loads(vehicle_data)
        vehicle_in = VehicleCreate(**payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Datos del vehiculo invalidos: {exc}",
        ) from exc

    vehicle_in.vehicle_photo_path = await save_vehicle_photo(photo)
    return await create_vehicle(vehicle_in, db)


@router.put("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: str,
    vehicle_in: VehicleCreate,
    db: AsyncSession = Depends(get_db),
):
    vehicle = await get_vehicle_with_owner(vehicle_id, db)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehiculo no encontrado.",
        )

    owner = await resolve_owner(vehicle_in, db)
    if not owner.is_active or owner.status == RecordStatusEnum.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se pueden registrar vehiculos a nombre de una persona inactiva.",
        )

    vehicle.owner_id = owner.id
    apply_vehicle_changes(vehicle, vehicle_in)

    try:
        await db.commit()
        await db.refresh(vehicle)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo actualizar el vehiculo.",
        )

    return await get_vehicle_with_owner(vehicle.id, db)


@router.put("/{vehicle_id}/with-photo", response_model=VehicleResponse)
async def update_vehicle_with_photo(
    vehicle_id: str,
    vehicle_data: str = Form(...),
    photo: UploadFile | None = File(default=None),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = json.loads(vehicle_data)
        vehicle_in = VehicleCreate(**payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Datos del vehiculo invalidos: {exc}",
        ) from exc

    if photo:
        vehicle_in.vehicle_photo_path = await save_vehicle_photo(photo)

    return await update_vehicle(vehicle_id, vehicle_in, db)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(vehicle_id: str, db: AsyncSession = Depends(get_db)):
    vehicle = await get_vehicle_with_owner(vehicle_id, db)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehiculo no encontrado.",
        )

    await db.delete(vehicle)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
