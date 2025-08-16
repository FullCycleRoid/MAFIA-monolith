from fastapi import APIRouter, Depends
from . import service
from app.domains.auth.dependencies import get_current_user


router = APIRouter()


@router.post("/wallets")
async def create_wallet(user=Depends(get_current_user)):
    return await service.create_wallet(user['sub'])

@router.post("/rewards")
async def award_tokens():
    return {"status": "awarded"}
