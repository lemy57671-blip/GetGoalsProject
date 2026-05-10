"use client";

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  onboardingDeadlines,
  onboardingSteps,
  onboardingStudyTimes,
  onboardingTargetScores,
  onboardingWeakSkills,
} from "@src/data/onboarding";
import { authService } from "@src/services/authService";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Brain,
  Calendar,
  CheckCircle2,
  Clock,
  Headphones,
  Sparkles,
  Target,
} from "lucide-react";

const deadlineWeeks: Record<string, number | null> = {
  "1month": 4,
  "2months": 8,
  "3months": 12,
  "6months": 24,
  flexible: null,
};

const studyMinutesByValue: Record<string, number> = {
  "30min": 30,
  "1hour": 60,
  "2hours": 120,
  "3hours": 180,
};

function examDateFromDeadline(deadline: string) {
  const weeks = deadlineWeeks[deadline];
  if (!weeks) return null;
  const date = new Date();
  date.setDate(date.getDate() + weeks * 7);
  return date.toISOString().slice(0, 10);
}

function parseOptionalToeicScore(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  if (!Number.isInteger(parsed) || parsed < 0 || parsed > 990) {
    return Number.NaN;
  }
  return parsed;
}

export function OnboardingPage() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({
    currentScore: "",
    hasNoCurrentScore: false,
    targetScore: "",
    deadline: "",
    studyTime: "",
    weakSkills: [] as string[],
  });

  const progress = (currentStep / onboardingSteps.length) * 100;

  const handleNext = () => {
    if (currentStep < onboardingSteps.length) {
      setCurrentStep((prev) => prev + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  const handleWeakSkillToggle = (skill: string) => {
    setFormData((prev) => ({
      ...prev,
      weakSkills: prev.weakSkills.includes(skill)
        ? prev.weakSkills.filter((item) => item !== skill)
        : [...prev.weakSkills, skill],
    }));
  };

  const canProceed = () => {
    switch (currentStep) {
      case 1:
        if (formData.hasNoCurrentScore || formData.currentScore.trim() === "") {
          return true;
        }
        return !Number.isNaN(parseOptionalToeicScore(formData.currentScore));
      case 2:
        return formData.targetScore !== "";
      case 3:
        return formData.deadline !== "";
      case 4:
        return formData.studyTime !== "";
      case 5:
        return formData.weakSkills.length > 0;
      default:
        return true;
    }
  };

  const handleSubmit = async () => {
    const currentScore = formData.hasNoCurrentScore
      ? null
      : parseOptionalToeicScore(formData.currentScore);
    const studyMinutesPerDay = formData.studyTime
      ? studyMinutesByValue[formData.studyTime] ?? null
      : null;

    const result = await authService.completeOnboarding({
      currentScore: currentScore === null || Number.isNaN(currentScore) ? null : currentScore,
      targetScore: formData.targetScore
        ? Number.parseInt(formData.targetScore, 10)
        : null,
      examDate: examDateFromDeadline(formData.deadline),
      studyMinutesPerDay: studyMinutesPerDay === null || Number.isNaN(studyMinutesPerDay)
        ? null
        : studyMinutesPerDay,
      weakSkills: formData.weakSkills,
    });

    navigate(result.nextPath);
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Target className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-semibold text-foreground">GetGoals</span>
          </Link>
          <Button variant="ghost" size="sm" asChild>
            <Link to="/dashboard">Bỏ qua</Link>
          </Button>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 lg:py-12">
        <div className="mx-auto max-w-5xl">
          <div className="mb-8">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                Bước {currentStep} / {onboardingSteps.length}
              </span>
              <span className="text-sm text-muted-foreground">
                {Math.round(progress)}% hoàn thành
              </span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>

          <div className="grid gap-8 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <Card className="rounded-2xl border-border">
                <CardHeader>
                  <CardTitle className="text-2xl text-foreground">
                    {onboardingSteps[currentStep - 1].title}
                  </CardTitle>
                  <CardDescription className="text-muted-foreground">
                    {currentStep === 1 &&
                      "Nhập điểm TOEIC hiện tại nếu bạn đã từng thi hoặc có điểm ước lượng"}
                    {currentStep === 2 && "Bạn muốn đạt bao nhiêu điểm TOEIC?"}
                    {currentStep === 3 && "Khi nào bạn cần đạt mục tiêu?"}
                    {currentStep === 4 &&
                      "Bạn có thể dành bao nhiêu thời gian học mỗi ngày?"}
                    {currentStep === 5 &&
                      "Chọn những kỹ năng bạn muốn cải thiện (có thể chọn nhiều)"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {currentStep === 1 && (
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">
                          Điểm TOEIC hiện tại (nếu có)
                        </label>
                        <Input
                          type="number"
                          min={0}
                          max={990}
                          step={5}
                          inputMode="numeric"
                          placeholder="Ví dụ: 350"
                          value={formData.currentScore}
                          disabled={formData.hasNoCurrentScore}
                          onChange={(event) =>
                            setFormData((prev) => ({
                              ...prev,
                              currentScore: event.target.value,
                            }))
                          }
                        />
                        {!canProceed() ? (
                          <p className="text-xs text-destructive">
                            Điểm TOEIC hiện tại phải là số từ 0 đến 990.
                          </p>
                        ) : (
                          <p className="text-xs text-muted-foreground">
                            Bạn có thể bỏ trống nếu chưa từng thi TOEIC.
                          </p>
                        )}
                      </div>

                      <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-border p-4 transition hover:bg-accent/50">
                        <Checkbox
                          checked={formData.hasNoCurrentScore}
                          onCheckedChange={(checked) =>
                            setFormData((prev) => ({
                              ...prev,
                              hasNoCurrentScore: Boolean(checked),
                              currentScore: checked ? "" : prev.currentScore,
                            }))
                          }
                        />
                        <div>
                          <div className="font-medium text-foreground">
                            Chưa có điểm TOEIC
                          </div>
                          <div className="text-sm text-muted-foreground">
                            GetGoals sẽ dùng placement test để ước lượng trình độ ban đầu.
                          </div>
                        </div>
                      </label>
                    </div>
                  )}

                  {currentStep === 2 && (
                    <RadioGroup
                      value={formData.targetScore}
                      onValueChange={(value) =>
                        setFormData((prev) => ({ ...prev, targetScore: value }))
                      }
                      className="space-y-3"
                    >
                      {onboardingTargetScores.map((score) => (
                        <label
                          key={score.value}
                          className={`flex cursor-pointer items-center justify-between rounded-xl border p-4 transition-all ${
                            formData.targetScore === score.value
                              ? "border-primary bg-accent"
                              : "border-border hover:border-primary/50 hover:bg-accent/50"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <RadioGroupItem value={score.value} />
                            <div>
                              <div className="font-medium text-foreground">
                                {score.label}
                              </div>
                              <div className="text-sm text-muted-foreground">
                                {score.desc}
                              </div>
                            </div>
                          </div>
                          <Target className="h-5 w-5 text-primary" />
                        </label>
                      ))}
                    </RadioGroup>
                  )}

                  {currentStep === 3 && (
                    <RadioGroup
                      value={formData.deadline}
                      onValueChange={(value) =>
                        setFormData((prev) => ({ ...prev, deadline: value }))
                      }
                      className="grid grid-cols-2 gap-3 md:grid-cols-3"
                    >
                      {onboardingDeadlines.map((deadline) => (
                        <label
                          key={deadline.value}
                          className={`flex cursor-pointer flex-col items-center rounded-xl border p-4 text-center transition-all ${
                            formData.deadline === deadline.value
                              ? "border-primary bg-accent"
                              : "border-border hover:border-primary/50 hover:bg-accent/50"
                          }`}
                        >
                          <RadioGroupItem value={deadline.value} className="sr-only" />
                          <Calendar
                            className={`mb-2 h-6 w-6 ${
                              formData.deadline === deadline.value
                                ? "text-primary"
                                : "text-muted-foreground"
                            }`}
                          />
                          <div className="font-medium text-foreground">
                            {deadline.label}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            Cường độ: {deadline.intensity}
                          </div>
                        </label>
                      ))}
                    </RadioGroup>
                  )}

                  {currentStep === 4 && (
                    <RadioGroup
                      value={formData.studyTime}
                      onValueChange={(value) =>
                        setFormData((prev) => ({ ...prev, studyTime: value }))
                      }
                      className="grid grid-cols-2 gap-3"
                    >
                      {onboardingStudyTimes.map((time) => (
                        <label
                          key={time.value}
                          className={`flex cursor-pointer flex-col items-center rounded-xl border p-6 text-center transition-all ${
                            formData.studyTime === time.value
                              ? "border-primary bg-accent"
                              : "border-border hover:border-primary/50 hover:bg-accent/50"
                          }`}
                        >
                          <RadioGroupItem value={time.value} className="sr-only" />
                          <Clock
                            className={`mb-2 h-8 w-8 ${
                              formData.studyTime === time.value
                                ? "text-primary"
                                : "text-muted-foreground"
                            }`}
                          />
                          <div className="font-medium text-foreground">
                            {time.label}
                          </div>
                        </label>
                      ))}
                    </RadioGroup>
                  )}

                  {currentStep === 5 && (
                    <div className="space-y-3">
                      {onboardingWeakSkills.map((skill) => (
                        <label
                          key={skill.value}
                          className={`flex cursor-pointer items-center gap-3 rounded-xl border p-4 transition-all ${
                            formData.weakSkills.includes(skill.value)
                              ? "border-primary bg-accent"
                              : "border-border hover:border-primary/50 hover:bg-accent/50"
                          }`}
                        >
                          <Checkbox
                            checked={formData.weakSkills.includes(skill.value)}
                            onCheckedChange={() => handleWeakSkillToggle(skill.value)}
                          />
                          <div className="flex-1">
                            <div className="font-medium text-foreground">
                              {skill.label}
                            </div>
                            <div className="text-sm text-muted-foreground">
                              {skill.desc}
                            </div>
                          </div>
                          {skill.value.startsWith("listening") ? (
                            <Headphones className="h-5 w-5 text-muted-foreground" />
                          ) : (
                            <BookOpen className="h-5 w-5 text-muted-foreground" />
                          )}
                        </label>
                      ))}
                    </div>
                  )}

                  <div className="mt-8 flex items-center justify-between">
                    <Button
                      variant="ghost"
                      onClick={handleBack}
                      disabled={currentStep === 1}
                    >
                      <ArrowLeft className="mr-2 h-4 w-4" />
                      Quay lại
                    </Button>

                    {currentStep < onboardingSteps.length ? (
                      <Button onClick={handleNext} disabled={!canProceed()}>
                        Tiếp tục
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </Button>
                    ) : (
                      <Button onClick={handleSubmit} disabled={!canProceed()}>
                        <Sparkles className="mr-2 h-4 w-4" />
                        Tạo lộ trình cho tôi
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="lg:col-span-1">
              <Card className="sticky top-8 rounded-2xl border-border">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg text-foreground">
                    <Brain className="h-5 w-5 text-primary" />
                    Lộ trình của bạn
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        Trình độ hiện tại
                      </span>
                      <span className="text-sm font-medium text-foreground">
                        {formData.hasNoCurrentScore
                          ? "Chưa có điểm"
                          : formData.currentScore
                            ? `${formData.currentScore} điểm`
                            : "—"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Mục tiêu</span>
                      <span className="text-sm font-medium text-foreground">
                        {formData.targetScore
                          ? `${formData.targetScore} điểm`
                          : "—"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Deadline</span>
                      <span className="text-sm font-medium text-foreground">
                        {formData.deadline
                          ? onboardingDeadlines.find((item) => item.value === formData.deadline)?.label
                          : "—"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        Thời gian học
                      </span>
                      <span className="text-sm font-medium text-foreground">
                        {formData.studyTime
                          ? onboardingStudyTimes.find((item) => item.value === formData.studyTime)?.label
                          : "—"}
                      </span>
                    </div>
                  </div>

                  {formData.weakSkills.length > 0 && (
                    <div className="border-t border-border pt-4">
                      <span className="text-sm text-muted-foreground">
                        Kỹ năng cần cải thiện:
                      </span>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {formData.weakSkills.map((skill) => (
                          <Badge key={skill} variant="secondary" className="text-xs">
                            {
                              onboardingWeakSkills.find((item) => item.value === skill)
                                ?.label
                            }
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {formData.targetScore && formData.deadline && (
                    <div className="border-t border-border pt-4">
                      <div className="rounded-xl bg-accent p-4">
                        <div className="mb-2 flex items-center gap-2 font-medium text-primary">
                          <CheckCircle2 className="h-4 w-4" />
                          <span className="text-sm">Dự kiến</span>
                        </div>
                        <p className="text-sm text-foreground">
                          Với{" "}
                          {onboardingStudyTimes.find(
                            (item) => item.value === formData.studyTime,
                          )?.label || "thời gian học hợp lý"}
                          , bạn có thể đạt {formData.targetScore} điểm trong{" "}
                          {
                            onboardingDeadlines.find(
                              (item) => item.value === formData.deadline,
                            )?.label
                          }
                          .
                        </p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
