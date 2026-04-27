import { ApiError, apiRequest } from "@src/services/apiClient";

export type ProPlanCode = "PRO_MONTHLY" | "PRO_QUARTERLY" | "PRO_YEARLY";

export const PAYMENT_ORDER_STORAGE_KEY = "getgoals.latestPaymentOrderCode";

export type CreateProOrderResponse = {
  orderCode: string;
  amount: number;
  checkoutUrl: string;
  qrCode: string;
  bankCode: string;
  bankAccountNo: string;
  bankAccountName: string;
  description: string;
  expiredAt: string;
};

export type PaymentStatus = "pending" | "paid" | "cancelled" | "expired" | "failed";

export type PaymentStatusResponse = {
  orderCode: string;
  status: PaymentStatus;
  amount: number;
  paidAt?: string | null;
  checkoutUrl?: string | null;
  qrCode?: string | null;
  expiredAt: string;
};

export type PaymentConfigStatus = {
  payosConfigured: boolean;
  bankTransferConfigured: boolean;
  missingKeys: string[];
  returnUrl: string;
  cancelUrl: string;
};

function getErrorPayload(error: ApiError) {
  return typeof error.payload === "object" && error.payload
    ? (error.payload as Record<string, unknown>)
    : null;
}

function toFriendlyMessage(error: unknown) {
  if (error instanceof ApiError) {
    const payload = getErrorPayload(error);
    const domainCode =
      typeof payload?.code === "string" ? payload.code : "";
    const payosCode =
      typeof payload?.payosCode === "string" ? payload.payosCode : "";

    if (
      domainCode === "PAYOS_GATEWAY_UNAVAILABLE" ||
      payosCode === "214"
    ) {
      return "Hiện chưa tạo được link thanh toán PayOS. Vui lòng kiểm tra cấu hình cổng thanh toán hoặc thử lại sau.";
    }

    if (error.message) {
      return error.message;
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Không tạo được phiên thanh toán. Vui lòng thử lại.";
}

export const paymentsService = {
  async createProOrder(planCode: ProPlanCode): Promise<CreateProOrderResponse> {
    try {
      return await apiRequest<CreateProOrderResponse>(
        "/api/payments/create-pro-order",
        {
          method: "POST",
          auth: true,
          body: JSON.stringify({ planCode }),
        },
      );
    } catch (error) {
      throw new Error(toFriendlyMessage(error));
    }
  },

  async getPaymentStatus(orderCode: string): Promise<PaymentStatusResponse> {
    return apiRequest<PaymentStatusResponse>(
      `/api/payments/status/${encodeURIComponent(orderCode)}`,
      { auth: true },
    );
  },

  async getConfigStatus(): Promise<PaymentConfigStatus> {
    return apiRequest<PaymentConfigStatus>("/api/payments/config-status");
  },

  rememberOrder(orderCode: string) {
    window.localStorage.setItem(PAYMENT_ORDER_STORAGE_KEY, orderCode);
  },

  getRememberedOrder() {
    return window.localStorage.getItem(PAYMENT_ORDER_STORAGE_KEY);
  },

  clearRememberedOrder() {
    window.localStorage.removeItem(PAYMENT_ORDER_STORAGE_KEY);
  },
};
