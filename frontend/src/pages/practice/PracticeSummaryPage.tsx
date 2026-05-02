"use client";

import { useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Brain,
  CheckCircle2,
  ChevronRight,
  Clock,
  Headphones,
  MinusCircle,
  RotateCcw,
  Sparkles,
  Target,
  TrendingUp,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ProFeatureGuard } from "@/components/pro-feature-guard";
import { ChatPanel } from "@src/components/chat/ChatPanel";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  practiceResults as mockPracticeResults,
  reviewQuestions as mockReviewQuestions,
  skillBreakdown as mockSkillBreakdown,
  weaknesses as mockWeaknesses,
} from "@src/data/practice-summary";
import {
  attemptsService,
  PracticeAttemptResult,
  SavePracticeAttemptResponse,
} from "@src/services/attemptsService";
import { ApiError } from "@src/services/apiClient";
import { chatService } from "@src/services/chatService";

type SummaryAiMessage = {
  role: "assistant" | "user";
  content: string;
};

function isUsableReviewFocusRetryUrl(value: unknown) {
  if (typeof value !== "string" || !value.startsWith("/practice/runner?")) {
    return false;
  }

  const query = value.split("?")[1] || "";
  const params = new URLSearchParams(query);
  return params.get("mode") === "review-focus" && Boolean(params.get("reviewItemId"));
}

export function PracticeSummaryPage() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [aiMessage, setAiMessage] = useState("");
  const [aiMessages, setAiMessages] = useState<SummaryAiMessage[]>([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiConversationId, setAiConversationId] = useState<number | null>(null);
  const [selectedQuestion, setSelectedQuestion] = useState<number | null>(null);
  const [fetchedResult, setFetchedResult] = useState<PracticeAttemptResult | null>(null);
  const [isLoadingResult, setIsLoadingResult] = useState(false);
  const [resultLoadError, setResultLoadError] = useState<string | null>(null);
  const summaryState = location.state as {
    attempt?: SavePracticeAttemptResponse;
    retryUrl?: string;
  } | null;
  const stateAttempt = summaryState?.attempt;
  const attemptId = Number(searchParams.get("attemptId"));
  const attempt =
    stateAttempt ||
    (fetchedResult
      ? {
          attemptId: fetchedResult.attemptId,
          reviewQueuedCount: 0,
          skillStatsUpdated: 0,
          partStatsUpdated: 0,
          result: fetchedResult,
        }
      : undefined);
  const result: PracticeAttemptResult | null = attempt?.result || null;

  useEffect(() => {
    if (stateAttempt || !Number.isFinite(attemptId) || attemptId <= 0) {
      return;
    }

    let cancelled = false;

    async function loadResult() {
      setIsLoadingResult(true);
      setResultLoadError(null);

      try {
        const data = await attemptsService.getPracticeAttemptResult(attemptId);
        if (!cancelled) {
          setFetchedResult(data);
        }
      } catch (error) {
        if (!cancelled) {
          setResultLoadError(
            error instanceof Error
              ? error.message
              : "Could not load this practice result.",
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
  }, [attemptId, stateAttempt]);
  const isReviewFocusResult =
    result?.title?.toLowerCase().includes("review focus") ||
    result?.questions.some((item) => item.skill?.toLowerCase().includes("review"));
  const retryUrl =
    isReviewFocusResult && isUsableReviewFocusRetryUrl(summaryState?.retryUrl)
      ? summaryState?.retryUrl
      : "/practice/runner";
  const reviewFocusPart = result?.partBreakdown[0]?.part;
  const reviewFocusSkill = result?.skillBreakdown[0]?.skill;
  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs
      .toString()
      .padStart(2, "0")}`;
  };
  const sendAiMessage = async (messageOverride?: string) => {
    if (aiLoading) return;

    const userMessage = (messageOverride || aiMessage).trim();
    if (!userMessage) return;

    const activeAttemptId =
      result?.attemptId ||
      attempt?.attemptId ||
      (Number.isFinite(attemptId) && attemptId > 0 ? attemptId : null);

    setAiMessages((current) => [...current, { role: "user", content: userMessage }]);
    setAiMessage("");
    setAiLoading(true);

    try {
      const response = await chatService.sendDetailed({
        message: userMessage,
        conversation_id: aiConversationId,
        attempt_id: activeAttemptId,
        context_type: "practice_review",
      });

      if (typeof response.conversation_id === "number") {
        setAiConversationId(response.conversation_id);
      }
      setAiMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.reply || "AI Tutor chưa tạo được phản hồi.",
        },
      ]);
    } catch (error) {
      const message =
        error instanceof ApiError && [401, 403].includes(error.status)
          ? "AI Tutor là tính năng Pro. Vui lòng đăng nhập tài khoản Pro để hỏi sau bài luyện."
          : error instanceof Error
            ? `Không gọi được AI Tutor: ${error.message}`
            : "Không gọi được AI Tutor.";

      setAiMessages((current) => [...current, { role: "assistant", content: message }]);
    } finally {
      setAiLoading(false);
    }
  };
  const practiceResults = result
    ? {
        totalQuestions: result.totalQuestions,
        correct: result.correctCount,
        incorrect: result.wrongCount,
        skipped: result.unansweredCount,
        timeSpent: formatDuration(result.durationSeconds),
        accuracy: Math.round(result.accuracyPct),
        improvement: 0,
      }
    : mockPracticeResults;
  const skillBreakdown = result
    ? result.skillBreakdown.map((item) => ({
        skill: item.skill,
        correct: item.correct,
        total: item.total,
        percentage: Math.round(item.accuracyPct),
      }))
    : mockSkillBreakdown;
  const weaknesses = result
    ? result.weakAreas.map((item) => ({
        skill: item.label,
        description: item.suggestion,
      }))
    : mockWeaknesses;
  const reviewQuestions = result
    ? result.questions.map((item) => ({
        id: item.questionId,
        question: item.question,
        userAnswer: item.userAnswer || "Skipped",
        correctAnswer: item.correctAnswer || "",
        isCorrect: item.isCorrect,
        explanation: item.explanation || "",
        skill: item.skill,
        difficulty: "",
        part: item.partLabel || `Part ${item.part}`,
      }))
    : mockReviewQuestions;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground lg:text-3xl">
            Kết quả luyện tập
          </h1>
          <p className="mt-1 text-muted-foreground">
            Reading Part 5 - Hoàn thành lúc 14:30 hôm nay
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" asChild>
            <Link to={retryUrl ?? "/practice/runner"}>
              <RotateCcw className="mr-2 h-4 w-4" />
              Làm lại
            </Link>
          </Button>
          <Button asChild>
            <Link to="/practice">
              Tiếp tục học
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </div>

      {(isLoadingResult || resultLoadError) && (
        <Card className="rounded-xl border-border">
          <CardContent className="p-4 text-sm text-muted-foreground">
            {isLoadingResult
              ? "Loading saved result from FastAPI..."
              : `Could not load saved result: ${resultLoadError}`}
          </CardContent>
        </Card>
      )}

      {isReviewFocusResult && (
        <Card className="rounded-xl border-primary/20 bg-primary/5">
          <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
            <Badge className="w-fit border-0 bg-primary/10 text-primary">
              Review-focused practice
            </Badge>
            <div>
              <p className="font-medium text-foreground">
                Based on a recent mistake
              </p>
              <p className="text-sm text-muted-foreground">
                Similar questions were selected from the same part and focus area.
                {reviewFocusPart ? ` Part ${reviewFocusPart}` : ""}
                {reviewFocusSkill ? ` / ${reviewFocusSkill}` : ""}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      <Card className="rounded-xl border-border bg-gradient-to-r from-primary/5 to-primary/10">
        <CardContent className="p-6 lg:p-8">
          <div className="grid gap-6 md:grid-cols-4">
            <div className="text-center">
              <div className="mb-1 text-5xl font-bold text-primary">
                {practiceResults.accuracy}%
              </div>
              <p className="text-sm text-muted-foreground">Độ chính xác</p>
              <Badge className="mt-2 bg-primary/10 text-primary">
                <TrendingUp className="mr-1 h-3 w-3" />+
                {practiceResults.improvement}% so với lần trước
              </Badge>
            </div>
            <div className="flex items-center justify-center gap-6">
              <div className="text-center">
                <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-green-500/10">
                  <CheckCircle2 className="h-6 w-6 text-green-500" />
                </div>
                <div className="text-xl font-bold text-foreground">
                  {practiceResults.correct}
                </div>
                <p className="text-xs text-muted-foreground">Đúng</p>
              </div>
              <div className="text-center">
                <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-red-500/10">
                  <XCircle className="h-6 w-6 text-red-500" />
                </div>
                <div className="text-xl font-bold text-foreground">
                  {practiceResults.incorrect}
                </div>
                <p className="text-xs text-muted-foreground">Sai</p>
              </div>
              <div className="text-center">
                <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-gray-500/10">
                  <MinusCircle className="h-6 w-6 text-gray-500" />
                </div>
                <div className="text-xl font-bold text-foreground">
                  {practiceResults.skipped}
                </div>
                <p className="text-xs text-muted-foreground">Bỏ qua</p>
              </div>
            </div>
            <div className="text-center">
              <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/10">
                <Clock className="h-6 w-6 text-blue-500" />
              </div>
              <div className="text-xl font-bold text-foreground">
                {practiceResults.timeSpent}
              </div>
              <p className="text-xs text-muted-foreground">Thời gian</p>
            </div>
            <div className="text-center">
              <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-purple-500/10">
                <Target className="h-6 w-6 text-purple-500" />
              </div>
              <div className="text-xl font-bold text-foreground">
                {practiceResults.totalQuestions}
              </div>
              <p className="text-xs text-muted-foreground">Tổng câu</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card className="rounded-xl border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg text-foreground">
                <Target className="h-5 w-5 text-primary" />
                Phân tích theo kỹ năng
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {skillBreakdown.map((skill, index) => (
                <div key={index} className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-foreground">
                      {skill.skill}
                    </span>
                    <span className="text-muted-foreground">
                      {skill.correct}/{skill.total} ({skill.percentage}%)
                    </span>
                  </div>
                  <Progress
                    value={skill.percentage}
                    className={`h-2 ${
                      skill.percentage >= 80
                        ? "[&>div]:bg-green-500"
                        : skill.percentage >= 60
                          ? "[&>div]:bg-yellow-500"
                          : "[&>div]:bg-red-500"
                    }`}
                  />
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="rounded-xl border-border">
            <CardHeader>
              <CardTitle className="text-lg text-foreground">
                Xem lại câu hỏi
              </CardTitle>
              <CardDescription className="text-muted-foreground">
                Click vào câu hỏi để xem giải thích chi tiết
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="all">
                <TabsList className="mb-4">
                  <TabsTrigger value="all">Tất cả</TabsTrigger>
                  <TabsTrigger value="incorrect">
                    Sai ({practiceResults.incorrect})
                  </TabsTrigger>
                  <TabsTrigger value="correct">
                    Đúng ({practiceResults.correct})
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="all" className="space-y-3">
                  {reviewQuestions.map((q) => (
                    <div
                      key={q.id}
                      className={`cursor-pointer rounded-xl border p-4 transition-all ${
                        selectedQuestion === q.id
                          ? "border-primary bg-accent"
                          : "border-border hover:border-primary/50"
                      }`}
                      onClick={() =>
                        setSelectedQuestion(
                          selectedQuestion === q.id ? null : q.id,
                        )
                      }
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className={`h-8 w-8 shrink-0 rounded-lg flex items-center justify-center ${
                            q.isCorrect ? "bg-green-500/10" : "bg-red-500/10"
                          }`}
                        >
                          {q.isCorrect ? (
                            <CheckCircle2 className="h-4 w-4 text-green-500" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-500" />
                          )}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="mb-1 flex items-center gap-2">
                            <Badge variant="outline" className="text-xs">
                              {q.part}
                            </Badge>
                            <Badge variant="secondary" className="text-xs">
                              {q.skill}
                            </Badge>
                          </div>
                          <p className="line-clamp-2 text-sm font-medium text-foreground">
                            {q.question}
                          </p>
                          <div className="mt-2 flex items-center gap-4 text-xs text-muted-foreground">
                            <span>
                              Bạn chọn:{" "}
                              <span
                                className={
                                  q.isCorrect ? "text-green-500" : "text-red-500"
                                }
                              >
                                {q.userAnswer}
                              </span>
                            </span>
                            {!q.isCorrect && (
                              <span>
                                Đáp án:{" "}
                                <span className="text-green-500">
                                  {q.correctAnswer}
                                </span>
                              </span>
                            )}
                          </div>
                        </div>
                        <ChevronRight
                          className={`h-5 w-5 text-muted-foreground transition-transform ${
                            selectedQuestion === q.id ? "rotate-90" : ""
                          }`}
                        />
                      </div>

                      {selectedQuestion === q.id && (
                        <div className="mt-4 border-t border-border pt-4">
                          <div className="flex items-start gap-2 rounded-lg bg-primary/5 p-3">
                            <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                            <p className="text-sm text-foreground">
                              {q.explanation}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </TabsContent>

                <TabsContent value="incorrect" className="space-y-3">
                  {reviewQuestions
                    .filter((q) => !q.isCorrect)
                    .map((q) => (
                      <div
                        key={q.id}
                        className={`cursor-pointer rounded-xl border p-4 transition-all ${
                          selectedQuestion === q.id
                            ? "border-primary bg-accent"
                            : "border-border hover:border-primary/50"
                        }`}
                        onClick={() =>
                          setSelectedQuestion(
                            selectedQuestion === q.id ? null : q.id,
                          )
                        }
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-red-500/10">
                            <XCircle className="h-4 w-4 text-red-500" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="mb-1 flex items-center gap-2">
                              <Badge variant="outline" className="text-xs">
                                {q.part}
                              </Badge>
                              <Badge variant="secondary" className="text-xs">
                                {q.skill}
                              </Badge>
                            </div>
                            <p className="line-clamp-2 text-sm font-medium text-foreground">
                              {q.question}
                            </p>
                            <div className="mt-2 flex items-center gap-4 text-xs text-muted-foreground">
                              <span>
                                Bạn chọn:{" "}
                                <span className="text-red-500">
                                  {q.userAnswer}
                                </span>
                              </span>
                              <span>
                                Đáp án:{" "}
                                <span className="text-green-500">
                                  {q.correctAnswer}
                                </span>
                              </span>
                            </div>
                          </div>
                          <ChevronRight
                            className={`h-5 w-5 text-muted-foreground transition-transform ${
                              selectedQuestion === q.id ? "rotate-90" : ""
                            }`}
                          />
                        </div>

                        {selectedQuestion === q.id && (
                          <div className="mt-4 border-t border-border pt-4">
                            <div className="flex items-start gap-2 rounded-lg bg-primary/5 p-3">
                              <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                              <p className="text-sm text-foreground">
                                {q.explanation}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                </TabsContent>

                <TabsContent value="correct" className="space-y-3">
                  {reviewQuestions
                    .filter((q) => q.isCorrect)
                    .map((q) => (
                      <div
                        key={q.id}
                        className={`cursor-pointer rounded-xl border p-4 transition-all ${
                          selectedQuestion === q.id
                            ? "border-primary bg-accent"
                            : "border-border hover:border-primary/50"
                        }`}
                        onClick={() =>
                          setSelectedQuestion(
                            selectedQuestion === q.id ? null : q.id,
                          )
                        }
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-green-500/10">
                            <CheckCircle2 className="h-4 w-4 text-green-500" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="mb-1 flex items-center gap-2">
                              <Badge variant="outline" className="text-xs">
                                {q.part}
                              </Badge>
                              <Badge variant="secondary" className="text-xs">
                                {q.skill}
                              </Badge>
                            </div>
                            <p className="line-clamp-2 text-sm font-medium text-foreground">
                              {q.question}
                            </p>
                          </div>
                          <ChevronRight
                            className={`h-5 w-5 text-muted-foreground transition-transform ${
                              selectedQuestion === q.id ? "rotate-90" : ""
                            }`}
                          />
                        </div>

                        {selectedQuestion === q.id && (
                          <div className="mt-4 border-t border-border pt-4">
                            <div className="flex items-start gap-2 rounded-lg bg-primary/5 p-3">
                              <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                              <p className="text-sm text-foreground">
                                {q.explanation}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="rounded-xl border-border">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-lg text-foreground">
                <AlertTriangle className="h-5 w-5 text-orange-500" />
                Điểm cần cải thiện
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {weaknesses.map((w, index) => (
                <div
                  key={index}
                  className="rounded-lg border border-orange-500/20 bg-orange-500/5 p-3"
                >
                  <p className="text-sm font-medium text-foreground">
                    {w.skill}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {w.description}
                  </p>
                </div>
              ))}
            </CardContent>
          </Card>

          <ProFeatureGuard
            feature="aiChatUnlimited"
            compact
            title="AI Tutor trong Practice Summary la tinh nang Pro"
            description="Free van xem ket qua va loi sai. Nang cap Pro de hoi AI Tutor sau bai lam."
          >
          <Card className="rounded-xl border-primary bg-primary/5">
            <CardContent className="h-[320px] p-4">
              <ChatPanel
                title="Hỏi AI Tutor"
                description="Hỏi theo dữ liệu bài luyện."
                messages={aiMessages}
                value={aiMessage}
                onValueChange={setAiMessage}
                onSend={() => void sendAiMessage()}
                loading={aiLoading}
                placeholder="Nhập câu hỏi..."
                className="h-full"
              />
            </CardContent>
          </Card>
          </ProFeatureGuard>

          <Card className="rounded-xl border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg text-foreground">
                Gợi ý tiếp theo
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Link
                to="/practice?skill=prepositions"
                className="flex items-center gap-3 rounded-lg border border-border p-3 transition-colors hover:border-primary/50 hover:bg-accent/50"
              >
                <BookOpen className="h-5 w-5 text-primary" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-foreground">
                    Luyện Prepositions
                  </p>
                  <p className="text-xs text-muted-foreground">20 câu hỏi</p>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
              </Link>
              <Link
                to="/practice?part=2"
                className="flex items-center gap-3 rounded-lg border border-border p-3 transition-colors hover:border-primary/50 hover:bg-accent/50"
              >
                <Headphones className="h-5 w-5 text-primary" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-foreground">
                    Listening Part 2
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Question-Response
                  </p>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
