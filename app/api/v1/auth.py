import json
from pathlib import Path
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config.settings import settings
from app.core.security import ALGORITHM, create_access_token, hash_password, verify_password
from app.db.models import AuthUser, RecordStatusEnum, RoleEnum, UniversityPerson
from app.db.session import get_db
from app.schemas.auth import (
    AuthResponse,
    AuthUserResponse,
    UserLoginRequest,
    UserProfileUpdateRequest,
    UserRegisterRequest,
)

router = APIRouter()
USERS_FILE = Path(__file__).resolve().parents[3] / "usuarios.json"


def normalize_catalog_role(raw_role: str) -> tuple[AuthRoleEnum, RoleEnum]:
    role = raw_role.strip().upper()
    role_map = {
        "ADMIN": (AuthRoleEnum.ADMIN, RoleEnum.ADMIN),
        "ADMINISTRATIVO": (AuthRoleEnum.ADMIN, RoleEnum.ADMIN),
        "OPERATOR": (AuthRoleEnum.OPERATOR, RoleEnum.STUDENT),
        "OPERADOR": (AuthRoleEnum.OPERATOR, RoleEnum.STUDENT),
        "STUDENT": (AuthRoleEnum.OPERATOR, RoleEnum.STUDENT),
        "ESTUDIANTE": (AuthRoleEnum.OPERATOR, RoleEnum.STUDENT),
        "TEACHER": (AuthRoleEnum.OPERATOR, RoleEnum.TEACHER),
        "DOCENTE": (AuthRoleEnum.OPERATOR, RoleEnum.TEACHER),
    }
    if role not in role_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El rol '{raw_role}' no es valido dentro de usuarios.json.",
        )
    return role_map[role]


def get_catalog_user(code: str) -> tuple[AuthRoleEnum, RoleEnum]:
    if not USERS_FILE.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No existe el archivo usuarios.json para validar registros.",
        )

    try:
        users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="El archivo usuarios.json no tiene un formato JSON valido.",
        )

    normalized_code = code.strip()
    match = next(
        (
            item
            for item in users
            if str(item.get("code", "")).strip() == normalized_code
        ),
        None,
    )
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El registro no existe en usuarios.json. No se puede crear el perfil.",
        )

    if not match.get("role"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El registro existe en usuarios.json pero no tiene rol asignado.",
        )

    return normalize_catalog_role(str(match["role"]))


def build_user_response(user: AuthUser) -> AuthUserResponse:
    person = user.university_person
    return AuthUserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        status=user.status,
        is_active=user.is_active,
        university_person_id=user.university_person_id,
        code=person.code if person else None,
        faculty=person.faculty if person else None,
        contact_info=person.contact_info if person else None,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def get_current_user(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
) -> AuthUser:
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado.",
        )

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido.",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido.",
        )
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido.",
        )

    result = await db.execute(select(AuthUser).where(AuthUser.id == user_uuid))
    user = result.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no disponible.",
        )
    return user


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuthUser).where(AuthUser.email == user_in.email.lower().strip())
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este correo ya se encuentra registrado.",
        )

    auth_role, person_role = get_catalog_user(user_in.code)

    owner_result = await db.execute(
        select(UniversityPerson).where(UniversityPerson.code == user_in.code.strip())
    )
    university_person = owner_result.scalars().first()

    if university_person:
        university_person.full_name = user_in.full_name.strip()
        university_person.role = person_role
        university_person.faculty = user_in.faculty
        university_person.contact_info = user_in.contact_info
        university_person.is_active = True
        university_person.status = RecordStatusEnum.ACTIVE
    else:
        university_person = UniversityPerson(
            code=user_in.code.strip(),
            role=person_role,
            full_name=user_in.full_name.strip(),
            faculty=user_in.faculty,
            contact_info=user_in.contact_info,
            status=RecordStatusEnum.ACTIVE,
            is_active=True,
        )
        db.add(university_person)
        await db.flush()

    user = AuthUser(
        full_name=user_in.full_name.strip(),
        email=user_in.email.lower().strip(),
        password_hash=hash_password(user_in.password),
        role=auth_role,
        status=RecordStatusEnum.ACTIVE,
        is_active=True,
        university_person_id=university_person.id,
    )
    db.add(user)

    try:
        await db.commit()
        await db.refresh(user)
        await db.refresh(university_person)
        user.university_person = university_person
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo completar el registro.",
        )

    return AuthResponse(
        token=create_access_token(str(user.id)),
        user=build_user_response(user),
    )


@router.post("/login", response_model=AuthResponse)
async def login_user(
    credentials: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuthUser).where(AuthUser.email == credentials.email.lower().strip())
    )
    user = result.scalars().first()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario se encuentra inactivo.",
        )

    if user.university_person_id:
        person_result = await db.execute(
            select(UniversityPerson).where(UniversityPerson.id == user.university_person_id)
        )
        user.university_person = person_result.scalars().first()

    return AuthResponse(
        token=create_access_token(str(user.id)),
        user=build_user_response(user),
    )


@router.get("/me", response_model=AuthUserResponse)
async def get_my_profile(current_user: AuthUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.university_person_id:
        person_result = await db.execute(
            select(UniversityPerson).where(UniversityPerson.id == current_user.university_person_id)
        )
        current_user.university_person = person_result.scalars().first()

    return build_user_response(current_user)


@router.put("/me", response_model=AuthUserResponse)
async def update_my_profile(
    profile_in: UserProfileUpdateRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing_user_result = await db.execute(
        select(AuthUser).where(
            AuthUser.email == profile_in.email.lower().strip(),
            AuthUser.id != current_user.id,
        )
    )
    if existing_user_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ese correo ya esta siendo usado por otra cuenta.",
        )

    existing_person_result = await db.execute(
        select(UniversityPerson).where(
            UniversityPerson.code == profile_in.code.strip(),
            UniversityPerson.id != current_user.university_person_id,
        )
    )
    if existing_person_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ese registro ya pertenece a otra persona.",
        )

    auth_role, person_role = get_catalog_user(profile_in.code)

    current_user.full_name = profile_in.full_name.strip()
    current_user.email = profile_in.email.lower().strip()
    current_user.role = auth_role
    if profile_in.password:
        current_user.password_hash = hash_password(profile_in.password)

    person = None
    if current_user.university_person_id:
        person_result = await db.execute(
            select(UniversityPerson).where(UniversityPerson.id == current_user.university_person_id)
        )
        person = person_result.scalars().first()

    if not person:
        person = UniversityPerson(
            code=profile_in.code.strip(),
            role=person_role,
            full_name=profile_in.full_name.strip(),
            faculty=profile_in.faculty,
            contact_info=profile_in.contact_info,
            status=RecordStatusEnum.ACTIVE,
            is_active=True,
        )
        db.add(person)
        await db.flush()
        current_user.university_person_id = person.id
    else:
        person.code = profile_in.code.strip()
        person.role = person_role
        person.full_name = profile_in.full_name.strip()
        person.faculty = profile_in.faculty
        person.contact_info = profile_in.contact_info
        person.is_active = True
        person.status = RecordStatusEnum.ACTIVE

    try:
        await db.commit()
        await db.refresh(current_user)
        await db.refresh(person)
        current_user.university_person = person
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo actualizar el perfil.",
        )

    return build_user_response(current_user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_profile(
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.is_active = False
    current_user.status = RecordStatusEnum.INACTIVE

    if current_user.university_person_id:
        person_result = await db.execute(
            select(UniversityPerson).where(UniversityPerson.id == current_user.university_person_id)
        )
        person = person_result.scalars().first()
        if person:
            person.is_active = False
            person.status = RecordStatusEnum.INACTIVE

    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
