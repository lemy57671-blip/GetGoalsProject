import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  paymentsService,
  type PaymentStatusResponse,
} from "@src/services/paymentsService";

function formatCurrency(value?: number) {
  if (!value) return "";
  return `${value.toLocaleString("vi-VN")} VND`;
}

export function PaymentSuccessPage() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<PaymentStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const orderCode = useMemo(
    () =>
      searchParams.get("orderCode") ||
      searchParams.get("order_code") ||
      searchParams.get("id") ||
      paymentsService.getRememberedOrder() ||
      "",
    [searchParams],
  );

  useEffect(() => {
    if (!orderCode) return;

    let cancelled = false;

    async function loadStatus() {
      setIsLoading(true);
      setError(null);

      try {
        const result = await paymentsService.getPaymentStatus(orderCode);
        if (cancelled) return;

        setStatus(result);

        if (result.status === "paid") {
          paymentsService.clearRememberedOrder();
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Khong kiem tra duoc trang thai thanh toan.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadStatus();

    return () => {
      cancelled = true;
    };
  }, [orderCode]);

  const statusText = status
    ? status.status === "paid"
      ? "Thanh toan da duoc xac nhan va goi Pro da duoc kich hoat."
      : status.status === "pending"
        ? "Giao dich dang cho xac nhan. Vui long quay lai sau it phut."
        : `Trang thai hien tai: ${status.status}.`
    : "Giao dich cua ban da duoc ghi nhan.";

  return (
    <div className="grid min-h-screen place-items-center bg-background px-4">
      <Card className="max-w-lg rounded-3xl">
        <CardHeader>
          <CardTitle>Thanh toan thanh cong</CardTitle>
          <CardDescription>{statusText}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading && (
            <p className="text-sm text-muted-foreground">
              Dang kiem tra trang thai don thanh toan...
            </p>
          )}
          {status && (
            <div className="rounded-2xl border bg-muted/40 p-4 text-sm">
              <div className="flex justify-between gap-4">
                <span className="text-muted-foreground">Ma don</span>
                <span className="font-medium">{status.orderCode}</span>
              </div>
              <div className="mt-2 flex justify-between gap-4">
                <span className="text-muted-foreground">So tien</span>
                <span className="font-medium">{formatCurrency(status.amount)}</span>
              </div>
            </div>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <p className="text-sm text-muted-foreground">
            Neu tai khoan chua cap nhat ngay, vui long dang nhap lai sau it
            phut de dong bo trang thai goi.
          </p>
          <Button asChild className="w-full">
            <Link to="/dashboard">Di den dashboard</Link>
          </Button>
          <Button asChild variant="outline" className="w-full">
            <Link to="/pricing">Quay lai bang gia</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
