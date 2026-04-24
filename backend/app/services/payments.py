from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.models import PaymentOrder, User
from app.schemas.payments import CreateProOrderRequest, CreateProOrderResponse, PayOSWebhookData, PayOSWebhookRequest
from app.services.subscription import activate_paid_subscription, get_amount_by_plan_code, normalize_plan_code


logger = logging.getLogger(__name__)


def extract_payos_error_details(response_text: str) -> dict[str, str]:
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError:
        return {
            "code": "",
            "desc": response_text.strip()[:300]
            or "PayOS returned a non-JSON error payload.",
        }

    code = str(payload.get("code") or "").strip()
    desc = str(payload.get("desc") or "").strip()

    if not desc:
        data = payload.get("data")
        if isinstance(data, dict):
            desc = str(data.get("desc") or data.get("message") or "").strip()

    return {
        "code": code,
        "desc": desc or "PayOS returned an unexpected error payload.",
    }


def create_create_payment_signature(amount: int, cancel_url: str, description: str, order_code: int, return_url: str, checksum_key: str) -> str:
    raw_data = f"amount={amount}&cancelUrl={cancel_url}&description={description}&orderCode={order_code}&returnUrl={return_url}"
    return hmac.new(checksum_key.encode("utf-8"), raw_data.encode("utf-8"), hashlib.sha256).hexdigest()


def create_webhook_signature(data: PayOSWebhookData, checksum_key: str) -> str:
    values = {
        "accountNumber": data.accountNumber or "",
        "amount": str(data.amount),
        "code": data.code or "",
        "counterAccountBankId": data.counterAccountBankId or "",
        "counterAccountBankName": data.counterAccountBankName or "",
        "counterAccountName": data.counterAccountName or "",
        "counterAccountNumber": data.counterAccountNumber or "",
        "currency": data.currency or "",
        "desc": data.desc or "",
        "description": data.description or "",
        "orderCode": str(data.orderCode),
        "paymentLinkId": data.paymentLinkId or "",
        "reference": data.reference or "",
        "transactionDateTime": data.transactionDateTime or "",
        "virtualAccountName": data.virtualAccountName or "",
        "virtualAccountNumber": data.virtualAccountNumber or "",
    }
    raw_data = "&".join(f"{key}={value}" for key, value in sorted(values.items()))
    return hmac.new(checksum_key.encode("utf-8"), raw_data.encode("utf-8"), hashlib.sha256).hexdigest()


def is_valid_webhook_signature(webhook: PayOSWebhookRequest, checksum_key: str) -> bool:
    return hmac.compare_digest(create_webhook_signature(webhook.data, checksum_key), webhook.signature)


async def create_pro_order(db: Session, request: CreateProOrderRequest, resolved_user_id: int | None) -> CreateProOrderResponse:
    plan_code = normalize_plan_code(request.planCode)
    if not plan_code:
        raise ValueError("PlanCode khong hop le")

    user_id_value = resolved_user_id
    if not user_id_value:
        user_id_text = (request.userId or "").strip()
        try:
            user_id_value = int(user_id_text)
        except ValueError as exc:
            raise ValueError("UserId khong hop le") from exc

    user = db.get(User, user_id_value)
    if user is None:
        raise LookupError("Khong tim thay user")

    now = datetime.utcnow()
    has_active_pro = user.plan == "pro" and user.plan_expired_at and user.plan_expired_at > now
    if has_active_pro:
        raise RuntimeError("PRO_ALREADY_ACTIVE")

    amount = get_amount_by_plan_code(plan_code)
    expired_at = now + timedelta(minutes=30)
    if not settings.payos_client_id or not settings.payos_api_key or not settings.payos_checksum_key:
        raise ValueError("Thieu cau hinh PayOS trong backend.")

    internal_order_code = f"GGPRO_{hashlib.sha1(f'{user.id}-{now.isoformat()}'.encode()).hexdigest()[:8].upper()}"
    payos_order_code = int(datetime.utcnow().timestamp() * 1000)
    signature = create_create_payment_signature(
        int(amount),
        settings.payos_cancel_url,
        internal_order_code,
        payos_order_code,
        settings.payos_return_url,
        settings.payos_checksum_key,
    )
    request_body = {
        "orderCode": payos_order_code,
        "amount": int(amount),
        "description": internal_order_code,
        "returnUrl": settings.payos_return_url,
        "cancelUrl": settings.payos_cancel_url,
        "signature": signature,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api-merchant.payos.vn/v2/payment-requests",
                headers={"x-client-id": settings.payos_client_id, "x-api-key": settings.payos_api_key},
                json=request_body,
            )
            response_text = response.text
            if response.status_code >= 400:
                details = extract_payos_error_details(response_text)
                logger.error(
                    "PayOS create payment failed. status=%s payos_code=%s payos_desc=%s user_id=%s plan_code=%s order_code=%s return_url=%s cancel_url=%s",
                    response.status_code,
                    details["code"] or "unknown",
                    details["desc"],
                    user.id,
                    plan_code,
                    internal_order_code,
                    settings.payos_return_url,
                    settings.payos_cancel_url,
                )
                raise RuntimeError(
                    f"PAYOS_CREATE_FAILED::{json.dumps(details, ensure_ascii=False)}"
                )
            try:
                payload = json.loads(response_text)
            except json.JSONDecodeError as exc:
                details = extract_payos_error_details(response_text)
                logger.error(
                    "PayOS create payment returned non-JSON payload. user_id=%s plan_code=%s order_code=%s payos_desc=%s",
                    user.id,
                    plan_code,
                    internal_order_code,
                    details["desc"],
                )
                raise RuntimeError(
                    f"PAYOS_CREATE_FAILED::{json.dumps(details, ensure_ascii=False)}"
                ) from exc
            data = payload.get("data")
            if not isinstance(data, dict):
                details = extract_payos_error_details(response_text)
                logger.error(
                    "PayOS create payment returned unexpected payload. user_id=%s plan_code=%s order_code=%s payos_code=%s payos_desc=%s",
                    user.id,
                    plan_code,
                    internal_order_code,
                    details["code"] or "unknown",
                    details["desc"],
                )
                raise RuntimeError(
                    f"PAYOS_CREATE_FAILED::{json.dumps(details, ensure_ascii=False)}"
                )
    except httpx.HTTPError as exc:
        raise ValueError("Khong tao duoc link thanh toan PayOS") from exc

    order = PaymentOrder(
        user_id=user.id,
        plan_code=plan_code,
        order_code=internal_order_code,
        payos_order_code=payos_order_code,
        amount=amount,
        status="pending",
        checkout_url=data.get("checkoutUrl"),
        qr_code=data.get("qrCode"),
        payos_payment_link_id=data.get("paymentLinkId"),
        transfer_content=internal_order_code,
        created_at=datetime.utcnow(),
        expired_at=expired_at,
    )
    try:
        db.add(order)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to persist PayOS order %s: %s", internal_order_code, exc)
        raise RuntimeError("PAYOS_ORDER_SAVE_FAILED") from exc
    return CreateProOrderResponse(
        orderCode=order.order_code,
        amount=float(order.amount),
        checkoutUrl=data.get("checkoutUrl") or "",
        qrCode=data.get("qrCode") or "",
        bankCode=data.get("bin") or settings.payment_bank_code,
        bankAccountNo=data.get("accountNumber") or settings.payment_bank_account_no,
        bankAccountName=data.get("accountName") or settings.payment_bank_account_name,
        description=order.transfer_content or "",
        expiredAt=order.expired_at,
    )


def get_config_status() -> dict[str, Any]:
    missing_keys = []
    if not settings.payos_client_id:
        missing_keys.append("PayOS:ClientId")
    if not settings.payos_api_key:
        missing_keys.append("PayOS:ApiKey")
    if not settings.payos_checksum_key:
        missing_keys.append("PayOS:ChecksumKey")
    if not settings.payment_bank_account_no:
        missing_keys.append("Payment:BankAccountNo")
    if not settings.payment_bank_account_name:
        missing_keys.append("Payment:BankAccountName")
    return {
        "payosConfigured": not any(item.startswith("PayOS:") for item in missing_keys),
        "bankTransferConfigured": not any(item.startswith("Payment:") for item in missing_keys),
        "missingKeys": missing_keys,
        "returnUrl": settings.payos_return_url,
        "cancelUrl": settings.payos_cancel_url,
    }


def find_order_by_webhook(db: Session, webhook: PayOSWebhookRequest) -> PaymentOrder | None:
    order = db.scalar(select(PaymentOrder).where(PaymentOrder.payos_order_code == webhook.data.orderCode))
    if order is None and webhook.data.description:
        order = db.scalar(select(PaymentOrder).where(PaymentOrder.order_code == webhook.data.description))
    return order


async def sync_pending_order_from_payos(db: Session, order: PaymentOrder) -> None:
    if order.payos_order_code is None or not settings.payos_client_id or not settings.payos_api_key:
        return
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"https://api-merchant.payos.vn/v2/payment-requests/{order.payos_order_code}",
                headers={"x-client-id": settings.payos_client_id, "x-api-key": settings.payos_api_key},
            )
            if response.status_code >= 400:
                logger.warning("Get payOS payment status failed. status=%s body=%s", response.status_code, response.text)
                return
            payload = response.json()
        data = payload.get("data", {})
        payos_status = str(data.get("status", "")).upper()
        if payos_status == "PAID":
            if order.status != "paid":
                order.status = "paid"
                order.paid_at = order.paid_at or datetime.utcnow()
                db.commit()
                activate_paid_subscription(db, order)
        elif payos_status == "CANCELLED":
            if order.status == "pending":
                order.status = "cancelled"
                db.commit()
        elif order.expired_at <= datetime.utcnow() and order.status == "pending":
            order.status = "expired"
            db.commit()
    except Exception as exc:  # pragma: no cover
        logger.exception("Error syncing payOS order %s: %s", order.order_code, exc)
