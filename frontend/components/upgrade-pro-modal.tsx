"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Check,
  CheckCircle,
  Clock,
  Copy,
  Crown,
  ExternalLink,
  Loader2,
  RefreshCcw,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAuthSession } from "@src/hooks/useAuthSession";
import {
  paymentsService,
  type CreateProOrderResponse,
  type PaymentConfigStatus,
  type ProPlanCode,
} from "@src/services/paymentsService";

interface UpgradeProModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  planCode?: ProPlanCode;
  planName?: string;
  amount?: number;
}

type PaymentState = "idle" | "creating" | "pending" | "paid" | "expired" | "failed";

function formatTime(seconds: number) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, "0")}:${secs
    .toString()
    .padStart(2, "0")}`;
}

export function UpgradeProModal({
  open,
  onOpenChange,
  planCode = "PRO_MONTHLY",
  planName = "Pro thang",
  amount = 99000,
}: UpgradeProModalProps) {
  const { isAuthenticated, refreshSession } = useAuthSession();
  const [payment, setPayment] = useState<CreateProOrderResponse | null>(null);
  const [paymentState, setPaymentState] = useState<PaymentState>("idle");
  const [message, setMessage] = useState("");
  const [copied, setCopied] = useState<string | null>(null);
  const [countdown, setCountdown] = useState(0);
  const [configStatus, setConfigStatus] = useState<PaymentConfigStatus | null>(null);

  const amountLabel = useMemo(
    () => `${(payment?.amount || amount).toLocaleString("vi-VN")} VND`,
    [payment?.amount, amount],
  );
  const qrIsImage =
    !!payment?.qrCode &&
    (payment.qrCode.startsWith("http://") ||
      payment.qrCode.startsWith("https://") ||
      payment.qrCode.startsWith("data:image"));
  const paymentReady = Boolean(
    configStatus?.payosConfigured && configStatus?.bankTransferConfigured,
  );

  useEffect(() => {
    if (!open) return;

    let cancelled = false;

    async function loadConfig() {
      try {
        const status = await paymentsService.getConfigStatus();
        if (!cancelled) {
          setConfigStatus(status);
        }
      } catch {
        if (!cancelled) {
          setConfigStatus(null);
        }
      }
    }

    void loadConfig();

    return () => {
      cancelled = true;
    };
  }, [open]);

  useEffect(() => {
    if (!payment?.expiredAt || paymentState !== "pending") return;

    const timer = window.setInterval(() => {
      const secondsLeft = Math.max(
        0,
        Math.floor((new Date(payment.expiredAt).getTime() - Date.now()) / 1000),
      );

      setCountdown(secondsLeft);

      if (secondsLeft <= 0) {
        setPaymentState("expired");
        setMessage("Ma thanh toan da het han.");
        window.clearInterval(timer);
      }
    }, 1000);

    return () => window.clearInterval(timer);
  }, [payment?.expiredAt, paymentState]);

  useEffect(() => {
    if (!payment?.orderCode || paymentState !== "pending") return;

    const timer = window.setInterval(async () => {
      try {
        const status = await paymentsService.getPaymentStatus(payment.orderCode);

        if (status.status === "paid") {
          setPaymentState("paid");
          setMessage("Thanh toan da duoc xac nhan thanh cong.");
          paymentsService.clearRememberedOrder();
          void refreshSession();
          try {
            window.localStorage.setItem(
              "getgoals_pro_upgrade_success",
              Date.now().toString(),
            );
            window.dispatchEvent(new CustomEvent("getgoals:pro-upgraded"));
          } catch {
            // The subscription is already activated; the toast signal is best-effort.
          }
          window.clearInterval(timer);
          window.setTimeout(() => onOpenChange(false), 1200);
        } else if (status.status === "expired") {
          setPaymentState("expired");
          setMessage("Don thanh toan da het han.");
          window.clearInterval(timer);
        } else if (status.status === "cancelled" || status.status === "failed") {
          setPaymentState("failed");
          setMessage("Thanh toan chua hoan tat.");
          window.clearInterval(timer);
        }
      } catch {
        // Keep polling gently; the payment page can still confirm via webhook.
      }
    }, 5000);

    return () => window.clearInterval(timer);
  }, [payment?.orderCode, paymentState, onOpenChange, refreshSession]);

  async function handleCreatePayment() {
    if (!isAuthenticated) {
      setPaymentState("failed");
      setMessage("Ban can dang nhap truoc khi thanh toan.");
      return;
    }

    setPaymentState("creating");
    setMessage("");

    try {
      const order = await paymentsService.createProOrder(planCode);
      setPayment(order);
      paymentsService.rememberOrder(order.orderCode);
      setPaymentState("pending");
      setCountdown(
        Math.max(
          0,
          Math.floor((new Date(order.expiredAt).getTime() - Date.now()) / 1000),
        ),
      );
    } catch (error) {
      setPaymentState("failed");
      setMessage(
        error instanceof Error
          ? error.message
          : "Khong tao duoc ma thanh toan.",
      );
    }
  }

  async function handleCopy(text: string, field: string) {
    await navigator.clipboard.writeText(text);
    setCopied(field);
    window.setTimeout(() => setCopied(null), 2000);
  }

  function handleReset() {
    setPayment(null);
    setPaymentState("idle");
    setMessage("");
    setCountdown(0);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        onOpenChange(nextOpen);
        if (!nextOpen) {
          handleReset();
        }
      }}
    >
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Crown className="h-5 w-5 text-yellow-500" />
            Nang cap Pro
          </DialogTitle>
          <DialogDescription>
            Goi dang chon: <strong>{planName}</strong>
          </DialogDescription>
        </DialogHeader>

        {configStatus && (
          <div
            className={`rounded-xl border p-3 text-sm ${
              paymentReady
                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                : "border-orange-200 bg-orange-50 text-orange-700"
            }`}
          >
            {paymentReady
              ? "He thong thanh toan da san sang."
              : "Tam thoi chua the tao thanh toan. Vui long thu lai sau."}
          </div>
        )}

        {paymentState === "idle" && (
          <div className="space-y-6">
            <div className="rounded-xl border bg-primary/5 p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="font-medium">{planName}</span>
                <Badge className="bg-primary">{amountLabel}</Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                Don hang se duoc tao qua FastAPI va PayOS.
              </p>
            </div>

            <Button
              onClick={() => void handleCreatePayment()}
              className="w-full gap-2"
              disabled={!paymentReady}
            >
              <Crown className="h-4 w-4" />
              Tao thanh toan
            </Button>
          </div>
        )}

        {paymentState === "creating" && (
          <div className="space-y-4 py-8 text-center">
            <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Dang tao ma thanh toan...</p>
          </div>
        )}

        {paymentState === "pending" && payment && (
          <div className="space-y-6">
            <div className="flex flex-col items-center gap-4">
              <div className="grid h-52 w-52 place-items-center rounded-2xl border bg-white p-4">
                {qrIsImage ? (
                  <img
                    src={payment.qrCode}
                    alt="QR thanh toan"
                    className="h-full w-full object-contain"
                  />
                ) : (
                  <div className="text-center text-xs text-muted-foreground">
                    Quet QR tai PayOS hoac bam mo trang thanh toan.
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2 text-sm">
                <Clock className="h-4 w-4 text-orange-500" />
                <span>Het han trong:</span>
                <span className="font-mono font-bold text-orange-500">
                  {formatTime(countdown)}
                </span>
              </div>
            </div>

            <div className="space-y-3">
              {[
                ["Ma don", payment.orderCode, "orderCode"],
                ["So tien", amountLabel, "amount"],
                ["Ngan hang", payment.bankCode || "Dang cap nhat", "bankCode"],
                ["So tai khoan", payment.bankAccountNo || "Dang cap nhat", "accountNumber"],
                ["Ten tai khoan", payment.bankAccountName || "Dang cap nhat", "accountName"],
                ["Noi dung CK", payment.description || payment.orderCode, "description"],
              ].map(([label, value, key]) => (
                <div
                  key={String(key)}
                  className="flex items-center justify-between gap-3 rounded-lg bg-muted p-3"
                >
                  <div>
                    <p className="text-xs text-muted-foreground">{label}</p>
                    <p className="break-all font-medium">{value}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => void handleCopy(String(value), String(key))}
                  >
                    {copied === key ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              ))}
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <Button asChild variant="outline" className="gap-2">
                <a href={payment.checkoutUrl} target="_blank" rel="noreferrer">
                  <ExternalLink className="h-4 w-4" />
                  Mo PayOS
                </a>
              </Button>
              <Button variant="secondary" onClick={handleReset} className="gap-2">
                <RefreshCcw className="h-4 w-4" />
                Tao lai
              </Button>
            </div>
          </div>
        )}

        {paymentState === "paid" && (
          <div className="space-y-4 py-8 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">Thanh toan thanh cong!</h3>
              <p className="text-muted-foreground">
                {message || "He thong da ghi nhan thanh toan."}
              </p>
            </div>
            <Button onClick={() => onOpenChange(false)} className="w-full">
              Dong
            </Button>
          </div>
        )}

        {(paymentState === "expired" || paymentState === "failed") && (
          <div className="space-y-4 py-8 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
              <AlertCircle className="h-8 w-8 text-red-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">Khong hoan tat thanh toan</h3>
              <p className="text-muted-foreground">
                {message || "Vui long thu lai sau it phut."}
              </p>
            </div>
            <Button onClick={handleReset} variant="outline" className="w-full gap-2">
              <RefreshCcw className="h-4 w-4" />
              Thu lai
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
