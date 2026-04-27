"use client";

import { useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  CheckCircle2,
  Headphones,
  Sparkles,
  Target,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  fallbackMockTestResult,
  mockTestResultAnalysis,
} from "@src/data/mock-test-result";
import {
  attemptsService,
  type PracticeAttemptResult,
  type SavePracticeAttemptResponse,
} from "@src/services/attemptsService";
import { weeklyCheckService } from "@src/services/weeklyCheckService";

type MockTestResultState = {
  scorePercentage?: number;
  estimatedScore?: string;
  level?: string;
  attempt?: SavePracticeAttemptResponse;
} | null;

type ResultKind = "mock" | "full" | "mini" | "weekly";

const resultCopy: Record<
  ResultKind,
  {
    title: string;
    description: string;
    loadingMessage: string;
    loadErrorPrefix: string;
    scoreLabel: string;
    retryHref: string;
    retryLabel: string;
    nextStepDescription: string;
  }
> = {
  mock: {
    title: "Hoàn thành Mock Test!",
    description: "Dựa trên kết quả, đây là đánh giá bài thi của bạn",
    loadingMessage: "Loading saved mock-test result from FastAPI...",
    loadErrorPrefix: "Could not load saved mock-test result",
    scoreLabel: "Điểm ước tính",
    retryHref: "/mock-test/runner?type=full",
    retryLabel: "Làm lại bài test",
    nextStepDescription:
      "Tiếp tục luyện tập với Mini Test hoặc làm thêm Full Test để cải thiện độ chính xác và làm quen với áp lực thời gian.",
  },
  full: {
    title: "Hoàn thành Full TOEIC Test!",
    description: "Dựa trên kết quả, đây là đánh giá bài thi đầy đủ của bạn",
    loadingMessage: "Loading saved full-test result from FastAPI...",
    loadErrorPrefix: "Could not load saved full-test result",
    scoreLabel: "Điểm ước tính",
    retryHref: "/mock-test/runner?type=full",
    retryLabel: "Làm lại Full Test",
    nextStepDescription:
      "Xem các vùng điểm yếu rồi luyện tiếp bằng Practice hoặc Mini Test để kéo điểm từng phần lên ổn định hơn.",
  },
  mini: {
    title: "Hoàn thành Mini Test!",
    description: "Đây là phần tổng kết nhanh cho bài Mini Test vừa nộp",
    loadingMessage: "Loading saved mini-test result from FastAPI...",
    loadErrorPrefix: "Could not load saved mini-test result",
    scoreLabel: "Số câu đúng",
    retryHref: "/mock-test/runner?type=mini&test=1",
    retryLabel: "Làm lại Mini Test",
    nextStepDescription:
      "Dùng các câu sai để ôn lại đúng kỹ năng vừa kiểm tra, rồi tạo một Mini Test mới theo part còn yếu.",
  },
  weekly: {
    title: "Hoàn thành Weekly Check!",
    description: "Đây là kết quả bài kiểm tra hằng tuần được tạo từ điểm yếu của bạn",
    loadingMessage: "Loading saved weekly-check result from FastAPI...",
    loadErrorPrefix: "Could not load saved weekly-check result",
    scoreLabel: "Số câu đúng",
    retryHref: "/weekly-check/runner",
    retryLabel: "Làm lại Weekly Check",
    nextStepDescription:
      "Weekly Check đã cập nhật dữ liệu học tập. Hãy chuyển sang Practice để ôn ngay các kỹ năng đang yếu nhất.",
  },
};

function getResultKind(pathname: string): ResultKind {
  if (pathname.startsWith("/weekly-check/result")) return "weekly";
  if (pathname.startsWith("/mini-test/result")) return "mini";
  if (pathname.startsWith("/full-test/result")) return "full";
  return "mock";
}

function getLevelFromAccuracy(accuracy: number) {
  if (accuracy >= 90) return "Cao cấp";
  if (accuracy >= 70) return "Trung cấp cao";
  if (accuracy >= 50) return "Trung cấp";
  if (accuracy >= 30) return "Sơ cấp";
  return "Mới bắt đầu";
}

function formatScore(result: SavePracticeAttemptResponse["result"] | null | undefined) {
  if (!result) return null;
  if (result.listeningScore || result.readingScore) {
    return `${result.listeningScore || 0} + ${result.readingScore || 0} = ${
      result.scaledScore || 0
    }`;
  }
  return result.scaledScore ? String(result.scaledScore) : null;
}

function summarizeSection(
  result: SavePracticeAttemptResponse["result"] | null | undefined,
  section: "Listening" | "Reading",
) {
  if (!result) return null;
  const parts = result.partBreakdown.filter((item) =>
    section === "Listening" ? item.part <= 4 : item.part >= 5,
  );

  if (parts.length === 0) return null;

  const total = parts.reduce((sum, item) => sum + item.total, 0);
  const correct = parts.reduce((sum, item) => sum + item.correct, 0);
  const accuracy = total > 0 ? Math.round((correct / total) * 100) : 0;

  return `${correct}/${total} correct (${accuracy}%)`;
}

function formatDuration(seconds?: number | null, minutes?: number | null) {
  if (typeof minutes === "number" && minutes > 0) {
    return `${minutes} min`;
  }

  if (!seconds || seconds <= 0) return "0 min";

  const roundedMinutes = Math.max(1, Math.round(seconds / 60));
  return `${roundedMinutes} min`;
}

export function MockTestResultPage() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [fetchedResult, setFetchedResult] = useState<PracticeAttemptResult | null>(null);
  const [isLoadingResult, setIsLoadingResult] = useState(false);
  const [resultLoadError, setResultLoadError] = useState<string | null>(null);
  const resultState = location.state as MockTestResultState;
  const attemptId = Number(searchParams.get("attemptId"));
  const resultKind = getResultKind(location.pathname);
  const copy = resultCopy[resultKind];
  const backendResult = resultState?.attempt?.result || fetchedResult;

  useEffect(() => {
    if (resultState?.attempt?.result || !Number.isFinite(attemptId) || attemptId <= 0) {
      return;
    }

    let cancelled = false;

    async function loadResult() {
      setIsLoadingResult(true);
      setResultLoadError(null);

      try {
        const data =
          resultKind === "weekly"
            ? await weeklyCheckService.getResult(attemptId)
            : await attemptsService.getMockTestAttemptResult(attemptId);
        if (!cancelled) {
          setFetchedResult(data);
        }
      } catch (error) {
        if (!cancelled) {
          setResultLoadError(
            error instanceof Error
              ? error.message
              : "Could not load this test result.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoadingResult(false);
        }
      }
    }

    void loadResult();

    return () => {
      cancelled = true;
    };
  }, [attemptId, resultKind, resultState?.attempt?.result]);

  const scorePercentage =
    backendResult?.accuracyPct ?? resultState?.scorePercentage ?? fallbackMockTestResult.scorePercentage;
  const estimatedScore =
    formatScore(backendResult) ?? resultState?.estimatedScore ?? fallbackMockTestResult.estimatedScore;
  const displayScore =
    resultKind === "mini" || resultKind === "weekly"
      ? backendResult
        ? `${backendResult.correctCount}/${backendResult.totalQuestions}`
        : estimatedScore
      : estimatedScore;
  const level = resultState?.level ?? getLevelFromAccuracy(scorePercentage) ?? fallbackMockTestResult.level;
  const listeningSummary = summarizeSection(backendResult, "Listening");
  const readingSummary = summarizeSection(backendResult, "Reading");
  const summaryItems = backendResult
    ? [
        { label: "Correct", value: `${backendResult.correctCount}/${backendResult.totalQuestions}` },
        { label: "Wrong", value: String(backendResult.wrongCount) },
        { label: "Unanswered", value: String(backendResult.unansweredCount) },
        {
          label: "Time",
          value: formatDuration(backendResult.durationSeconds, backendResult.durationMinutes),
        },
      ]
    : [];
  const weakAreas = backendResult?.weakAreas.slice(0, 3) || [];
  const reviewQuestions =
    backendResult?.questions.filter((question) => !question.isCorrect).slice(0, 5) || [];

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="container mx-auto flex h-16 items-center px-4">
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Target className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-semibold text-foreground">
              GetGoals
            </span>
          </Link>
        </div>
      </header>

      <div className="container mx-auto px-4 py-12 lg:py-20">
        <div className="mx-auto max-w-2xl text-center">
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-primary/10">
            <CheckCircle2 className="h-10 w-10 text-primary" />
          </div>

          <h1 className="mb-2 text-3xl font-bold text-foreground">
            {copy.title}
          </h1>
          <p className="mb-8 text-muted-foreground">
            {copy.description}
          </p>

          {(isLoadingResult || resultLoadError) && (
            <Card className="mb-8 rounded-2xl border-border">
              <CardContent className="p-4 text-sm text-muted-foreground">
                {isLoadingResult
                  ? copy.loadingMessage
                  : `${copy.loadErrorPrefix}: ${resultLoadError}`}
              </CardContent>
            </Card>
          )}

          <Card className="mb-8 rounded-2xl border-border">
            <CardContent className="p-8">
              <div className="mb-6 grid gap-6 md:grid-cols-3">
                <div className="text-center">
                  <div className="mb-1 text-4xl font-bold text-primary">
                    {scorePercentage}%
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Độ chính xác
                  </div>
                </div>

                <div className="text-center">
                  <div className="mb-1 text-4xl font-bold text-foreground">
                    {displayScore}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {copy.scoreLabel}
                  </div>
                </div>

                <div className="text-center">
                  <Badge className="bg-primary/10 px-4 py-1 text-lg text-primary hover:bg-primary/20">
                    {level}
                  </Badge>
                  <div className="mt-2 text-sm text-muted-foreground">
                    Trình độ
                  </div>
                </div>
              </div>

              <div className="border-t border-border pt-6">
                <h3 className="mb-4 flex items-center justify-center gap-2 font-semibold text-foreground">
                  <BarChart3 className="h-5 w-5 text-primary" />
                  Phân tích kết quả
                </h3>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="rounded-xl bg-[#A6C8FF] p-4">
                    <div className="mb-2 flex items-center gap-2">
                      <Headphones className="h-4 w-4 text-primary" />
                      <span className="font-medium text-foreground">
                        {mockTestResultAnalysis[0].section}
                      </span>
                    </div>
                    <p className="text-muted-foreground">
                      {listeningSummary || mockTestResultAnalysis[0].description}
                    </p>
                  </div>

                  <div className="rounded-xl bg-[#A6C8FF] p-4">
                    <div className="mb-2 flex items-center gap-2">
                      <BookOpen className="h-4 w-4 text-primary" />
                      <span className="font-medium text-foreground">
                        {mockTestResultAnalysis[1].section}
                      </span>
                    </div>
                    <p className="text-muted-foreground">
                      {readingSummary || mockTestResultAnalysis[1].description}
                    </p>
                  </div>
                </div>

                {summaryItems.length > 0 && (
                  <div className="mt-6 grid gap-3 sm:grid-cols-4">
                    {summaryItems.map((item) => (
                      <div key={item.label} className="rounded-xl bg-muted p-3 text-center">
                        <div className="text-lg font-bold text-foreground">{item.value}</div>
                        <div className="text-xs text-muted-foreground">{item.label}</div>
                      </div>
                    ))}
                  </div>
                )}

                {weakAreas.length > 0 && (
                  <div className="mt-6 rounded-xl border border-border p-4 text-left">
                    <h4 className="mb-3 text-sm font-semibold text-foreground">
                      Focus areas from this result
                    </h4>
                    <div className="space-y-3">
                      {weakAreas.map((area) => (
                        <div
                          key={`${area.type}-${area.label}`}
                          className="rounded-lg bg-muted/60 p-3"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <span className="font-medium text-foreground">{area.label}</span>
                            <Badge variant="outline">
                              {Math.round(area.accuracyPct)}%
                            </Badge>
                          </div>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {area.correct}/{area.total} correct
                            {area.suggestion ? ` - ${area.suggestion}` : ""}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {reviewQuestions.length > 0 && (
                  <div className="mt-6 rounded-xl border border-border p-4 text-left">
                    <h4 className="mb-3 text-sm font-semibold text-foreground">
                      Questions to review
                    </h4>
                    <div className="space-y-2">
                      {reviewQuestions.map((question) => (
                        <div
                          key={`${question.questionId}-${question.questionNumber}`}
                          className="rounded-lg bg-muted/60 p-3 text-sm"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <span className="font-medium text-foreground">
                              Question {question.questionNumber} - Part {question.part}
                            </span>
                            <Badge variant="secondary">{question.skill}</Badge>
                          </div>
                          <p className="mt-1 text-muted-foreground line-clamp-2">
                            {question.question}
                          </p>
                          <p className="mt-2 text-xs text-muted-foreground">
                            Your answer: {question.userAnswer || "Skipped"} | Correct:{" "}
                            {question.correctAnswer || "Unavailable"}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="mb-8 rounded-2xl border-primary bg-primary/5">
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary">
                  <Sparkles className="h-5 w-5 text-primary-foreground" />
                </div>

                <div className="text-left">
                  <h3 className="mb-1 font-semibold text-foreground">
                    Bước tiếp theo
                  </h3>
                  <p className="mb-4 text-sm text-muted-foreground">
                    {copy.nextStepDescription}
                  </p>

                  <Button asChild>
                    <Link to="/mock-test">
                      Quay lại Mock Test
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="flex items-center justify-center gap-4">
            <Button variant="outline" asChild>
              <Link to={copy.retryHref}>{copy.retryLabel}</Link>
            </Button>

            <Button variant="ghost" asChild>
              <Link to="/dashboard">Đi đến Dashboard</Link>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
