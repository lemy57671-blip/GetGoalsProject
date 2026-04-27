"use client";

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Menu,
  MessageSquare,
  Sparkles,
  Target,
  Users,
  X,
} from "lucide-react";
import {
  marketingFaqs,
  marketingFeatures,
  marketingStats,
  marketingSteps,
  marketingTestimonials,
} from "@src/data/marketing";

export function LandingPage() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [currentTestimonial, setCurrentTestimonial] = useState(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const nextTestimonial = () => {
    setCurrentTestimonial(
      (prev) => (prev + 1) % marketingTestimonials.length,
    );
  };

  const prevTestimonial = () => {
    setCurrentTestimonial(
      (prev) =>
        (prev - 1 + marketingTestimonials.length) %
        marketingTestimonials.length,
    );
  };

  return (
    <div className="min-h-screen bg-background">
      <header
        className={`fixed left-0 right-0 top-0 z-50 transition-all duration-300 ${
          isScrolled
            ? "border-b border-border bg-background/95 shadow-sm backdrop-blur-md"
            : "bg-transparent"
        }`}
      >
        <div className="container mx-auto px-4">
          <div className="flex h-16 items-center justify-between lg:h-20">
            <Link to="/" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
                <Target className="h-5 w-5 text-primary-foreground" />
              </div>
              <span className="text-xl font-semibold text-foreground">
                GetGoals
              </span>
            </Link>

            <nav className="hidden items-center gap-8 lg:flex">
              <a
                href="#features"
                className="text-muted-foreground transition-colors hover:text-foreground"
              >
                Tính năng
              </a>
              <a
                href="#testimonials"
                className="text-muted-foreground transition-colors hover:text-foreground"
              >
                Đánh giá
              </a>
              <Link
                to="/pricing"
                className="text-muted-foreground transition-colors hover:text-foreground"
              >
                Bảng giá
              </Link>
              <a
                href="#faq"
                className="text-muted-foreground transition-colors hover:text-foreground"
              >
                FAQ
              </a>
            </nav>

            <div className="hidden items-center gap-3 lg:flex">
              <Button variant="ghost" asChild>
                <Link to="/login">Đăng nhập</Link>
              </Button>
              <Button asChild>
                <Link to="/register">Bắt đầu miễn phí</Link>
              </Button>
            </div>

            <button
              type="button"
              className="p-2 lg:hidden"
              onClick={() => setMobileMenuOpen((prev) => !prev)}
            >
              {mobileMenuOpen ? (
                <X className="h-6 w-6" />
              ) : (
                <Menu className="h-6 w-6" />
              )}
            </button>
          </div>
        </div>

        {mobileMenuOpen && (
          <div className="border-t border-border bg-background lg:hidden">
            <nav className="container mx-auto flex flex-col gap-4 px-4 py-4">
              <a
                href="#features"
                className="py-2 text-muted-foreground hover:text-foreground"
              >
                Tính năng
              </a>
              <a
                href="#testimonials"
                className="py-2 text-muted-foreground hover:text-foreground"
              >
                Đánh giá
              </a>
              <Link
                to="/pricing"
                className="py-2 text-muted-foreground hover:text-foreground"
              >
                Bảng giá
              </Link>
              <a
                href="#faq"
                className="py-2 text-muted-foreground hover:text-foreground"
              >
                FAQ
              </a>

              <div className="flex flex-col gap-2 border-t border-border pt-4">
                <Button variant="outline" asChild className="w-full">
                  <Link to="/login">Đăng nhập</Link>
                </Button>
                <Button asChild className="w-full">
                  <Link to="/register">Bắt đầu miễn phí</Link>
                </Button>
              </div>
            </nav>
          </div>
        )}
      </header>

      <section className="relative overflow-hidden pb-20 pt-32 lg:pb-32 lg:pt-40">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-accent via-background to-background" />
        <div className="container relative mx-auto px-4">
          <div className="mx-auto max-w-4xl text-center">
            <Badge variant="secondary" className="mb-6 px-4 py-1.5">
              <Sparkles className="mr-1.5 h-3.5 w-3.5" />
              Nền tảng luyện thi TOEIC #1 Việt Nam
            </Badge>

            <h1 className="mb-6 text-4xl font-bold leading-tight text-foreground text-balance lg:text-6xl">
              Chinh phục TOEIC với{" "}
              <span className="text-primary">lộ trình thông minh</span>
            </h1>

            <p className="mx-auto mb-8 max-w-2xl text-lg leading-relaxed text-muted-foreground text-pretty lg:text-xl">
              Bài kiểm tra chẩn đoán, lộ trình cá nhân hóa, AI Coach hỗ trợ
              24/7 và hàng nghìn bài luyện tập giúp bạn đạt mục tiêu điểm số
              nhanh nhất.
            </p>

            <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Button size="lg" className="w-full px-8 sm:w-auto" asChild>
                <Link to="/register">
                  Bắt đầu miễn phí
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>

              <Button
                size="lg"
                variant="outline"
                className="w-full border-border bg-white px-8 text-foreground transition-colors duration-200 hover:border-[#A6C8FF] hover:bg-[#A6C8FF] hover:text-foreground sm:w-auto"
                asChild
              >
                <Link to="/dashboard">Làm bài chẩn đoán</Link>
              </Button>
            </div>

            <p className="mt-4 text-sm text-muted-foreground">
              Không cần thẻ tín dụng • Dùng thử miễn phí 7 ngày
            </p>
          </div>

          <div className="mt-16 grid grid-cols-2 gap-6 lg:mt-24 lg:grid-cols-4 lg:gap-8">
            {marketingStats.map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="mb-1 text-3xl font-bold text-primary lg:text-4xl">
                  {stat.value}
                </div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="features" className="bg-card py-20 lg:py-32">
        <div className="container mx-auto px-4">
          <div className="mx-auto mb-16 max-w-2xl text-center">
            <Badge variant="secondary" className="mb-4">
              Tính năng nổi bật
            </Badge>
            <h2 className="mb-4 text-3xl font-bold text-foreground text-balance lg:text-4xl">
              Mọi thứ bạn cần để đạt điểm TOEIC mục tiêu
            </h2>
            <p className="text-lg text-muted-foreground">
              Hệ thống học tập toàn diện được thiết kế bởi chuyên gia TOEIC và
              công nghệ AI tiên tiến.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 lg:gap-8">
            {marketingFeatures.map((feature) => (
              <Card
                key={feature.title}
                className="rounded-2xl border-border bg-background transition-shadow hover:shadow-lg"
              >
                <CardContent className="p-6 lg:p-8">
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary shadow-sm">
                    <feature.icon
                      className="h-6 w-6 text-white"
                      strokeWidth={2.6}
                      absoluteStrokeWidth
                    />
                  </div>
                  <h3 className="mb-2 text-lg font-semibold text-foreground">
                    {feature.title}
                  </h3>
                  <p className="leading-relaxed text-muted-foreground">
                    {feature.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20 lg:py-32">
        <div className="container mx-auto px-4">
          <div className="mx-auto mb-16 max-w-2xl text-center">
            <Badge variant="secondary" className="mb-4">
              Quy trình học
            </Badge>
            <h2 className="text-3xl font-bold text-foreground text-balance lg:text-4xl">
              4 bước đơn giản để đạt mục tiêu
            </h2>
          </div>

          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-4">
            {marketingSteps.map((item) => (
              <div key={item.step} className="text-center">
                <div className="relative mb-4 inline-flex">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary shadow-md">
                    <item.icon
                      className="h-8 w-8 text-white"
                      strokeWidth={2.75}
                      absoluteStrokeWidth
                    />
                  </div>

                  <div className="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                    {item.step}
                  </div>
                </div>

                <h3 className="mb-1 font-semibold text-foreground">
                  {item.title}
                </h3>
                <p className="text-sm text-muted-foreground">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="testimonials" className="bg-card py-20 lg:py-32">
        <div className="container mx-auto px-4">
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <Badge variant="secondary" className="mb-4">
              Đánh giá từ học viên
            </Badge>
            <h2 className="text-3xl font-bold text-foreground text-balance lg:text-4xl">
              Hàng nghìn học viên đã thành công
            </h2>
          </div>

          <div className="mx-auto max-w-3xl">
            <Card className="overflow-hidden rounded-2xl border-border bg-background">
              <CardContent className="p-8 lg:p-12">
                <div className="mb-6 flex items-center gap-4">
                  <div className="flex h-14 w-14 items-center justify-center rounded-full bg-accent text-lg font-semibold text-primary">
                    {marketingTestimonials[currentTestimonial].avatar}
                  </div>

                  <div>
                    <div className="font-semibold text-foreground">
                      {marketingTestimonials[currentTestimonial].name}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {marketingTestimonials[currentTestimonial].role}
                    </div>
                  </div>

                  <Badge className="ml-auto bg-primary/10 text-primary hover:bg-primary/20">
                    {marketingTestimonials[currentTestimonial].score} điểm
                  </Badge>
                </div>

                <p className="mb-8 text-lg leading-relaxed text-foreground">
                  &ldquo;{marketingTestimonials[currentTestimonial].content}
                  &rdquo;
                </p>

                <div className="flex items-center justify-between">
                  <div className="flex gap-2">
                    {marketingTestimonials.map((testimonial, index) => (
                      <button
                        key={testimonial.name}
                        type="button"
                        onClick={() => setCurrentTestimonial(index)}
                        className={`h-2 w-2 rounded-full transition-colors ${
                          index === currentTestimonial
                            ? "bg-primary"
                            : "bg-border"
                        }`}
                      />
                    ))}
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={prevTestimonial}
                      className="rounded-full"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={nextTestimonial}
                      className="rounded-full"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      <section className="py-20 lg:py-32">
        <div className="container mx-auto px-4">
          <div className="mx-auto max-w-4xl">
            <Card className="overflow-hidden rounded-2xl bg-primary text-primary-foreground">
              <CardContent className="p-8 lg:p-12">
                <div className="flex flex-col items-center gap-8 lg:flex-row">
                  <div className="flex-1 text-center lg:text-left">
                    <h2 className="mb-4 text-2xl font-bold text-balance lg:text-3xl">
                      Sẵn sàng chinh phục TOEIC?
                    </h2>
                    <p className="mb-6 text-primary-foreground/80">
                      Bắt đầu với gói Free hoặc nâng cấp Pro để mở khóa toàn bộ
                      tính năng AI Coach và lộ trình cá nhân hóa.
                    </p>

                    <div className="flex flex-col justify-center gap-3 sm:flex-row lg:justify-start">
                      <Button variant="secondary" size="lg" asChild>
                        <Link to="/pricing">
                          Xem bảng giá
                          <ArrowRight className="ml-2 h-4 w-4" />
                        </Link>
                      </Button>

                      <Button
                        variant="outline"
                        size="lg"
                        className="border-primary-foreground/30 bg-transparent text-primary-foreground hover:bg-primary-foreground/10"
                        asChild
                      >
                        <Link to="/register">Dùng thử miễn phí</Link>
                      </Button>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="text-center">
                      <div className="text-4xl font-bold lg:text-5xl">Free</div>
                      <div className="text-sm text-primary-foreground/70">
                        Mãi mãi
                      </div>
                    </div>

                    <div className="text-2xl text-primary-foreground/30">/</div>

                    <div className="text-center">
                      <div className="text-4xl font-bold lg:text-5xl">199K</div>
                      <div className="text-sm text-primary-foreground/70">
                        VNĐ/tháng
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      <section id="faq" className="bg-card py-20 lg:py-32">
        <div className="container mx-auto px-4">
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <Badge variant="secondary" className="mb-4">
              FAQ
            </Badge>
            <h2 className="text-3xl font-bold text-foreground text-balance lg:text-4xl">
              Câu hỏi thường gặp
            </h2>
          </div>

          <div className="mx-auto max-w-2xl">
            <Accordion type="single" collapsible className="space-y-4">
              {marketingFaqs.map((faq, index) => (
                <AccordionItem
                  key={faq.question}
                  value={`item-${index}`}
                  className="rounded-xl border border-border bg-background px-6"
                >
                  <AccordionTrigger className="py-4 text-left text-foreground hover:no-underline">
                    {faq.question}
                  </AccordionTrigger>
                  <AccordionContent className="pb-4 text-muted-foreground">
                    {faq.answer}
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        </div>
      </section>

      <section className="py-20 lg:py-32">
        <div className="container mx-auto px-4 text-center">
          <h2 className="mb-4 text-3xl font-bold text-foreground text-balance lg:text-4xl">
            Bắt đầu hành trình chinh phục TOEIC ngay hôm nay
          </h2>
          <p className="mx-auto mb-8 max-w-xl text-lg text-muted-foreground">
            Hàng nghìn học viên đã đạt mục tiêu. Bạn sẽ là người tiếp theo?
          </p>
          <Button size="lg" className="px-8" asChild>
            <Link to="/register">
              Bắt đầu miễn phí
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </section>

      <footer className="border-t border-border bg-card py-12 lg:py-16">
        <div className="container mx-auto px-4">
          <div className="mb-12 grid grid-cols-2 gap-8 lg:grid-cols-4">
            <div className="col-span-2 lg:col-span-1">
              <Link to="/" className="mb-4 flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
                  <Target className="h-5 w-5 text-primary-foreground" />
                </div>
                <span className="text-xl font-semibold text-foreground">
                  GetGoals
                </span>
              </Link>
              <p className="text-sm leading-relaxed text-muted-foreground">
                Nền tảng luyện thi TOEIC thông minh với AI Coach và lộ trình cá
                nhân hóa.
              </p>
            </div>

            <div>
              <h4 className="mb-4 font-semibold text-foreground">Sản phẩm</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <a
                    href="#"
                    className="transition-colors hover:text-foreground"
                  >
                    Bài chẩn đoán
                  </a>
                </li>
                <li>
                  <Link
                    to="/practice"
                    className="transition-colors hover:text-foreground"
                  >
                    Luyện tập
                  </Link>
                </li>
                <li>
                  <Link
                    to="/mock-test"
                    className="transition-colors hover:text-foreground"
                  >
                    Mock Test
                  </Link>
                </li>
                <li>
                  <Link
                    to="/pricing"
                    className="transition-colors hover:text-foreground"
                  >
                    Bảng giá
                  </Link>
                </li>
              </ul>
            </div>

            <div>
              <h4 className="mb-4 font-semibold text-foreground">Hỗ trợ</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <a
                    href="#"
                    className="transition-colors hover:text-foreground"
                  >
                    Trung tâm trợ giúp
                  </a>
                </li>
                <li>
                  <a
                    href="#"
                    className="transition-colors hover:text-foreground"
                  >
                    Liên hệ
                  </a>
                </li>
                <li>
                  <a
                    href="#faq"
                    className="transition-colors hover:text-foreground"
                  >
                    FAQ
                  </a>
                </li>
              </ul>
            </div>

            <div>
              <h4 className="mb-4 font-semibold text-foreground">Pháp lý</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <a
                    href="#"
                    className="transition-colors hover:text-foreground"
                  >
                    Điều khoản sử dụng
                  </a>
                </li>
                <li>
                  <a
                    href="#"
                    className="transition-colors hover:text-foreground"
                  >
                    Chính sách bảo mật
                  </a>
                </li>
              </ul>
            </div>
          </div>

          <div className="flex flex-col items-center justify-between gap-4 border-t border-border pt-8 md:flex-row">
            <p className="text-sm text-muted-foreground">
              © 2024 GetGoals. Mọi quyền được bảo lưu.
            </p>

            <div className="flex items-center gap-4">
              <a
                href="#"
                className="text-muted-foreground hover:text-foreground"
              >
                <MessageSquare className="h-5 w-5" />
              </a>
              <a
                href="#"
                className="text-muted-foreground hover:text-foreground"
              >
                <Users className="h-5 w-5" />
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
