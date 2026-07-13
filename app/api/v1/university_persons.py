from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import UniversityPerson
from app.schemas.person import PersonResponse

router = APIRouter()

@router.get("/validate/{code}", response_model=PersonResponse)
async def validate_person(code: str, db: AsyncSession = Depends(get_db)):
    """
    Valida si un código universitario existe y está activo.
    (SPEC-004)
    """
    result = await db.execute(select(UniversityPerson).where(UniversityPerson.code == code))
    person = result.scalars().first()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Código universitario no encontrado en la base de datos."
        )
        
    if not person.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La persona asociada a este código se encuentra inactiva."
        )
        
    return person
