from decimal import Decimal
from typing import Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field, validator

from app.domains.auth.dependencies import get_current_user
from app.domains.economy.service import economy_service
from app.shared.utils.logger import get_logger

logger = get_logger(__name__)


router = APIRouter()


# Endpoints
@router.post("/wallets", response_model=CreateWalletResponse)
async def create_wallet(user=Depends(get_current_user)):
    """Create TON wallet for user"""
    try:
        wallet = await economy_service.create_wallet(user["id"])
        return CreateWalletResponse(**wallet)
    except Exception as e:
        logger.error(f"Wallet creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create wallet")


@router.get("/wallets/balance", response_model=BalanceResponse)
async def get_balance(user=Depends(get_current_user)):
    """Get user's token balance"""
    balance = await economy_service.get_balance(user["id"])
    if "error" in balance:
        raise HTTPException(status_code=404, detail=balance["error"])
    return BalanceResponse(**balance)


@router.post("/withdraw")
async def withdraw_tokens(
    request: WithdrawRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
):
    """Withdraw tokens from off-chain to on-chain wallet"""
    try:
        tx_hash = await economy_service.withdraw_to_chain(user["id"], request.amount)

        if not tx_hash:
            raise HTTPException(
                status_code=400, detail="Insufficient balance or withdrawal failed"
            )

        return {
            "success": True,
            "tx_hash": tx_hash,
            "amount": request.amount,
            "status": "processing",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Withdrawal error: {e}")
        raise HTTPException(status_code=500, detail="Withdrawal failed")


@router.post("/purchase")
async def purchase_item(request: PurchaseRequest, user=Depends(get_current_user)):
    """Purchase in-game item with tokens"""
    success = await economy_service.purchase_item(
        user["id"], request.item_type, request.item_id, request.price
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Purchase failed. Insufficient balance or item unavailable.",
        )

    return {"success": True, "item_id": request.item_id}


@router.post("/gift/send")
async def send_gift(request: SendGiftRequest, user=Depends(get_current_user)):
    """Send tokens as gift to another user"""
    try:
        success = await economy_service.send_gift_tokens(
            from_user=user["id"], to_user=request.to_user, amount=request.amount
        )

        if not success:
            raise HTTPException(status_code=400, detail="Gift failed. Check balance.")

        return {
            "success": True,
            "amount_sent": request.amount,
            "to_user": request.to_user,
        }

    except Exception as e:
        logger.error(f"Gift error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send gift")


@router.post("/claim/daily")
async def claim_daily_reward(user=Depends(get_current_user)):
    """Claim daily login reward"""
    success = await economy_service.claim_daily_reward(user["id"])

    if not success:
        raise HTTPException(
            status_code=400, detail="Already claimed today. Come back tomorrow!"
        )

    return {
        "success": True,
        "amount": economy_service.rewards_config["daily_claim"],
        "next_claim_in": 86400,  # seconds
    }


@router.post("/referral/{referral_code}")
async def use_referral_code(referral_code: str, user=Depends(get_current_user)):
    """Use referral code for bonus tokens"""
    from app.domains.auth.repository import get_user_by_referral_code

    referrer = await get_user_by_referral_code(referral_code)
    if not referrer:
        raise HTTPException(status_code=404, detail="Invalid referral code")

    if referrer.id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot use own referral code")

    await economy_service.process_referral_reward(
        referrer_id=referrer.id, referred_id=user["id"]
    )

    return {
        "success": True,
        "bonus_received": economy_service.rewards_config["referred_bonus"],
    }


@router.get("/transactions")
async def get_transaction_history(limit: int = 50, user=Depends(get_current_user)):
    """Get user's transaction history"""
    transactions = await economy_service.get_transaction_history(user["id"], limit)
    return {"transactions": transactions}


@router.get("/leaderboard")
async def get_leaderboard(period: str = "all", limit: int = 100):
    """Get token leaderboard"""
    if period not in ["all", "daily", "weekly", "monthly"]:
        raise HTTPException(status_code=400, detail="Invalid period")

    leaderboard = await economy_service.get_leaderboard(period, limit)
    return {"leaderboard": leaderboard, "period": period}


@router.post("/transfer/jetton")
async def transfer_jettons_direct(
    request: TransferRequest, user=Depends(get_current_user)
):
    """Direct on-chain jetton transfer (requires user's mnemonic)"""
    # This endpoint would be used in a more advanced implementation
    # where users can directly transfer on-chain tokens
    raise HTTPException(
        status_code=501,
        detail="Direct transfers not yet implemented. Use withdrawal system.",
    )


@router.get("/price")
async def get_token_price():
    """Get current $MAFIA token price"""
    # This would fetch from DEX or price oracle
    return {
        "symbol": "MAFIA",
        "price_usd": 0.001,
        "price_ton": 0.0002,
        "volume_24h": 50000,
        "market_cap": 1000000,
        "total_supply": 1000000000,
        "circulating_supply": 100000000,
    }


@router.post("/verify/{tx_hash}")
async def verify_transaction(tx_hash: str, user=Depends(get_current_user)):
    """Verify blockchain transaction"""
    result = await economy_service.verify_payment(tx_hash)
    return result


# Admin endpoints
@router.post("/admin/mint", tags=["admin"])
async def mint_tokens(
    user_id: str, amount: int, reason: str, admin=Depends(get_current_user)
):
    """Mint tokens for user (admin only)"""
    # TODO: Check admin privileges
    if not admin.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    success = await economy_service.add_tokens(user_id, amount, f"admin_mint:{reason}")

    return {
        "success": success,
        "user_id": user_id,
        "amount": amount,
        "minted_by": admin["id"],
    }


@router.post("/admin/burn", tags=["admin"])
async def burn_tokens(
    user_id: str, amount: int, reason: str, admin=Depends(get_current_user)
):
    """Burn tokens from user (admin only)"""
    # TODO: Check admin privileges
    if not admin.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    success = await economy_service.spend_tokens(
        user_id, amount, f"admin_burn:{reason}"
    )

    if not success:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    return {
        "success": success,
        "user_id": user_id,
        "amount": amount,
        "burned_by": admin["id"],
    }


# Webhook for TON blockchain events
@router.post("/webhook/ton", include_in_schema=False)
async def ton_webhook(data: Dict):
    """Handle TON blockchain events"""
    # Process incoming transfers, confirmations, etc.
    logger.info(f"TON webhook received: {data}")

    # Validate webhook signature
    # Process the event
    # Update database accordingly

    return {"status": "processed"}
