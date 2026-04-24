from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CreateProOrderRequest(BaseModel):
    userId: str | None = None
    planCode: str = "PRO_MONTHLY"


class CreateProOrderResponse(BaseModel):
    orderCode: str = ""
    amount: float = 0
    checkoutUrl: str = ""
    qrCode: str = ""
    bankCode: str = ""
    bankAccountNo: str = ""
    bankAccountName: str = ""
    description: str = ""
    expiredAt: datetime


class PayOSWebhookData(BaseModel):
    orderCode: int
    amount: int
    description: str = ""
    accountNumber: str = ""
    reference: str = ""
    transactionDateTime: str = ""
    currency: str = ""
    paymentLinkId: str = ""
    code: str = ""
    desc: str = ""
    counterAccountBankId: str = ""
    counterAccountBankName: str = ""
    counterAccountName: str = ""
    counterAccountNumber: str = ""
    virtualAccountName: str = ""
    virtualAccountNumber: str = ""


class PayOSWebhookRequest(BaseModel):
    code: str = ""
    desc: str = ""
    success: bool = False
    data: PayOSWebhookData = PayOSWebhookData(orderCode=0, amount=0)
    signature: str = ""


class ChatBody(BaseModel):
    message: str | None = None
