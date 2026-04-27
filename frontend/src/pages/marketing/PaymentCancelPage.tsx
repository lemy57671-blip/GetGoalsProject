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

export function PaymentCancelPage() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<PaymentStatusResponse | null>(null);
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
      try {
        const result = await paymentsService.getPaymentStatus(orderCode);
        if (!cancelled) {
          setStatus(result);
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Khong kiem tra duoc trang thai thanh toan.",
          );
        }
      }
    }

    void loadStatus();

    return () => {
      cancelled = true;
    };
  }, [orderCode]);

  return (
    <div className="grid min-h-screen place-items-center bg-background px-4">
      <Card className="max-w-lg rounded-3xl">
        <CardHeader>
          <CardTitle>Thanh toan da bi huy</CardTitle>
          <CardDescription>
            Ban da dung giao dich nay. Co the tao phien thanh toan moi bat cu
            luc nao.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {status && (
            <div className="rounded-2xl border bg-muted/40 p-4 text-sm">
              <div className="flex justify-between gap-4">
                <span className="text-muted-foreground">Ma don</span>
                <span className="font-medium">{status.orderCode}</span>
              </div>
              <div className="mt-2 flex justify-between gap-4">
                <span className="text-muted-foreground">Trang thai</span>
                <span className="font-medium">{status.status}</span>
              </div>
            </div>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <p className="text-sm text-muted-foreground">
            Neu ban da chuyen khoan nhung trang thai chua cap nhat, hay quay lai
            trang thanh cong sau vai phut hoac kiem tra lai trong tai khoan.
          </p>
          <Button asChild variant="outline" className="w-full">
            <Link to="/pricing">Quay lai bang gia</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
