from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config.settings import settings
from app.core.security import ALGORITHM, create_access_token, hash_password, verify_password
from app.db.models import AuthRoleEnum, AuthUser, RecordStatusEnum, RoleEnum, UniversityPerson
from app.db.session import get_db
from app.schemas.auth import (
    AuthResponse,
    AuthUserResponse,
    UserLoginRequest,
    UserProfileUpdateRequest,
    UserRegisterRequest,
)

router = APIRouter()


def normalize_selected_role(raw_role: str) -> tuple[AuthRoleEnum, RoleEnum, str]:
    role = (raw_role or "").strip().upper()
    role_map = {
        "ADMIN": (AuthRoleEnum.ADMIN, RoleEnum.ADMIN, "ADMINISTRATIVO"),
        "ADMINISTRATIVE": (AuthRoleEnum.ADMIN, RoleEnum.ADMIN, "ADMINISTRATIVO"),
        "ADMINISTRATIVO": (AuthRoleEnum.ADMIN, RoleEnum.ADMIN, "ADMINISTRATIVO"),
        "OPERATOR": (AuthRoleEnum.OPERATOR, RoleEnum.STUDENT, "ESTUDIANTE"),
        "STUDENT": (AuthRoleEnum.OPERATOR, RoleEnum.STUDENT, "ESTUDIANTE"),
        "ESTUDIANTE": (AuthRoleEnum.OPERATOR, RoleEnum.STUDENT, "ESTUDIANTE"),
        "TEACHER": (AuthRoleEnum.OPERATOR, RoleEnum.TEACHER, "DOCENTE"),
        "DOCENTE": (AuthRoleEnum.OPERATOR, RoleEnum.TEACHER, "DOCENTE"),
    }
    if role not in role_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rol invalido. Usa Administrativo, Estudiante o Docente.",
        )
    return role_map[role]


def normalize_faculty(role: RoleEnum, faculty: str | None) -> str | None:
    if role != RoleEnum.STUDENT:
        return None
    value = (faculty or "").strip()
    return value or None


def get_catalog_role_label(role: AuthRoleEnum) -> str:
    role_map = {
        AuthRoleEnum.ADMIN: "ADMINISTRATIVO",
        AuthRoleEnum.OPERATOR: "ESTUDIANTE",
    }
    return role_map.get(role, role.value)


def get_person_role_label(person: UniversityPerson | None, auth_role: AuthRoleEnum) -> str:
    if person and person.role == RoleEnum.TEACHER:
        return "DOCENTE"
    if person and person.role == RoleEnum.ADMIN:
        return "ADMINISTRATIVO"
    if person and person.role == RoleEnum.STUDENT:
        return "ESTUDIANTE"
    return get_catalog_role_label(auth_role)


def build_user_response(user: AuthUser) -> AuthUserResponse:
    person = user.university_person
    phone = user.phone or (person.contact_info if person else None)
    return AuthUserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=phone,
        role=user.role,
        catalog_role=get_person_role_label(person, user.role),
        status=user.status,
        is_active=user.is_active,
        university_person_id=user.university_person_id,
        code=person.code if person else None,
        faculty=person.faculty if person else None,
        contact_info=phone,
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

    auth_role, person_role, _ = normalize_selected_role(user_in.role)
    faculty_value = normalize_faculty(person_role, user_in.faculty)
    phone_value = (user_in.phone or user_in.contact_info).strip()

    owner_result = await db.execute(
        select(UniversityPerson).where(UniversityPerson.code == user_in.code.strip())
    )
    university_person = owner_result.scalars().first()

    if university_person:
        university_person.full_name = user_in.full_name.strip()
        university_person.role = person_role
        university_person.faculty = faculty_value
        university_person.contact_info = phone_value
        university_person.is_active = True
        university_person.status = RecordStatusEnum.ACTIVE
    else:
        university_person = UniversityPerson(
            code=user_in.code.strip(),
            role=person_role,
            full_name=user_in.full_name.strip(),
            faculty=faculty_value,
            contact_info=phone_value,
            status=RecordStatusEnum.ACTIVE,
            is_active=True,
        )
        db.add(university_person)
        await db.flush()

    user = AuthUser(
        full_name=user_in.full_name.strip(),
        email=user_in.email.lower().strip(),
        phone=phone_value,
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

    auth_role, person_role, _ = normalize_selected_role(profile_in.role)
    faculty_value = normalize_faculty(person_role, profile_in.faculty)
    phone_value = (profile_in.phone or profile_in.contact_info).strip()

    current_user.full_name = profile_in.full_name.strip()
    current_user.email = profile_in.email.lower().strip()
    current_user.phone = phone_value
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
            faculty=faculty_value,
            contact_info=phone_value,
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
        person.faculty = faculty_value
        person.contact_info = phone_value
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
