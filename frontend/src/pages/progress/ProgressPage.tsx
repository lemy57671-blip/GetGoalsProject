"use client";

import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpen,
  Brain,
  CalendarDays,
  Clock3,
  FileText,
  Flame,
  Headphones,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
  Trophy,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  heatmap,
  roadmapSteps,
} from "@src/data/progress";
import { useLanguage } from "@src/contexts/LanguageContext";
import { progressService, ProgressView } from "@src/services/progressService";

function ScoreLineChart({
  scoreHistory,
}: {
  scoreHistory: Array<{ week: string; score: number }>;
}) {
  const width = 520;
  const height = 220;
  const padding = 24;
  const safeScoreHistory =
    scoreHistory.length > 0 ? scoreHistory : [{ week: "Now", score: 0 }];

  const values = safeScoreHistory.map((d) => d.score);
  const min = Math.min(...values) - 20;
  const max = Math.max(...values) + 20;

  const points = safeScoreHistory.map((d, i) => {
    const denominator = Math.max(safeScoreHistory.length - 1, 1);
    const x = padding + (i * (width - padding * 2)) / denominator;
    const y =
      height - padding - ((d.score - min) / (max - min)) * (height - padding * 2);
    return `${x},${y}`;
  });

  return (
    <div className="w-full overflow-hidden rounded-3xl border border-border bg-card p-4">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-foreground">
            Tiến bộ điểm ước lượng
          </h3>
          <p className="text-sm text-muted-foreground">
            Theo dõi mức điểm TOEIC qua từng tuần
          </p>
        </div>
        <Badge className="bg-[#EEF4FF] text-primary hover:bg-[#EEF4FF]">
          Live accuracy trend
        </Badge>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="h-[220px] w-full">
        {[0, 1, 2, 3].map((i) => {
          const y = padding + (i * (height - padding * 2)) / 3;
          return (
            <line
              key={i}
              x1={padding}
              y1={y}
              x2={width - padding}
              y2={y}
              stroke="hsl(var(--border))"
              strokeDasharray="4 4"
            />
          );
        })}

        <polyline
          fill="none"
          stroke="hsl(var(--primary))"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
          points={points.join(" ")}
        />

        {safeScoreHistory.map((d, i) => {
          const denominator = Math.max(safeScoreHistory.length - 1, 1);
          const x = padding + (i * (width - padding * 2)) / denominator;
          const y =
            height - padding - ((d.score - min) / (max - min)) * (height - padding * 2);
          return (
            <g key={d.week}>
              <circle cx={x} cy={y} r="5" fill="hsl(var(--primary))" />
              <circle cx={x} cy={y} r="10" fill="hsl(var(--primary) / 0.12)" />
              <text
                x={x}
                y={height - 6}
                textAnchor="middle"
                fontSize="12"
                fill="hsl(var(--muted-foreground))"
              >
                {d.week}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="mt-3 flex items-center justify-between text-sm">
        <span className="text-muted-foreground">
          Start: {safeScoreHistory[0]?.score ?? 0}%
        </span>
        <span className="font-medium text-foreground">
          Current: {safeScoreHistory.at(-1)?.score ?? 0}%
        </span>
        <span className="text-muted-foreground">Target: 100%</span>
      </div>
    </div>
  );
}

function WeeklyBarChart({
  weeklyActivity,
}: {
  weeklyActivity: Array<{ day: string; minutes: number }>;
}) {
  const safeWeeklyActivity =
    weeklyActivity.length > 0 ? weeklyActivity : [{ day: "Now", minutes: 0 }];
  const max = Math.max(...safeWeeklyActivity.map((d) => d.minutes), 1);

  return (
    <div className="rounded-3xl border border-border bg-card p-5">
      <div className="mb-5">
        <h3 className="font-semibold text-foreground">Thời gian học tuần này</h3>
        <p className="text-sm text-muted-foreground">
          Tổng thời gian học theo từng ngày
        </p>
      </div>

      <div className="flex h-56 items-end justify-between gap-3">
        {safeWeeklyActivity.map((item) => (
          <div key={item.day} className="flex flex-1 flex-col items-center gap-2">
            <div className="flex h-44 w-full items-end">
              <div
                className="w-full rounded-t-2xl bg-primary/85 transition-all"
                style={{ height: `${(item.minutes / max) * 100}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground">{item.day}</span>
            <span className="text-xs font-medium text-foreground">
              {item.minutes}m
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function extractPartNumber(partLabel: string) {
  const matched = partLabel.match(/\d+/);
  return matched ? Number(matched[0]) : null;
}

function buildRecommendedPracticeUrl(progress: ProgressView) {
  const weakPart = progress.partProgress
    .map((item) => ({
      part: extractPartNumber(item.part),
      accuracy: item.accuracy,
    }))
    .filter((item): item is { part: number; accuracy: number } =>
      Boolean(item.part && item.part >= 1 && item.part <= 7),
    )
    .sort((left, right) => left.accuracy - right.accuracy)[0];

  const weakSkill = progress.skillProgress
    .slice()
    .sort((left, right) => left.accuracy - right.accuracy)[0];

  if (!weakPart && !weakSkill) {
    return "/practice?recommended=true";
  }

  const params = new URLSearchParams({
    mode: "recommended",
    difficulty: "medium",
    count: "20",
    source: "progress",
  });

  if (weakPart?.part) {
    params.set("parts", String(weakPart.part));
  } else if (weakSkill?.name.toLowerCase().includes("listening")) {
    params.set("parts", "1,2,3,4");
  } else if (weakSkill?.name.toLowerCase().includes("reading")) {
    params.set("parts", "5,6,7");
  } else {
    params.set("parts", "5");
    params.set("skill", "grammar_vocabulary");
  }

  if (weakSkill?.name) {
    params.set("skill", weakSkill.name);
  }

  return `/practice/runner?${params.toString()}`;
}

export function ProgressPage() {
  const { t } = useLanguage();
  const [progressData, setProgressData] = useState<ProgressView | null>(null);
  const [isLoadingProgress, setIsLoadingProgress] = useState(true);
  const [progressError, setProgressError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadProgress() {
      setIsLoadingProgress(true);
      setProgressError(null);

      try {
        const summary = await progressService.getSummary();

        if (cancelled) return;

        setProgressData(summary);
      } catch (error) {
        if (!cancelled) {
          setProgressError(
            error instanceof Error
              ? error.message
              : "Could not load progress data from FastAPI.",
          );
          setProgressData(null);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingProgress(false);
        }
      }
    }

    loadProgress();

    return () => {
      cancelled = true;
    };
  }, []);

  const liveProgress = progressData ?? {
    totalAttempts: 0,
    totalCorrectAnswers: 0,
    totalWrongAnswers: 0,
    averageAccuracy: 0,
    pendingReviewCount: 0,
    weeklyStudyMinutes: [],
    scoreHistory: [],
    weeklyActivity: [],
    skillProgress: [],
    partProgress: [],
    recentPracticeAttempts: [],
    recentMockTestsCount: 0,
    weeklyMinutes: 0,
  };
  const completedTests = liveProgress.totalAttempts;
  const currentScore = Math.round(liveProgress.averageAccuracy);
  const targetScore = 100;
  const daysLeft = liveProgress.pendingReviewCount;
  const streak = liveProgress.weeklyStudyMinutes.filter(
    (point) => point.studyMinutes > 0 || point.attemptsCount > 0,
  ).length;
  const weeklyHours = Number((liveProgress.weeklyMinutes / 60).toFixed(1));
  const targetProgress = Math.round((currentScore / targetScore) * 100);
  const skillProgress = useMemo(
    () =>
      liveProgress.skillProgress.map((skill) => ({
        ...skill,
        icon:
          skill.name.toLowerCase().includes("listening")
            ? Headphones
            : skill.name.toLowerCase().includes("reading")
              ? FileText
              : skill.name.toLowerCase().includes("grammar")
                ? Brain
                : BookOpen,
      })),
    [liveProgress.skillProgress],
  );
  const partProgress = liveProgress.partProgress;
  const recommendedPracticeUrl = buildRecommendedPracticeUrl(liveProgress);
  const weeklyCheckUrl = "/weekly-check/runner?count=25&source=progress";

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="rounded-[28px] border border-border bg-[radial-gradient(circle_at_top,_rgba(124,131,255,0.12),_transparent_35%),linear-gradient(180deg,#F8FAFF_0%,#EEF4FF_100%)] p-6 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-foreground">
                Tiến độ học tập
              </h1>
              <p className="mt-2 max-w-2xl text-muted-foreground">
                Theo dõi điểm số, kỹ năng, từng Part TOEIC và biết rõ bạn nên học
                gì tiếp theo.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Button asChild className="rounded-2xl bg-primary text-primary-foreground hover:bg-primary/90">
                <Link to="/roadmap">
                  Xem lộ trình
                </Link>
              </Button>
              <Button
                asChild
                variant="outline"
                className="rounded-2xl border-border bg-white/80 text-foreground hover:bg-[#EEF4FF]"
              >
                <Link to={recommendedPracticeUrl}>
                  {t("progress.recommended")}
                </Link>
              </Button>
              <Button
                asChild
                variant="outline"
                className="rounded-2xl border-border bg-white/80 text-foreground hover:bg-[#EEF4FF]"
              >
                <Link to={weeklyCheckUrl}>
                  {t("progress.weekly")}
                </Link>
              </Button>
            </div>
          </div>
        </div>

        {(isLoadingProgress || progressError || liveProgress.totalAttempts === 0) && (
          <Card className="border-[#E7EEF9] bg-[#F8FBFF]">
            <CardContent className="py-4 text-sm text-muted-foreground">
              {isLoadingProgress
                ? "Loading progress data from FastAPI..."
                : progressError
                  ? `Could not load progress data: ${progressError}`
                  : "No progress attempts yet. Complete a practice session to populate these charts."}
            </CardContent>
          </Card>
        )}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
          <Card className="rounded-3xl border-border bg-card shadow-sm">
            <CardContent className="flex items-center gap-4 pt-6">
              <div className="rounded-2xl bg-[#EEF4FF] p-3">
                <Trophy className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Average accuracy</p>
                <p className="text-2xl font-bold text-foreground">{currentScore}%</p>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-border bg-card shadow-sm">
            <CardContent className="flex items-center gap-4 pt-6">
              <div className="rounded-2xl bg-[#EEF4FF] p-3">
                <Target className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Target accuracy</p>
                <p className="text-2xl font-bold text-foreground">{targetScore}%</p>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-border bg-card shadow-sm">
            <CardContent className="flex items-center gap-4 pt-6">
              <div className="rounded-2xl bg-[#EEF4FF] p-3">
                <Sparkles className="h-5 w-5 text-accent" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">
                  Correct answers
                </p>
                <p className="text-2xl font-bold text-foreground">
                  {liveProgress.totalCorrectAnswers}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-border bg-card shadow-sm">
            <CardContent className="flex items-center gap-4 pt-6">
              <div className="rounded-2xl bg-[#EEF4FF] p-3">
                <CalendarDays className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Pending review</p>
                <p className="text-2xl font-bold text-foreground">{daysLeft}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-border bg-card shadow-sm">
            <CardContent className="flex items-center gap-4 pt-6">
              <div className="rounded-2xl bg-[#EEF4FF] p-3">
                <Flame className="h-5 w-5 text-orange-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Active days</p>
                <p className="text-2xl font-bold text-foreground">{streak}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-border bg-card shadow-sm">
            <CardContent className="flex items-center gap-4 pt-6">
              <div className="rounded-2xl bg-[#EEF4FF] p-3">
                <Clock3 className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Attempts</p>
                <p className="text-2xl font-bold text-foreground">
                  {completedTests}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="rounded-3xl border-border bg-card shadow-sm">
          <CardHeader>
            <CardTitle>Bạn đang ở đâu?</CardTitle>
            <CardDescription>
              Tiến độ hiện tại so với mục tiêu TOEIC
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm text-muted-foreground">
                  Mức tiến gần mục tiêu
                </p>
                <p className="text-xl font-semibold text-foreground">
                  {currentScore}/{targetScore} điểm
                </p>
              </div>
              <Badge className="bg-[#EEF4FF] text-primary hover:bg-[#EEF4FF]">
                {targetProgress}% mục tiêu
              </Badge>
            </div>
            <Progress value={targetProgress} className="h-3" />
          </CardContent>
        </Card>

        <div className="grid gap-6 xl:grid-cols-3">
          <div className="xl:col-span-2">
            <ScoreLineChart scoreHistory={liveProgress.scoreHistory} />
          </div>
          <WeeklyBarChart weeklyActivity={liveProgress.weeklyActivity} />
        </div>

        <div className="grid gap-6 xl:grid-cols-3">
          <Card className="rounded-3xl border-border bg-card shadow-sm xl:col-span-2">
            <CardHeader>
              <CardTitle>Theo kỹ năng</CardTitle>
              <CardDescription>
                Listening, Reading, Grammar và Vocabulary
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              {skillProgress.map((skill) => {
                const Icon = skill.icon;
                const isUp = skill.trend === "up";

                return (
                  <div
                    key={skill.name}
                    className="rounded-3xl border border-border bg-[linear-gradient(180deg,#FFFFFF_0%,#F8FAFF_100%)] p-5"
                  >
                    <div className="mb-4 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="rounded-2xl bg-[#EEF4FF] p-3">
                          <Icon className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <p className="font-semibold text-foreground">
                            {skill.name}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            Accuracy {skill.accuracy}%
                          </p>
                        </div>
                      </div>

                      <div
                        className={`flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium ${
                          isUp
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-rose-100 text-rose-700"
                        }`}
                      >
                        {isUp ? (
                          <TrendingUp className="h-3 w-3" />
                        ) : (
                          <TrendingDown className="h-3 w-3" />
                        )}
                        {skill.change}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">Mức hiện tại</span>
                        <span className="font-medium text-foreground">
                          {skill.value}%
                        </span>
                      </div>
                      <Progress value={skill.value} className="h-2.5" />
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-border bg-[linear-gradient(180deg,#EEF4FF_0%,#FFFFFF_100%)] shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-accent" />
                AI Insight
              </CardTitle>
              <CardDescription>Bạn nên học gì tiếp theo?</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-2xl border border-border bg-white/80 p-4">
                <p className="text-sm font-medium text-foreground">
                  Điểm mạnh hiện tại
                </p>
                <p className="mt-2 text-sm text-muted-foreground">
                  Listening Part 1 và Part 5 đang khá ổn, tốc độ xử lý câu ngắn tốt.
                </p>
              </div>

              <div className="rounded-2xl border border-border bg-white/80 p-4">
                <p className="text-sm font-medium text-foreground">
                  Điểm yếu lớn nhất
                </p>
                <p className="mt-2 text-sm text-muted-foreground">
                  Part 7 và Part 4 vẫn thấp, đặc biệt là tốc độ đọc và bắt ý chính.
                </p>
              </div>

              <div className="rounded-2xl border border-border bg-white/80 p-4">
                <p className="text-sm font-medium text-foreground">
                  Gợi ý tuần này
                </p>
                <p className="mt-2 text-sm text-muted-foreground">
                  Ưu tiên Reading speed + inference questions, sau đó làm 1 Weekly
                  Check để đo lại.
                </p>
              </div>

              <Button asChild className="w-full rounded-2xl bg-primary text-primary-foreground hover:bg-primary/90">
                <Link to={recommendedPracticeUrl}>
                  {t("progress.recommended")}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>

        <Card className="rounded-3xl border-border bg-card shadow-sm">
          <CardHeader>
            <CardTitle>Theo từng Part TOEIC</CardTitle>
            <CardDescription>Biết rõ bạn mạnh và yếu ở đâu</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {partProgress.map((item) => {
              const badgeClass =
                item.status === "Yếu nhất"
                  ? "bg-rose-100 text-rose-700"
                  : item.status.includes("Vững") || item.status.includes("Khá")
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-[#EEF4FF] text-primary";

              return (
                <div
                  key={item.part}
                  className="rounded-3xl border border-border bg-[linear-gradient(180deg,#FFFFFF_0%,#F8FAFF_100%)] p-5"
                >
                  <div className="mb-3 flex items-center justify-between">
                    <p className="font-semibold text-foreground">{item.part}</p>
                    <Badge className={`${badgeClass} hover:${badgeClass}`}>
                      {item.status}
                    </Badge>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <div className="mb-1 flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">Accuracy</span>
                        <span className="font-medium text-foreground">
                          {item.accuracy}%
                        </span>
                      </div>
                      <Progress value={item.accuracy} className="h-2.5" />
                    </div>

                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Tốc độ</span>
                      <span className="font-medium text-foreground">{item.speed}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        <div className="grid gap-6 xl:grid-cols-3">
          <Card className="rounded-3xl border-border bg-card shadow-sm xl:col-span-2">
            <CardHeader>
              <CardTitle>Hoạt động học gần đây</CardTitle>
              <CardDescription>
                Duy trì đều đặn sẽ giúp tăng điểm ổn định hơn
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl bg-[#EEF4FF] p-4">
                  <p className="text-sm text-muted-foreground">
                    Tổng giờ học tuần này
                  </p>
                  <p className="mt-1 text-2xl font-bold text-foreground">
                    {weeklyHours}h
                  </p>
                </div>
                <div className="rounded-2xl bg-[#EEF4FF] p-4">
                  <p className="text-sm text-muted-foreground">Mini Test đã làm</p>
                  <p className="mt-1 text-2xl font-bold text-foreground">
                    {liveProgress.recentPracticeAttempts.length}
                  </p>
                </div>
                <div className="rounded-2xl bg-[#EEF4FF] p-4">
                  <p className="text-sm text-muted-foreground">Full Test đã làm</p>
                  <p className="mt-1 text-2xl font-bold text-foreground">
                    {liveProgress.recentMockTestsCount}
                  </p>
                </div>
              </div>

              <div>
                <p className="mb-3 font-medium text-foreground">
                  Nhịp học 4 tuần gần đây
                </p>
                <div className="grid grid-cols-7 gap-2">
                  {heatmap.flatMap((row, rowIndex) =>
                    row.map((value, colIndex) => {
                      const bg =
                        value === 0
                          ? "bg-muted"
                          : value === 1
                            ? "bg-primary/20"
                            : value === 2
                              ? "bg-primary/45"
                              : "bg-primary";
                      return (
                        <div
                          key={`${rowIndex}-${colIndex}`}
                          className={`aspect-square rounded-xl ${bg}`}
                        />
                      );
                    }),
                  )}
                </div>
              </div>

              <div className="space-y-3 border-t border-border pt-4">
                <p className="font-medium text-foreground">
                  Recent practice attempts from FastAPI
                </p>
                {liveProgress.recentPracticeAttempts.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No practice attempts yet.
                  </p>
                ) : (
                  liveProgress.recentPracticeAttempts.map((attempt) => (
                    <div
                      key={attempt.id}
                      className="flex items-center justify-between rounded-2xl border border-border bg-[#F8FBFF] px-4 py-3"
                    >
                      <div>
                        <p className="font-medium text-foreground">
                          {attempt.title || `Practice attempt #${attempt.id}`}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {attempt.correctCount}/{attempt.totalQuestions} correct
                          - {Math.round(attempt.accuracy)}%
                        </p>
                      </div>
                      <Badge variant="secondary">#{attempt.id}</Badge>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-border bg-card shadow-sm">
            <CardHeader>
              <CardTitle>Lộ trình hiện tại</CardTitle>
              <CardDescription>Bạn nên tiến theo thứ tự nào?</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {roadmapSteps.map((step, index) => (
                <div key={step.title} className="flex items-start gap-3">
                  <div
                    className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
                      step.done
                        ? "bg-primary text-primary-foreground"
                        : (step as { current?: boolean }).current
                          ? "bg-[#EEF4FF] text-primary ring-2 ring-primary/20"
                          : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-foreground">{step.title}</p>
                    <p className="text-sm text-muted-foreground">
                      {step.done
                        ? "Đã hoàn thành tốt."
                        : (step as { current?: boolean }).current
                          ? "Đang là giai đoạn cần ưu tiên."
                          : "Sẽ mở sau khi hoàn thành bước trước."}
                    </p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
