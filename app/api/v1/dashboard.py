from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Vehicle
from app.db.session import get_db

router = APIRouter()


@router.get("/summary")
async def get_dashboard_summary(
    registered_by_user_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Vehicle).options(selectinload(Vehicle.owner)).order_by(Vehicle.created_at.desc())
    if registered_by_user_id:
        query = query.where(Vehicle.registered_by_user_id == registered_by_user_id)

    result = await db.execute(query)
    vehicles = list(result.scalars().all())

    total_query = select(func.count(Vehicle.id))
    if registered_by_user_id:
        total_query = total_query.where(Vehicle.registered_by_user_id == registered_by_user_id)
    total_result = await db.execute(total_query)
    total_vehicles = total_result.scalar() or 0

    active_vehicles = len(
        [
            vehicle
            for vehicle in vehicles
            if getattr(vehicle.status, "value", vehicle.status) == "ACTIVE"
        ]
    )

    return {
        "total_vehicles": total_vehicles,
        "active_vehicles": active_vehicles,
        "my_vehicles": vehicles[:12],
    }
