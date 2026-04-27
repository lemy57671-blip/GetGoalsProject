"use client";

import { useState } from "react";
import { Link } from "react-router-dom";
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
import {
  ArrowLeft,
  CheckCircle,
  Loader2,
  Mail,
  Target,
} from "lucide-react";

export function ForgotPasswordPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);

  const validateEmail = () => {
    if (!email) {
      setError("Vui lòng nhập email");
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError("Email không hợp lệ");
      return false;
    }
    setError("");
    return true;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!validateEmail()) return;

    setIsLoading(true);

    try {
      await authService.forgotPassword({ email });
      setIsSuccess(true);
    } finally {
      setIsLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-accent via-background to-background p-4">
        <div className="w-full max-w-md">
          <Link to="/" className="mb-8 flex items-center justify-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary">
              <Target className="h-6 w-6 text-primary-foreground" />
            </div>
            <span className="text-2xl font-semibold text-foreground">
              GetGoals
            </span>
          </Link>

          <Card className="rounded-2xl border-border shadow-lg">
            <CardContent className="pb-8 pt-8 text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                <CheckCircle className="h-8 w-8 text-primary" />
              </div>
              <h2 className="mb-2 text-xl font-semibold text-foreground">
                Kiểm tra email của bạn
              </h2>
              <p className="mb-6 text-muted-foreground">
                Chúng tôi đã gửi hướng dẫn đặt lại mật khẩu đến{" "}
                <span className="font-medium text-foreground">{email}</span>
              </p>
              <div className="space-y-3">
                <Button className="w-full" asChild>
                  <Link to="/login">Quay lại đăng nhập</Link>
                </Button>
                <Button
                  variant="ghost"
                  className="w-full text-muted-foreground"
                  onClick={() => setIsSuccess(false)}
                >
                  Không nhận được email? Gửi lại
                </Button>
              </div>
            </CardContent>
          </Card>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            Vui lòng kiểm tra cả thư mục spam nếu bạn không thấy email trong hộp
            thư đến.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-accent via-background to-background p-4">
      <div className="w-full max-w-md">
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
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-accent">
              <Mail className="h-7 w-7 text-primary" />
            </div>
            <CardTitle className="text-2xl text-foreground">
              Quên mật khẩu?
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              Nhập email đăng ký, chúng tôi sẽ gửi link đặt lại mật khẩu.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-foreground">
                  Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(event) => {
                    setEmail(event.target.value);
                    if (error) setError("");
                  }}
                  className={`h-11 ${
                    error
                      ? "border-destructive focus-visible:ring-destructive"
                      : ""
                  }`}
                />
                {error && <p className="text-sm text-destructive">{error}</p>}
              </div>

              <Button type="submit" className="h-11 w-full" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Đang gửi...
                  </>
                ) : (
                  "Gửi hướng dẫn đặt lại"
                )}
              </Button>
            </form>
          </CardContent>
          <CardFooter className="justify-center">
            <Link
              to="/login"
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4" />
              Quay lại đăng nhập
            </Link>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
