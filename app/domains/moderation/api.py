# app/domains/moderation/api.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.domains.auth.dependencies import get_current_user
from app.domains.moderation.service import moderation_service
from app.domains.moderation.entities import BanReason

router = APIRouter()


class BanUserRequest(BaseModel):
    user_id: str
    duration_hours: Optional[int]
    reason: str
    evidence: Optional[str] = None


class AppealRequest(BaseModel):
    appeal_text: str


@router.get("/status/{user_id}")
async def get_user_moderation_status(
    user_id: str,
    user=Depends(get_current_user)
):
    """Получить статус модерации пользователя"""
    status = await moderation_service.check_user_status(user_id)
    return status


@router.post("/appeal")
async def submit_ban_appeal(
    request: AppealRequest,
    user=Depends(get_current_user)
):
    """Подать апелляцию на бан"""
    result = await moderation_service.appeal_ban(
        user_id=user['id'],
        appeal_text=request.appeal_text
    )
    return {"status": result}


# Admin endpoints (требуют дополнительных прав)
@router.post("/admin/ban")
async def ban_user(
    request: BanUserRequest,
    user=Depends(get_current_user)
):
    """Забанить пользователя (только для модераторов)"""
    # TODO: Проверить права модератора
    ban = await moderation_service.ban_user(
        user_id=request.user_id,
        duration_hours=request.duration_hours,
        reason=BanReason(request.reason),
        issued_by=user['id'],
        evidence=request.evidence
    )
    return {"ban_id": ban.ban_id}
