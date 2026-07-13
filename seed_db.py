import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.db.models import UniversityPerson, RoleEnum

async def seed():
    async with AsyncSessionLocal() as session:
        # Check if we already have data
        from sqlalchemy.future import select
        result = await session.execute(select(UniversityPerson))
        if result.scalars().first():
            print("La base de datos ya tiene datos iniciales.")
            return

        # Insert some dummy persons
        persons = [
            UniversityPerson(
                id=uuid.uuid4(),
                code="202011111", # Estudiante 1
                role=RoleEnum.STUDENT,
                full_name="Juan Perez",
                is_active=True
            ),
            UniversityPerson(
                id=uuid.uuid4(),
                code="202022222", # Estudiante 2
                role=RoleEnum.STUDENT,
                full_name="Maria Gomez",
                is_active=True
            ),
            UniversityPerson(
                id=uuid.uuid4(),
                code="DOC001", # Docente
                role=RoleEnum.TEACHER,
                full_name="Dr. Roberto Sanchez",
                is_active=True
            ),
            UniversityPerson(
                id=uuid.uuid4(),
                code="202033333", # Estudiante Inactivo
                role=RoleEnum.STUDENT,
                full_name="Carlos Inactivo",
                is_active=False
            )
        ]
        
        session.add_all(persons)
        await session.commit()
        
        print("¡Base de datos sembrada con éxito!")
        for p in persons:
            print(f"- {p.role.value}: {p.full_name} (Código: {p.code}, ID: {p.id})")

if __name__ == "__main__":
    asyncio.run(seed())
