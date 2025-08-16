from fastapi import APIRouter, Depends, HTTPException
from app.domains.auth.dependencies import get_current_user
from app.domains.economy.schemas import PurchaseRequest
from app.domains.economy.service import economy_service

router = APIRouter()


@router.post("/wallets")
async def create_wallet(user=Depends(get_current_user)):
    """Создать кошелек для пользователя"""
    return await economy_service.create_wallet(user['id'])


@router.get("/wallets/balance")
async def get_balance(user=Depends(get_current_user)):
    """Получить баланс кошелька"""
    from app.domains.economy.repository import get_wallet
    wallet = await get_wallet(user['id'])
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return {"balance": wallet.balance_cache}


@router.post("/purchase")
async def purchase_item(request: PurchaseRequest, user=Depends(get_current_user)):
    """Купить предмет за токены"""
    if request.item_type == "skin":
        success = await economy_service.purchase_skin(
            user['id'], request.item_id, request.price
        )
    elif request.item_type == "language":
        success = await economy_service.purchase_language_pack(
            user['id'], request.item_id, request.price
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid item type")

    if not success:
        raise HTTPException(status_code=400, detail="Purchase failed")

    return {"success": success}


@router.post("/referral/{referral_code}")
async def use_referral_code(referral_code: str, user=Depends(get_current_user)):
    """Использовать реферальный код"""
    # Найти владельца кода
    from app.domains.auth.repository import get_user_by_referral_code
    referrer = await get_user_by_referral_code(referral_code)

    if not referrer:
        raise HTTPException(status_code=404, detail="Invalid referral code")

    await economy_service.process_referral_reward(
        referrer_id=referrer.id,
        referred_id=user['id']
    )

    return {"success": True}