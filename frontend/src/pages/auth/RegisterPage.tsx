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
import { CheckCircle2, Eye, EyeOff, Loader2, Target } from "lucide-react";

export function RegisterPage() {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    agreeTerms: false,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const passwordRequirements = [
    { label: "Ít nhất 8 ký tự", met: formData.password.length >= 8 },
    { label: "Chứa chữ hoa", met: /[A-Z]/.test(formData.password) },
    { label: "Chứa số", met: /[0-9]/.test(formData.password) },
  ];

  const validateForm = () => {
    const nextErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      nextErrors.name = "Vui lòng nhập họ tên";
    }

    if (!formData.email) {
      nextErrors.email = "Vui lòng nhập email";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      nextErrors.email = "Email không hợp lệ";
    }

    if (!formData.password) {
      nextErrors.password = "Vui lòng nhập mật khẩu";
    } else if (formData.password.length < 8) {
      nextErrors.password = "Mật khẩu phải có ít nhất 8 ký tự";
    }

    if (formData.password !== formData.confirmPassword) {
      nextErrors.confirmPassword = "Mật khẩu xác nhận không khớp";
    }

    if (!formData.agreeTerms) {
      nextErrors.agreeTerms = "Bạn cần đồng ý với điều khoản sử dụng";
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
      const result = await authService.register(formData);
      navigate(result.nextPath);
    } catch (error) {
      setAuthError(
        error instanceof Error
          ? error.message
          : "Không thể tạo tài khoản lúc này.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (field: string, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }));

    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: "" }));
    }

    if (authError) {
      setAuthError(null);
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
              Tạo tài khoản
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              Bắt đầu hành trình chinh phục TOEIC cùng GetGoals
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <GoogleSignInButton
              mode="signup"
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
                <Label htmlFor="name" className="text-foreground">
                  Họ và tên
                </Label>
                <Input
                  id="name"
                  type="text"
                  placeholder="Nguyễn Văn A"
                  value={formData.name}
                  onChange={(event) => handleChange("name", event.target.value)}
                  className={`h-11 ${
                    errors.name
                      ? "border-destructive focus-visible:ring-destructive"
                      : ""
                  }`}
                />
                {errors.name && (
                  <p className="text-sm text-destructive">{errors.name}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="email" className="text-foreground">
                  Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="name@example.com"
                  value={formData.email}
                  onChange={(event) => handleChange("email", event.target.value)}
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
                <Label htmlFor="password" className="text-foreground">
                  Mật khẩu
                </Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Tạo mật khẩu"
                    value={formData.password}
                    onChange={(event) =>
                      handleChange("password", event.target.value)
                    }
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

                {formData.password && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {passwordRequirements.map((requirement) => (
                      <span
                        key={requirement.label}
                        className={`flex items-center gap-1 rounded-full px-2 py-1 text-xs ${
                          requirement.met
                            ? "bg-primary/10 text-primary"
                            : "bg-muted text-muted-foreground"
                        }`}
                      >
                        {requirement.met && <CheckCircle2 className="h-3 w-3" />}
                        {requirement.label}
                      </span>
                    ))}
                  </div>
                )}

                {errors.password && (
                  <p className="text-sm text-destructive">{errors.password}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword" className="text-foreground">
                  Xác nhận mật khẩu
                </Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="Nhập lại mật khẩu"
                  value={formData.confirmPassword}
                  onChange={(event) =>
                    handleChange("confirmPassword", event.target.value)
                  }
                  className={`h-11 ${
                    errors.confirmPassword
                      ? "border-destructive focus-visible:ring-destructive"
                      : ""
                  }`}
                />
                {errors.confirmPassword && (
                  <p className="text-sm text-destructive">
                    {errors.confirmPassword}
                  </p>
                )}
              </div>

              <div className="flex items-start space-x-2">
                <Checkbox
                  id="terms"
                  checked={formData.agreeTerms}
                  onCheckedChange={(checked) =>
                    handleChange("agreeTerms", checked as boolean)
                  }
                  className="mt-0.5"
                />
                <Label
                  htmlFor="terms"
                  className="cursor-pointer text-sm font-normal leading-relaxed text-muted-foreground"
                >
                  Tôi đồng ý với{" "}
                  <a href="#" className="text-primary hover:underline">
                    Điều khoản sử dụng
                  </a>{" "}
                  và{" "}
                  <a href="#" className="text-primary hover:underline">
                    Chính sách bảo mật
                  </a>
                </Label>
              </div>

              {errors.agreeTerms && (
                <p className="text-sm text-destructive">{errors.agreeTerms}</p>
              )}

              <Button type="submit" className="h-11 w-full" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Đang tạo tài khoản...
                  </>
                ) : (
                  "Tạo tài khoản"
                )}
              </Button>

              {authError && (
                <p className="text-sm text-destructive">{authError}</p>
              )}
            </form>
          </CardContent>

          <CardFooter className="justify-center">
            <p className="text-sm text-muted-foreground">
              Đã có tài khoản?{" "}
              <Link
                to="/login"
                className="font-medium text-primary hover:underline"
              >
                Đăng nhập
              </Link>
            </p>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
