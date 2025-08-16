from fastapi import APIRouter, Depends
from . import service
from app.domains.auth.dependencies import get_current_user


router = APIRouter()

@router.post("/rooms")
async def create_room(game_id: str, user=Depends(get_current_user)):
    return await service.create_room(game_id)

@router.get("/rooms/{room_id}")
async def get_room(room_id: str, user=Depends(get_current_user)):
    return await service.get_room(room_id)