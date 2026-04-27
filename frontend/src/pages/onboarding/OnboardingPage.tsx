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
import { Progress } from "@/components/ui/progress";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  onboardingDeadlines,
  onboardingLevels,
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

export function OnboardingPage() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({
    level: "",
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
        return formData.level !== "";
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
    const selectedLevel = onboardingLevels.find(
      (level) => level.value === formData.level,
    );
    const currentScore = selectedLevel?.score
      ? Number.parseInt(selectedLevel.score.split("-")[0], 10)
      : null;
    const studyMinutesPerDay = formData.studyTime
      ? Number.parseInt(formData.studyTime, 10)
      : null;

    const result = await authService.completeOnboarding({
      currentScore: Number.isNaN(currentScore) ? null : currentScore,
      targetScore: formData.targetScore
        ? Number.parseInt(formData.targetScore, 10)
        : null,
      studyMinutesPerDay: Number.isNaN(studyMinutesPerDay)
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
                      "Chọn mức độ phù hợp nhất với trình độ hiện tại của bạn"}
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
                    <RadioGroup
                      value={formData.level}
                      onValueChange={(value) =>
                        setFormData((prev) => ({ ...prev, level: value }))
                      }
                      className="space-y-3"
                    >
                      {onboardingLevels.map((level) => (
                        <label
                          key={level.value}
                          className={`flex cursor-pointer items-center justify-between rounded-xl border p-4 transition-all ${
                            formData.level === level.value
                              ? "border-primary bg-accent"
                              : "border-border hover:border-primary/50 hover:bg-accent/50"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <RadioGroupItem value={level.value} />
                            <div>
                              <div className="font-medium text-foreground">
                                {level.label}
                              </div>
                              <div className="text-sm text-muted-foreground">
                                {level.desc}
                              </div>
                            </div>
                          </div>
                          <Badge variant="secondary">{level.score}</Badge>
                        </label>
                      ))}
                    </RadioGroup>
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
                        {formData.level
                          ? onboardingLevels.find((item) => item.value === formData.level)?.label
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

                  {formData.level && formData.targetScore && formData.deadline && (
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
