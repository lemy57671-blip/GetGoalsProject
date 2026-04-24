from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_optional_current_user_id
from app.db.session import get_db
from app.models import PaymentOrder, User
from app.schemas.payments import CreateProOrderRequest, PayOSWebhookRequest
from app.services.payments import (
    create_pro_order,
    extract_payos_error_details,
    find_order_by_webhook,
    get_config_status,
    is_valid_webhook_signature,
    sync_pending_order_from_payos,
)
from app.services.subscription import activate_paid_subscription


router = APIRouter()


def _find_payment_order(db: Session, order_code: str) -> PaymentOrder | None:
    order = db.scalar(select(PaymentOrder).where(PaymentOrder.order_code == order_code))
    if order is not None:
        return order

    if order_code.strip().isdigit():
        return db.scalar(
            select(PaymentOrder).where(PaymentOrder.payos_order_code == int(order_code.strip()))
        )

    return None


@router.post("/api/payments/create-pro-order")
@router.post("/api/Payments/create-pro-order")
async def create_order(payload: CreateProOrderRequest, db: Session = Depends(get_db), claim_user_id: int | None = Depends(get_optional_current_user_id)):
    try:
        return await create_pro_order(db, payload, claim_user_id)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"message": str(exc)})
    except LookupError as exc:
        return JSONResponse(status_code=404, content={"message": str(exc)})
    except RuntimeError as exc:
        message = str(exc)
        if message == "PRO_ALREADY_ACTIVE":
            user_id = claim_user_id
            if not user_id:
                try:
                    user_id = int((payload.userId or "").strip())
                except ValueError:
                    user_id = None
            user = db.get(User, user_id) if user_id else None
            return JSONResponse(
                status_code=409,
                content={
                    "message": "Tai khoan cua ban dang co goi Pro con hieu luc. Ban chi co the dang ky lai khi goi hien tai da het han.",
                    "code": "PRO_ALREADY_ACTIVE",
                    "expiresAt": user.plan_expired_at.isoformat() if user and user.plan_expired_at else None,
                },
            )
        if message.startswith("PAYOS_CREATE_FAILED::"):
            details = extract_payos_error_details(
                message.removeprefix("PAYOS_CREATE_FAILED::")
            )
            payos_code = details.get("code") or None
            payos_description = details.get("desc") or None
            user_message = "Khong tao duoc link thanh toan PayOS. Vui long thu lai sau."
            code = "PAYOS_CREATE_FAILED"

            if payos_code == "214":
                user_message = (
                    "Hien chua tao duoc link thanh toan PayOS. "
                    "Vui long kiem tra cau hinh cong thanh toan hoac thu lai sau."
                )
                code = "PAYOS_GATEWAY_UNAVAILABLE"

            return JSONResponse(
                status_code=400,
                content={
                    "message": user_message,
                    "code": code,
                    "payosCode": payos_code,
                    "payosDescription": payos_description,
                },
            )
        if message == "PAYOS_ORDER_SAVE_FAILED":
            return JSONResponse(
                status_code=500,
                content={"message": "Khong luu duoc don thanh toan PayOS"},
            )
        raise


@router.get("/api/payments/config-status")
@router.get("/api/Payments/config-status")
def config_status():
    return get_config_status()


@router.post("/api/payments/payos-webhook")
@router.post("/api/Payments/payos-webhook")
def payos_webhook(payload: PayOSWebhookRequest, db: Session = Depends(get_db)):
    from app.core.config import settings

    if payload is None or payload.data is None:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid webhook body"})
    if not settings.payos_checksum_key:
        return JSONResponse(status_code=400, content={"success": False, "message": "Missing checksum key"})
    if not is_valid_webhook_signature(payload, settings.payos_checksum_key):
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid signature"})
    order = find_order_by_webhook(db, payload)
    if order is None:
        return {"success": True}
    if order.status == "paid":
        return {"success": True}
    if float(order.amount) != payload.data.amount:
        return {"success": True}
    order.status = "paid"
    order.paid_at = datetime.utcnow()
    order.paid_by_webhook_signature = payload.signature
    db.commit()
    activate_paid_subscription(db, order)
    return {"success": True}


@router.get("/api/payments/status/{order_code}")
@router.get("/api/Payments/status/{order_code}")
async def payment_status(order_code: str, db: Session = Depends(get_db)):
    order = _find_payment_order(db, order_code)
    if order is None:
        return JSONResponse(status_code=404, content={"message": "Order not found"})
    if order.status == "pending":
        if order.expired_at <= datetime.utcnow():
            order.status = "expired"
            db.commit()
        else:
            await sync_pending_order_from_payos(db, order)
    return {
        "orderCode": order.order_code,
        "status": order.status,
        "amount": float(order.amount),
        "paidAt": order.paid_at,
        "checkoutUrl": order.checkout_url,
        "qrCode": order.qr_code,
        "expiredAt": order.expired_at,
    }


@router.get("/api/payments/{order_code}")
@router.get("/api/Payments/{order_code}")
def get_order(order_code: str, db: Session = Depends(get_db)):
    order = _find_payment_order(db, order_code)
    if order is None:
        return JSONResponse(status_code=404, content={"message": "Order not found"})
    return {
        "id": order.id,
        "orderCode": order.order_code,
        "userId": order.user_id,
        "planCode": order.plan_code,
        "amount": float(order.amount),
        "status": order.status,
        "payOsOrderCode": order.payos_order_code,
        "checkoutUrl": order.checkout_url,
        "qrCode": order.qr_code,
        "payOsPaymentLinkId": order.payos_payment_link_id,
        "paidByWebhookSignature": order.paid_by_webhook_signature,
        "transferContent": order.transfer_content,
        "createdAt": order.created_at,
        "expiredAt": order.expired_at,
        "paidAt": order.paid_at,
    }
