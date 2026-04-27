"use client";

import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authService } from "@src/services/authService";
import { ArrowLeft, CheckCircle, Loader2, Lock, Target } from "lucide-react";

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const account = useMemo(
    () => searchParams.get("account")?.trim() || "",
    [searchParams],
  );

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setSuccessMessage("");

    if (!account) {
      setError("Thiếu thông tin tài khoản cần đặt lại mật khẩu.");
      return;
    }

    if (!newPassword || !confirmPassword) {
      setError("Vui lòng nhập đầy đủ mật khẩu mới.");
      return;
    }

    if (newPassword.length < 8) {
      setError("Mật khẩu mới phải có ít nhất 8 ký tự.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Mật khẩu xác nhận không khớp.");
      return;
    }

    try {
      setIsSubmitting(true);
      const response = await authService.resetPasswordDirect({
        emailOrUsername: account,
        newPassword,
        confirmPassword,
      });

      setSuccessMessage(response.message);
      setNewPassword("");
      setConfirmPassword("");

      window.setTimeout(() => {
        navigate("/login");
      }, 1500);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Không đặt lại được mật khẩu.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-accent via-background to-background p-4">
      <div className="w-full max-w-md">
        <Link
          to="/forgot-password"
          className="mb-6 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Quay lại quên mật khẩu
        </Link>

        <Link to="/" className="mb-8 flex items-center justify-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary">
            <Target className="h-6 w-6 text-primary-foreground" />
          </div>
          <span className="text-2xl font-semibold text-foreground">
            GetGoals
          </span>
        </Link>

        <Card className="rounded-2xl border-border shadow-lg">
          <CardHeader className="pb-4 text-center">
            <CardTitle className="text-2xl text-foreground">
              Đặt lại mật khẩu
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              Tài khoản:{" "}
              <span className="font-medium text-foreground">
                {account || "Không xác định"}
              </span>
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            {successMessage ? (
              <div className="flex gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
                <CheckCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{successMessage} Đang chuyển về trang đăng nhập...</span>
              </div>
            ) : null}

            {error ? (
              <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                {error}
              </div>
            ) : null}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="newPassword">Mật khẩu mới</Label>
                <Input
                  id="newPassword"
                  type="password"
                  placeholder="Nhập mật khẩu mới"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  className="h-11"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Xác nhận mật khẩu</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="Nhập lại mật khẩu mới"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  className="h-11"
                />
              </div>

              <Button type="submit" className="h-11 w-full" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Đang cập nhật...
                  </>
                ) : (
                  <>
                    <Lock className="mr-2 h-4 w-4" />
                    Cập nhật mật khẩu mới
                  </>
                )}
              </Button>
            </form>
          </CardContent>

          <CardFooter className="justify-center">
            <p className="text-sm text-muted-foreground">
              Muốn quay lại?{" "}
              <Link to="/login" className="font-medium text-primary hover:underline">
                Đăng nhập
              </Link>
            </p>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
