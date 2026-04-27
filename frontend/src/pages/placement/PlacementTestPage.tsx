"use client";

import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AudioPlayerBar } from "@/components/audio-player-bar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  diagnosticService,
  type DiagnosticQuestion,
  type DiagnosticSubmitResponse,
} from "@src/services/diagnosticService";
import { API_BASE_URL } from "@src/services/apiClient";
import {
  ArrowLeft,
  ArrowRight,
  BarChart3,
  BookOpen,
  CheckCircle2,
  Headphones,
  ImageIcon,
  ListChecks,
  Loader2,
  Volume2,
} from "lucide-react";

function resolveAssetUrl(path?: string | null) {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

function prettifyRoadmapText(value?: string | null) {
  if (!value) return "";
  return String(value).replace(/_/g, " ").replace(/\s+/g, " ").trim();
}

export function PlacementTestPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [questions, setQuestions] = useState<DiagnosticQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<DiagnosticSubmitResponse | null>(null);
  const [targetScore, setTargetScore] = useState(750);
  const [weeks, setWeeks] = useState(8);
  const [minutesPerDay, setMinutesPerDay] = useState(30);

  useEffect(() => {
    let active = true;

    const loadQuestions = async () => {
      try {
        setLoading(true);
        setError("");
        const payload = await diagnosticService.getQuestions();
        if (!active) return;
        setQuestions(payload.questions || []);
      } catch (requestError) {
        if (!active) return;
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Không tải được bộ câu hỏi placement test.",
        );
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void loadQuestions();

    return () => {
      active = false;
    };
  }, []);

  const currentQuestion = questions[currentIndex];
  const progress =
    questions.length > 0 ? ((currentIndex + 1) / questions.length) * 100 : 0;
  const answeredCount = Object.keys(answers).length;
  const allAnswered = questions.length > 0 && answeredCount === questions.length;

  const answerEntries = useMemo(() => {
    const mapped: Record<string, number> = {};
    Object.entries(answers).forEach(([index, value]) => {
      mapped[index] = Number(value);
    });
    return mapped;
  }, [answers]);

  const handleAnswerSelect = (optionIndex: number) => {
    setAnswers((prev) => ({
      ...prev,
      [currentIndex]: optionIndex,
    }));

    if (currentIndex < questions.length - 1) {
      window.setTimeout(() => {
        setCurrentIndex((prev) => Math.min(questions.length - 1, prev + 1));
      }, 120);
    }
  };

  const handleSubmit = async () => {
    if (!allAnswered) {
      setError(`Bạn cần làm hết ${questions.length} câu trước khi nộp bài.`);
      return;
    }

    try {
      setSubmitting(true);
      setError("");
      const response = await diagnosticService.submitDiagnostic({
        answers: answerEntries,
        target_score: targetScore,
        weeks,
        minutes_per_day: minutesPerDay,
      });
      setResult(response);
      try {
        await diagnosticService.saveAttempt({
          targetScore,
          weeks,
          minutesPerDay,
          score: response.analysis.score,
          accuracyPct: response.analysis.accuracyPct,
          correctCount: response.analysis.correctCount,
          totalQuestions: response.analysis.total,
          levelName: response.analysis.level.name,
          levelRange: response.analysis.level.range,
          weakSubskillsJson: JSON.stringify(response.analysis.weakSubskills || []),
          topErrorsJson: JSON.stringify(response.analysis.topErrors || []),
          answers: questions.map((question, index) => {
            const selectedAnswerIndex = answers[index] ?? null;
            const correctAnswerIndex =
              typeof question.correct === "number" ? question.correct : null;

            return {
              questionId: question.id,
              questionNumber: index + 1,
              skill: question.skill ?? null,
              subskill: question.subskill ?? null,
              selectedAnswerIndex,
              correctAnswerIndex,
              isCorrect:
                correctAnswerIndex !== null &&
                selectedAnswerIndex === correctAnswerIndex,
            };
          }),
        });
      } catch (saveError) {
        setError(
          saveError instanceof Error
            ? `Da tinh ket qua nhung chua luu duoc diagnostic: ${saveError.message}`
            : "Da tinh ket qua nhung chua luu duoc diagnostic.",
        );
      }
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Không nộp được bài diagnostic.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="grid min-h-[60vh] place-items-center gap-3 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
        Đang tải placement test...
      </div>
    );
  }

  if (result) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <Badge className="mb-3">Kết quả placement test</Badge>
            <h1 className="text-3xl font-bold">Placement test hoàn tất</h1>
            <p className="mt-2 text-muted-foreground">
              Đây là tóm tắt kết quả mới nhất để bạn bắt đầu lộ trình học phù hợp.
            </p>
          </div>

          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => {
                setResult(null);
                setAnswers({});
                setCurrentIndex(0);
              }}
            >
              Làm lại bài test
            </Button>
            <Button onClick={() => navigate("/dashboard")}>Về dashboard</Button>
          </div>
        </div>

        {error ? (
          <div className="rounded-2xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            {error}
          </div>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Card className="rounded-3xl">
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Điểm ước lượng</p>
              <p className="text-3xl font-bold">{result.analysis.score}</p>
            </CardContent>
          </Card>

          <Card className="rounded-3xl">
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Level</p>
              <p className="text-xl font-bold">{result.analysis.level.name}</p>
              <p className="text-xs text-muted-foreground">
                {result.analysis.level.range}
              </p>
            </CardContent>
          </Card>

          <Card className="rounded-3xl">
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Accuracy</p>
              <p className="text-3xl font-bold">
                {result.analysis.accuracyPct}%
              </p>
            </CardContent>
          </Card>

          <Card className="rounded-3xl">
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Câu đúng</p>
              <p className="text-3xl font-bold">
                {result.analysis.correctCount}/{result.analysis.total}
              </p>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
          <Card className="rounded-3xl">
            <CardHeader>
              <CardTitle>Kỹ năng yếu</CardTitle>
              <CardDescription>
                Những nội dung bạn cần ưu tiên ôn tập.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {result.analysis.weakSubskills.length > 0 ? (
                result.analysis.weakSubskills.map((item) => (
                  <div key={item} className="rounded-2xl border p-3 text-sm">
                    {prettifyRoadmapText(item)}
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">
                  Chưa xác định kỹ năng yếu nổi bật.
                </p>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-3xl">
            <CardHeader>
              <CardTitle>Lỗi sai thường gặp</CardTitle>
              <CardDescription>
                Các nhóm lỗi được phát hiện nhiều nhất.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {result.analysis.topErrors.length > 0 ? (
                result.analysis.topErrors.map((item) => (
                  <div
                    key={item.type}
                    className="flex items-center justify-between rounded-2xl border p-3 text-sm"
                  >
                    <span>{prettifyRoadmapText(item.type)}</span>
                    <Badge variant="outline">{item.count}</Badge>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">
                  Không có đủ dữ liệu lỗi sai.
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        <Card className="rounded-3xl">
          <CardHeader>
            <CardTitle>Roadmap gợi ý</CardTitle>
            <CardDescription>
              Lộ trình học tập được gợi ý dựa trên kết quả vừa hoàn thành.
            </CardDescription>
          </CardHeader>

          <CardContent className="grid gap-5 lg:grid-cols-2">
            {result.roadmap.map((week) => {
              const focusItems = String(week.focus || "")
                .split(",")
                .map((item) => prettifyRoadmapText(item))
                .filter(Boolean);

              return (
                <div
                  key={week.week}
                  className="rounded-3xl border border-border bg-background p-5 shadow-sm"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-2">
                      <div className="inline-flex items-center rounded-full bg-primary/10 px-3 py-1 text-sm font-semibold text-primary">
                        Tuần {week.week}
                      </div>
                      <h3 className="text-base font-semibold leading-6 text-foreground">
                        {prettifyRoadmapText(week.title) || "Kế hoạch học tập"}
                      </h3>
                    </div>

                    <div className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
                      {focusItems.length} trọng tâm
                    </div>
                  </div>

                  {focusItems.length > 0 ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {focusItems.map((item, index) => (
                        <span
                          key={`${week.week}-${item}-${index}`}
                          className="rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary"
                        >
                          {item}
                        </span>
                      ))}
                    </div>
                  ) : null}

                  <div className="mt-5 rounded-2xl bg-muted/30 p-4">
                    <p className="mb-3 text-sm font-semibold text-foreground">
                      Nhiệm vụ tuần này
                    </p>

                    <ul className="space-y-3 text-sm text-muted-foreground">
                      {week.tasks.map((task, index) => (
                        <li
                          key={`${week.week}-task-${index}`}
                          className="flex items-start gap-3 rounded-xl bg-background px-3 py-3"
                        >
                          <span className="mt-1 inline-block h-2.5 w-2.5 shrink-0 rounded-full bg-primary" />
                          <span className="leading-6">
                            {prettifyRoadmapText(task)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!currentQuestion) {
    return (
      <Card className="rounded-3xl">
        <CardContent className="pt-6 text-sm text-muted-foreground">
          Chưa có câu hỏi phù hợp để hiển thị.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <Badge className="mb-3">Placement Test</Badge>
          <h1 className="text-3xl font-bold">TOEIC Placement Test</h1>
          <p className="mt-2 text-muted-foreground">
            Hoàn thành bài đánh giá để cập nhật mức điểm, kỹ năng cần ưu tiên và
            lộ trình học tập.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <p className="mb-2 text-sm text-muted-foreground">Điểm mục tiêu</p>
            <Input
              type="number"
              value={targetScore}
              onChange={(event) => setTargetScore(Number(event.target.value || 0))}
            />
          </div>
          <div>
            <p className="mb-2 text-sm text-muted-foreground">Số tuần</p>
            <Input
              type="number"
              value={weeks}
              onChange={(event) => setWeeks(Number(event.target.value || 0))}
            />
          </div>
          <div>
            <p className="mb-2 text-sm text-muted-foreground">Phút/ngày</p>
            <Input
              type="number"
              value={minutesPerDay}
              onChange={(event) =>
                setMinutesPerDay(Number(event.target.value || 0))
              }
            />
          </div>
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <Card className="rounded-3xl">
            <CardHeader>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <CardTitle>
                    Câu {currentIndex + 1} / {questions.length}
                  </CardTitle>
                  <CardDescription>
                    {currentQuestion.skill || "general"} ·{" "}
                    {currentQuestion.subskill || "practice"}
                  </CardDescription>
                </div>
                <Badge variant="outline">
                  Đã trả lời {answeredCount}/{questions.length}
                </Badge>
              </div>
              <Progress value={progress} className="h-2" />
            </CardHeader>

            <CardContent className="space-y-6">
              {currentQuestion.audio?.path ? (
                <div className="rounded-2xl border p-4">
                  <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                    <Volume2 className="h-4 w-4" />
                    Audio
                  </div>
                  <AudioPlayerBar
                    src={resolveAssetUrl(currentQuestion.audio.path) || undefined}
                    className="border-[#ececec] bg-[#f4f4f4]"
                  />
                </div>
              ) : null}

              {currentQuestion.image?.path ? (
                <div className="rounded-2xl border p-4">
                  <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                    <ImageIcon className="h-4 w-4" />
                    Hình minh hoạ
                  </div>
                  <img
                    src={resolveAssetUrl(currentQuestion.image.path) || ""}
                    alt="diagnostic"
                    className="max-h-72 w-full rounded-xl object-contain"
                  />
                </div>
              ) : null}

              <div>
                <p className="text-lg font-semibold leading-8">
                  {currentQuestion.question}
                </p>
              </div>

              <div className="grid gap-3">
                {currentQuestion.options.map((option, optionIndex) => {
                  const isSelected = answers[currentIndex] === optionIndex;

                  return (
                    <button
                      key={`${currentQuestion.id}-${optionIndex}`}
                      type="button"
                      className={`rounded-2xl border px-4 py-4 text-left transition ${
                        isSelected
                          ? "border-primary bg-primary/10"
                          : "hover:border-primary/40"
                      }`}
                      onClick={() => handleAnswerSelect(optionIndex)}
                    >
                      <span className="font-medium">
                        {String.fromCharCode(65 + optionIndex)}.
                      </span>{" "}
                      {option}
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex gap-3">
              <Button
                variant="outline"
                disabled={currentIndex === 0}
                onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Câu trước
              </Button>

              <Button
                variant="outline"
                disabled={currentIndex === questions.length - 1}
                onClick={() =>
                  setCurrentIndex((prev) => Math.min(questions.length - 1, prev + 1))
                }
              >
                Câu sau
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>

            <Button onClick={() => void handleSubmit()} disabled={submitting || !allAnswered}>
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Đang chấm bài...
                </>
              ) : (
                "Nộp bài"
              )}
            </Button>
          </div>
        </div>

        <Card className="h-fit rounded-3xl xl:sticky xl:top-6">
          <CardHeader>
            <div className="flex items-center gap-2">
              <ListChecks className="h-5 w-5" />
              <CardTitle>Danh sách câu hỏi</CardTitle>
            </div>
            <CardDescription>
              Chọn nhanh để chuyển tới câu muốn làm
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-5">
            <div className="grid grid-cols-5 gap-3">
              {questions.map((question, index) => {
                const isCurrent = index === currentIndex;
                const isAnswered = answers[index] !== undefined;

                return (
                  <button
                    key={question.id}
                    type="button"
                    onClick={() => setCurrentIndex(index)}
                    className={`flex h-11 w-11 items-center justify-center rounded-full border text-sm font-semibold transition ${
                      isCurrent
                        ? "border-primary bg-primary text-primary-foreground"
                        : isAnswered
                          ? "border-primary/40 bg-primary/10 text-primary"
                          : "border-border bg-background hover:border-primary/40"
                    }`}
                  >
                    {index + 1}
                  </button>
                );
              })}
            </div>

            <div className="space-y-2 rounded-2xl border p-4 text-sm">
              <div className="flex items-center justify-between">
                <span>Đã trả lời</span>
                <span className="font-semibold">
                  {answeredCount}/{questions.length}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Còn lại</span>
                <span className="font-semibold">
                  {questions.length - answeredCount}
                </span>
              </div>
              <div className="flex items-center gap-2 pt-2 text-muted-foreground">
                <Headphones className="h-4 w-4" />
                <span>Listening & Reading mix</span>
              </div>
              <div className="flex items-center gap-2 text-muted-foreground">
                <BookOpen className="h-4 w-4" />
                <span>Kết quả dùng để gợi ý roadmap tiếp theo</span>
              </div>
              <div className="flex items-center gap-2 text-muted-foreground">
                <BarChart3 className="h-4 w-4" />
                <span>Kết quả được lưu để cập nhật dashboard</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
