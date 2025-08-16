# app/domains/matchmaking/api.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.domains.auth.dependencies import get_current_user
from app.domains.matchmaking.use_cases import (
    join_queue, leave_queue, create_private_lobby, join_private_lobby
)
from app.domains.matchmaking.service import lobby_service

router = APIRouter()


@router.post("/queue/join")
async def join_matchmaking_queue(
    mode: str,
    languages: List[str],
    user=Depends(get_current_user)
):
    """Присоединиться к очереди поиска игры"""
    try:
        result = await join_queue(user['id'], mode, languages)
        return {"status": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/queue/leave")
async def leave_matchmaking_queue(user=Depends(get_current_user)):
    """Выйти из очереди"""
    success = await leave_queue(user['id'])
    return {"success": success}


@router.post("/lobby/create")
async def create_lobby(user=Depends(get_current_user)):
    """Создать приватное лобби"""
    invite_code = await create_private_lobby(user['id'])
    return {"invite_code": invite_code}


@router.post("/lobby/join/{invite_code}")
async def join_lobby(invite_code: str, user=Depends(get_current_user)):
    """Присоединиться к лобби по коду"""
    success = await join_private_lobby(user['id'], invite_code)
    if not success:
        raise HTTPException(status_code=404, detail="Lobby not found")
    return {"success": success}


@router.post("/lobby/{lobby_id}/ready")
async def mark_ready(lobby_id: str, user=Depends(get_current_user)):
    """Отметиться готовым в лобби"""
    success = await lobby_service.player_ready(lobby_id, user['id'])
    return {"success": success}

