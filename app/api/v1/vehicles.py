from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from app.db.session import get_db
from app.db.models import Vehicle, UniversityPerson
from app.schemas.vehicle import VehicleResponse, VehicleCreate

router = APIRouter()

@router.get("/by-plate/{plate}", response_model=VehicleResponse)
async def get_vehicle_by_plate(plate: str, db: AsyncSession = Depends(get_db)):
    """
    Busca un vehículo por su placa. Retorna los datos del vehículo y del dueño si existe.
    (SPEC-003)
    """
    # Convertir placa a mayúsculas para normalizar la búsqueda
    plate = plate.upper().strip()
    
    # Hacemos selectinload para traer también los datos del dueño en la misma consulta
    result = await db.execute(
        select(Vehicle)
        .options(selectinload(Vehicle.owner))
        .where(Vehicle.license_plate == plate)
    )
    vehicle = result.scalars().first()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehículo no registrado."
        )
        
    return vehicle

@router.post("/", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(vehicle_in: VehicleCreate, db: AsyncSession = Depends(get_db)):
    """
    Registra un nuevo vehículo asociado a un universitario.
    (SPEC-004)
    """
    # Primero verificamos si el dueño existe y está activo
    result = await db.execute(select(UniversityPerson).where(UniversityPerson.id == vehicle_in.owner_id))
    owner = result.scalars().first()
    
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La persona especificada (owner_id) no existe."
        )
        
    if not owner.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se pueden registrar vehículos a nombre de una persona inactiva."
        )

    new_vehicle = Vehicle(
        license_plate=vehicle_in.license_plate.upper().strip(),
        owner_id=vehicle_in.owner_id
    )
    db.add(new_vehicle)
    
    try:
        await db.commit()
        await db.refresh(new_vehicle)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta placa ya se encuentra registrada en el sistema."
        )
        
    # Recargar con el dueño para la respuesta
    result = await db.execute(
        select(Vehicle)
        .options(selectinload(Vehicle.owner))
        .where(Vehicle.id == new_vehicle.id)
    )
    return result.scalars().first()
