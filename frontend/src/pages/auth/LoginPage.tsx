"use client";

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { GoogleSignInButton } from "@src/components/auth/GoogleSignInButton";
import { authService } from "@src/services/authService";
import { Eye, EyeOff, Loader2, Target } from "lucide-react";

export function LoginPage() {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [remember, setRemember] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>(
    {},
  );

  const validateForm = () => {
    const nextErrors: { email?: string; password?: string } = {};

    if (!email) {
      nextErrors.email = "Vui lòng nhập email";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      nextErrors.email = "Email không hợp lệ";
    }

    if (!password) {
      nextErrors.password = "Vui lòng nhập mật khẩu";
    } else if (password.length < 6) {
      nextErrors.password = "Mật khẩu phải có ít nhất 6 ký tự";
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!validateForm()) {
      return;
    }

    setAuthError(null);
    setIsLoading(true);

    try {
      const result = await authService.login({ email, password, remember });
      navigate(result.nextPath);
    } catch (error) {
      setAuthError(
        error instanceof Error
          ? error.message
          : "Không thể đăng nhập lúc này.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
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
            <CardTitle className="text-2xl text-foreground">
              Đăng nhập
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              Chào mừng trở lại! Tiếp tục hành trình chinh phục TOEIC.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <GoogleSignInButton
              mode="signin"
              disabled={isLoading}
              onSuccess={(nextPath) => navigate(nextPath)}
            />

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-border" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-card px-2 text-muted-foreground">Hoặc</span>
              </div>
            </div>

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
                    if (authError) {
                      setAuthError(null);
                    }
                  }}
                  className={`h-11 ${
                    errors.email
                      ? "border-destructive focus-visible:ring-destructive"
                      : ""
                  }`}
                />
                {errors.email && (
                  <p className="text-sm text-destructive">{errors.email}</p>
                )}
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-foreground">
                    Mật khẩu
                  </Label>
                  <Link
                    to="/forgot-password"
                    className="text-sm text-primary hover:underline"
                  >
                    Quên mật khẩu?
                  </Link>
                </div>

                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Nhập mật khẩu"
                    value={password}
                    onChange={(event) => {
                      setPassword(event.target.value);
                      if (authError) {
                        setAuthError(null);
                      }
                    }}
                    className={`h-11 pr-10 ${
                      errors.password
                        ? "border-destructive focus-visible:ring-destructive"
                        : ""
                    }`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>

                {errors.password && (
                  <p className="text-sm text-destructive">{errors.password}</p>
                )}
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="remember"
                  checked={remember}
                  onCheckedChange={(checked) => setRemember(Boolean(checked))}
                />
                <Label
                  htmlFor="remember"
                  className="cursor-pointer text-sm font-normal text-muted-foreground"
                >
                  Ghi nhớ đăng nhập
                </Label>
              </div>

              <Button type="submit" className="h-11 w-full" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Đang đăng nhập...
                  </>
                ) : (
                  "Đăng nhập"
                )}
              </Button>

              {authError && (
                <p className="text-sm text-destructive">{authError}</p>
              )}
            </form>
          </CardContent>

          <CardFooter className="justify-center">
            <p className="text-sm text-muted-foreground">
              Chưa có tài khoản?{" "}
              <Link
                to="/register"
                className="font-medium text-primary hover:underline"
              >
                Đăng ký miễn phí
              </Link>
            </p>
          </CardFooter>
        </Card>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          Bằng việc đăng nhập, bạn đồng ý với{" "}
          <a href="#" className="underline hover:text-foreground">
            Điều khoản sử dụng
          </a>{" "}
          và{" "}
          <a href="#" className="underline hover:text-foreground">
            Chính sách bảo mật
          </a>
        </p>
      </div>
    </div>
  );
}
