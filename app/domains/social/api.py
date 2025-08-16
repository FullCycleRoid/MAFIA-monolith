# app/domains/social/api.py
from fastapi import APIRouter, Depends, HTTPException
from app.domains.auth.dependencies import get_current_user
from app.domains.social.schemas import SendGiftRequest, RateLinguisticRequest, ReportPlayerRequest
from app.domains.social.service import social_service
from app.domains.social.entities import GiftType


router = APIRouter()


@router.post("/gifts/send")
async def send_gift(request: SendGiftRequest, user=Depends(get_current_user)):
    """Отправить подарок другому игроку"""
    try:
        gift_type = GiftType(request.gift_type)
        success = await social_service.send_gift(
            from_user=user['id'],
            to_user=request.to_user,
            gift_type=gift_type,
            game_id=request.game_id
        )
        if not success:
            raise HTTPException(status_code=400, detail="Failed to send gift")
        return {"success": success}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid gift type")


@router.post("/linguistic/rate")
async def rate_linguistic_ability(
        request: RateLinguisticRequest,
        user=Depends(get_current_user)
):
    """Оценить лингвистические способности игрока"""
    if request.score < 1 or request.score > 5:
        raise HTTPException(status_code=400, detail="Score must be between 1 and 5")

    success = await social_service.rate_linguistic_ability(
        rater=user['id'],
        rated=request.rated_user,
        language=request.language,
        score=request.score,
        game_id=request.game_id
    )
    return {"success": success}


@router.post("/report")
async def report_player(
        request: ReportPlayerRequest,
        user=Depends(get_current_user)
):
    """Пожаловаться на игрока"""
    report_id = await social_service.report_player(
        reporter=user['id'],
        reported=request.reported_user,
        reason=request.reason,
        game_id=request.game_id,
        evidence=request.evidence
    )
    return {"report_id": report_id}


@router.get("/stats/{user_id}")
async def get_user_social_stats(user_id: str, user=Depends(get_current_user)):
    """Получить социальную статистику пользователя"""
    stats = social_service.user_stats.get(user_id)
    if not stats:
        return {"error": "No stats found"}
    return stats.__dict__
