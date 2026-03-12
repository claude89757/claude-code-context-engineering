import asyncio

from fastapi import APIRouter

from backend.services.scheduler import get_patrol_status, run_patrol

router = APIRouter(prefix="/api/patrol", tags=["patrol"])


@router.get("/status")
def patrol_status():
    return get_patrol_status()


@router.post("/trigger")
async def trigger_patrol():
    asyncio.create_task(run_patrol())
    return {"message": "Patrol triggered"}
