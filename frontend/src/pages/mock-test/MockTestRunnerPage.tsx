"use client";

import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock,
  FileText,
  Flag,
  Volume2,
} from "lucide-react";

import { AudioPlayerBar } from "@/components/audio-player-bar";
import { ProFeatureGuard } from "@/components/pro-feature-guard";
import { RightAnswerSheet } from "@src/components/runner/RightAnswerSheet";
import { RunnerActionButtons } from "@src/components/runner/RunnerActionButtons";
import { RunnerNotebookPanel } from "@src/components/runner/RunnerNotebookPanel";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { mockQuestions } from "@src/data/mock-test-runner";
import { useHighlightSelection } from "@src/hooks/useHighlightSelection";
import { attemptsService } from "@src/services/attemptsService";
import { ApiError } from "@src/services/apiClient";
import { reviewService, type ReviewHighlight, type ReviewNote, type ReviewSourceFilter } from "@src/services/reviewService";
import { toeicService, ToeicRunnerQuestion } from "@src/services/toeicService";
import { useLanguage } from "@src/contexts/LanguageContext";
import {
  weeklyCheckService,
  type WeeklyCheckCurrent,
} from "@src/services/weeklyCheckService";

type MockRunnerQuestion = (typeof mockQuestions)[number] & {
  sourceQuestionId?: number;
  section?: string;
  partLabel?: string;
  test?: number;
  questionNumber?: number;
  correctAnswerIndex?: number | null;
  explanation?: string;
  passageTitle?: string | null;
  passageText?: string | null;
  passage?: ToeicRunnerQuestion["passage"];
  groupId?: string | null;
  hasAudio?: boolean;
  hasImage?: boolean;
  audioPath?: string;
  graphicPath?: string;
  imagePath?: string;
  audioUrl?: string;
  graphicUrl?: string;
  imageUrl?: string;
};

function mapToeicQuestionToMockRunnerQuestion(
  question: ToeicRunnerQuestion,
  index: number,
): MockRunnerQuestion {
  return {
    id: index + 1,
    part: question.partNumber,
    type: question.type,
    question: question.question,
    options: question.options.map((text, optionIndex) => ({
      id: String.fromCharCode(65 + optionIndex),
      text,
    })),
    correctAnswer:
      question.correct >= 0 ? String.fromCharCode(65 + question.correct) : "",
    difficulty: "mixed",
    skill: question.skill,
    subskill: question.subskill || "",
    sourceQuestionId:
      question.docxQuestionId ||
      question.sourceQuestionId ||
      question.sqlId ||
      question.dbId ||
      question.questionId ||
      question.id,
    section: question.section,
    partLabel: question.part,
    test: question.test,
    questionNumber: question.questionNumber,
    correctAnswerIndex: question.correct,
    explanation: question.explanation,
    passageTitle: question.passageTitle,
    passageText: question.passageText,
    passage: question.passage,
    groupId: question.groupId,
    hasAudio: question.hasAudio,
    hasImage: question.hasImage,
    audioPath: question.audioPath,
    graphicPath: question.graphicPath,
    imagePath: question.imagePath,
    audioUrl: question.audioUrl,
    graphicUrl: question.graphicUrl,
    imageUrl: question.imageUrl,
  };
}

function parseParts(value: string | null) {
  return (value || "")
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((part) => Number.isInteger(part) && part >= 1 && part <= 7);
}

function parsePositiveNumber(value: string | null, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function getStableQuestionId(question?: MockRunnerQuestion | null) {
  const candidate =
    question?.sourceQuestionId ||
    (question as { questionId?: number | null } | null)?.questionId ||
    (question as { QuestionId?: number | null } | null)?.QuestionId ||
    null;
  const parsed = Number(candidate);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function formatFullTestAvailabilityError(error: unknown) {
  if (!(error instanceof ApiError) || error.status !== 409) {
    return error instanceof Error ? error.message : "Could not load mock-test questions from FastAPI.";
  }

  const payload = error.payload as { missing?: Record<string, number> } | null;
  const missingEntries = Object.entries(payload?.missing || {})
    .map(([part, count]) => [part, Number(count)] as const)
    .filter(([, count]) => count > 0);

  if (missingEntries.length === 0) {
    return "Dữ liệu chưa đủ để tạo Full Test 200 câu.";
  }

  return `Dữ liệu chưa đủ để tạo Full Test 200 câu. Thiếu ${missingEntries
    .map(([part, count]) => `Part ${part}: còn thiếu ${count} câu`)
    .join("; ")}.`;
}

export function MockTestRunnerPage() {
  const { t } = useLanguage();
  const highlightSelection = useHighlightSelection();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const runnerType = location.pathname.startsWith("/weekly-check/runner")
    ? "weekly"
    : searchParams.get("type") || searchParams.get("mode") || "full";
  const reviewToolSource: ReviewSourceFilter =
    runnerType === "weekly" ? "weeklycheck" : runnerType === "mini" ? "minitest" : "fulltest";
  const [currentQuestion, setCurrentQuestion] = useState(1);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [flagged, setFlagged] = useState<number[]>([]);
  const [timeLeft, setTimeLeft] = useState(120 * 60);
  const [showSubmitDialog, setShowSubmitDialog] = useState(false);
  const [questions, setQuestions] = useState<MockRunnerQuestion[]>([]);
  const [questionSource, setQuestionSource] = useState<"fastapi" | "local">("local");
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(true);
  const [questionError, setQuestionError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [startedAtUtc, setStartedAtUtc] = useState(() => new Date().toISOString());
  const [weeklyCheck, setWeeklyCheck] = useState<WeeklyCheckCurrent | null>(null);
  const [savedNotes, setSavedNotes] = useState<ReviewNote[]>([]);
  const [savedHighlights, setSavedHighlights] = useState<ReviewHighlight[]>([]);
  const [questionNote, setQuestionNote] = useState("");
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [noteFocusKey, setNoteFocusKey] = useState(0);
  const [noteSaved, setNoteSaved] = useState(false);
  const [isSavingNote, setIsSavingNote] = useState(false);
  const [isSavingHighlight, setIsSavingHighlight] = useState(false);
  const [reviewToolError, setReviewToolError] = useState<string | null>(null);
  const [notebookStatusByNumber, setNotebookStatusByNumber] = useState<
    Record<number, { bookmarked?: boolean; hasNote?: boolean; hasHighlight?: boolean }>
  >({});

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => Math.max(0, prev - 1));
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadQuestions() {
      setIsLoadingQuestions(true);
      setQuestionError(null);

      try {
        const test = parsePositiveNumber(searchParams.get("test"), 1);
        const count = parsePositiveNumber(searchParams.get("count"), 20);
        const parts = parseParts(searchParams.get("parts"));
        const weeklyResult =
          runnerType === "weekly" ? await weeklyCheckService.getCurrent() : null;
        const result = weeklyResult
          ? weeklyResult.questions
          : runnerType === "mini"
            ? await toeicService.getMiniTestRunner(test, parts.length > 0 ? parts : null, count)
            : runnerType === "full"
              ? await toeicService.getFullTestRunner(test)
              : [];

        if (cancelled) return;

        if (result.length > 0) {
          setQuestions(result.map(mapToeicQuestionToMockRunnerQuestion));
          setQuestionSource("fastapi");
          setWeeklyCheck(weeklyResult);
          setCurrentQuestion(1);
          setAnswers({});
          setFlagged([]);
          setStartedAtUtc(new Date().toISOString());
          setTimeLeft(
            weeklyResult
              ? Math.max(1, weeklyResult.estimatedMinutes || 45) * 60
              : runnerType === "full"
                ? 120 * 60
                : Math.max(10, result.length) * 90,
          );
        } else if (runnerType === "mini" || runnerType === "full" || runnerType === "weekly") {
          setQuestionError("Chưa có bài test phù hợp với lựa chọn này.");
          setQuestions([]);
          setQuestionSource("fastapi");
          setWeeklyCheck(null);
        }
      } catch (error) {
        if (!cancelled) {
          setQuestionError(
            runnerType === "full"
              ? formatFullTestAvailabilityError(error)
              : error instanceof Error
                ? error.message
                : "Could not load mock-test questions from FastAPI.",
          );
          setQuestions([]);
          setQuestionSource("local");
          setWeeklyCheck(null);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingQuestions(false);
        }
      }
    }

    loadQuestions();

    return () => {
      cancelled = true;
    };
  }, [runnerType, searchParams]);

  const formatTime = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hrs.toString().padStart(2, "0")}:${mins
      .toString()
      .padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const handleAnswer = (questionId: number, answer: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: answer }));
  };

  const toggleFlag = (questionId: number) => {
    setFlagged((prev) =>
      prev.includes(questionId)
        ? prev.filter((id) => id !== questionId)
        : [...prev, questionId],
    );
  };

  const goToQuestion = (questionId: number) => {
    setCurrentQuestion(questionId);
  };

  const getQuestionStatus = (questionId: number) => {
    if (questionId === currentQuestion) return "current";
    if (flagged.includes(questionId)) return "flagged";
    if (answers[questionId]) return "answered";
    return "unanswered";
  };

  const totalQuestions = questions.length;
  const answeredCount = Object.keys(answers).length;
  const progress = totalQuestions > 0 ? (answeredCount / totalQuestions) * 100 : 0;
  const currentQ = questions[currentQuestion - 1] ?? questions[0] ?? mockQuestions[0];
  const currentSqlQuestionId = getStableQuestionId(currentQ);
  const currentNotebookStatus = notebookStatusByNumber[currentQuestion] || {};
  const selectedTextForHighlight = highlightSelection.selection?.selectedText || "";
  const highlightTerms = useMemo(
    () =>
      Array.from(
        new Set(
          savedHighlights
            .map((highlight) => highlight.selectedText.trim())
            .filter(Boolean),
        ),
      ),
    [savedHighlights],
  );

  const renderHighlightedText = (text?: string | null) => {
    const value = text || "";
    if (!value || highlightTerms.length === 0) return value;
    const escaped = highlightTerms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    const regex = new RegExp(`(${escaped.join("|")})`, "gi");
    return value.split(regex).map((part, index) =>
      highlightTerms.some((term) => term.toLowerCase() === part.toLowerCase()) ? (
        <mark key={`${part}-${index}`} className="rounded bg-yellow-200 px-0.5 text-foreground">
          {part}
        </mark>
      ) : (
        part
      ),
    );
  };

  useEffect(() => {
    let cancelled = false;

    async function loadReviewTools() {
      if (!currentSqlQuestionId) {
        setSavedNotes([]);
        setSavedHighlights([]);
        setQuestionNote("");
        setNoteSaved(false);
        setIsBookmarked(false);
        return;
      }

      setReviewToolError(null);
      setNoteSaved(false);
      try {
        const [notes, highlights, bookmarked] = await Promise.all([
          reviewService.getNotes(currentSqlQuestionId, { source: reviewToolSource, runtimeQuestionId: currentSqlQuestionId }),
          reviewService.getHighlights(currentSqlQuestionId, { source: reviewToolSource, runtimeQuestionId: currentSqlQuestionId }),
          reviewService.getBookmark(currentSqlQuestionId, { source: reviewToolSource, runtimeQuestionId: currentSqlQuestionId }),
        ]);
        if (cancelled) return;
        setSavedNotes(notes);
        setSavedHighlights(highlights);
        setQuestionNote(notes[0]?.noteText || "");
        setNoteSaved(false);
        setIsBookmarked(bookmarked);
        setNotebookStatusByNumber((prev) => ({
          ...prev,
          [currentQuestion]: {
            bookmarked,
            hasNote: notes.length > 0,
            hasHighlight: highlights.length > 0,
          },
        }));
      } catch (error) {
        if (!cancelled) {
          setReviewToolError(error instanceof Error ? error.message : "Could not load review tools.");
        }
      }
    }

    void loadReviewTools();

    return () => {
      cancelled = true;
    };
  }, [currentQuestion, currentSqlQuestionId, reviewToolSource]);

  if (totalQuestions === 0) {
    return (
      <ProFeatureGuard
        feature="mockTestUnlimited"
        title={
          runnerType === "weekly"
            ? "Weekly Check la tinh nang Pro"
            : "Mock Test la tinh nang Pro"
        }
        description="Nang cap Pro de mo khoa de thi day du, mini test va bai kiem tra hang tuan."
      >
        <div className="grid min-h-[calc(100vh-4rem)] place-items-center bg-background p-6">
          <Card className="max-w-xl rounded-3xl border-border shadow-sm">
            <CardHeader>
              <CardTitle>
                {isLoadingQuestions ? "Đang tải bài test..." : "Chưa có bài test phù hợp"}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                {isLoadingQuestions
                  ? "Đang lấy câu hỏi từ FastAPI."
                  : questionError || "Chưa có bài test phù hợp với lựa chọn này."}
              </p>
              <Button asChild>
                <Link to="/mock-test">Quay lại Mock Test</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </ProFeatureGuard>
    );
  }

  const isListeningSection = currentQ.part <= 4;
  const currentAudioUrl = currentQ.audioUrl;
  const currentImageUrl = currentQ.imageUrl || currentQ.graphicUrl;
  const currentPassageTitle = currentQ.passage?.title || currentQ.passageTitle || "";
  const currentPassageText = currentQ.passage?.text || currentQ.passageText || "";
  const listeningQuestionNumbers = questions
    .map((question, index) => ({ question, number: index + 1 }))
    .filter((item) => item.question.part <= 4);
  const readingQuestionNumbers = questions
    .map((question, index) => ({ question, number: index + 1 }))
    .filter((item) => item.question.part >= 5);

  const calculateScore = () => {
    let correct = 0;

    Object.entries(answers).forEach(([questionId, answer]) => {
      if (questions[parseInt(questionId, 10) - 1]?.correctAnswer === answer) {
        correct++;
      }
    });

    return Math.round((correct / totalQuestions) * 100);
  };

  const getEstimatedScore = (percentage: number) => {
    if (percentage >= 90) return { score: "800-900", level: "Cao cấp" };
    if (percentage >= 70)
      return { score: "600-750", level: "Trung cấp cao" };
    if (percentage >= 50) return { score: "450-600", level: "Trung cấp" };
    if (percentage >= 30) return { score: "300-450", level: "Sơ cấp" };
    return { score: "< 300", level: "Mới bắt đầu" };
  };

  const scorePercentage = calculateScore();
  const estimated = getEstimatedScore(scorePercentage);
  const elapsedSeconds =
    runnerType === "full"
      ? 120 * 60 - timeLeft
      : runnerType === "weekly"
        ? Math.max(1, weeklyCheck?.estimatedMinutes || 45) * 60 - timeLeft
      : Math.max(10, totalQuestions) * 90 - timeLeft;

  const handleSubmit = async () => {
    if (isSubmitting) return;

    setSubmitError(null);

    if (questionSource !== "fastapi") {
      navigate("/mock-test/result", {
        state: {
          scorePercentage,
          estimatedScore: estimated.score,
          level: estimated.level,
        },
      });
      return;
    }

    try {
      setIsSubmitting(true);
      if (runnerType === "weekly" && weeklyCheck) {
        const result = await weeklyCheckService.submitWeeklyCheck({
          weeklyCheck,
          answers,
          flaggedQuestions: flagged,
          timeSpentSeconds: Math.max(0, elapsedSeconds),
          startedAtUtc,
        });

        navigate(`/weekly-check/result?attemptId=${result.attemptId}`, {
          state: {
            attempt: result,
          },
        });
        return;
      }

      const result = await attemptsService.submitMockTestAttempt({
        questions,
        answers,
        flaggedQuestions: flagged,
        timeSpentSeconds: Math.max(0, elapsedSeconds),
        source: runnerType === "mini" ? "minitest" : "fulltest",
        title: runnerType === "mini" ? "TOEIC Mini Test" : "TOEIC Full Mock Test",
        attemptType: runnerType === "mini" ? "mini-test" : "mock-test",
        startedAtUtc,
      });

      const resultPath =
        runnerType === "mini" ? "/mini-test/result" : "/full-test/result";

      navigate(`${resultPath}?attemptId=${result.attemptId}`, {
        state: {
          attempt: result,
          scorePercentage,
          estimatedScore: estimated.score,
          level: estimated.level,
        },
      });
    } catch (error) {
      const submitEndpoint =
        runnerType === "weekly" ? "/api/weekly-check/submit" : "/api/attempts/mock-test";
      console.error("Mock/weekly submit failed", {
        endpoint: submitEndpoint,
        status: error instanceof ApiError ? error.status : null,
        detail: error instanceof Error ? error.message : String(error),
        payload: error instanceof ApiError ? error.payload : null,
      });
      setSubmitError(
        error instanceof Error
          ? error.message
          : "Could not submit this mock test to FastAPI.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTextSelect = () => {
    highlightSelection.captureSelection();
  };

  const handleToggleBookmark = async () => {
    if (!currentSqlQuestionId) return;
    const nextValue = !isBookmarked;
    setIsBookmarked(nextValue);
    toggleFlag(currentQuestion);
    try {
      const saved = await reviewService.toggleBookmark(currentSqlQuestionId, null, {
        source: reviewToolSource,
        runtimeQuestionId: currentSqlQuestionId,
      });
      setIsBookmarked(saved);
      setNotebookStatusByNumber((prev) => ({
        ...prev,
        [currentQuestion]: {
          ...(prev[currentQuestion] || {}),
          bookmarked: saved,
        },
      }));
    } catch (error) {
      setIsBookmarked(!nextValue);
      setReviewToolError(error instanceof Error ? error.message : "Could not save bookmark.");
    }
  };

  const handleSaveNote = async () => {
    if (!currentSqlQuestionId || !questionNote.trim()) return;
    setIsSavingNote(true);
    setReviewToolError(null);
    try {
      const note = await reviewService.saveNote(currentSqlQuestionId, questionNote.trim(), null, {
        source: reviewToolSource,
        runtimeQuestionId: currentSqlQuestionId,
      });
      setSavedNotes([note]);
      setQuestionNote(note.noteText);
      setNoteSaved(true);
      setNotebookStatusByNumber((prev) => ({
        ...prev,
        [currentQuestion]: {
          ...(prev[currentQuestion] || {}),
          hasNote: true,
        },
      }));
    } catch (error) {
      setReviewToolError(error instanceof Error ? error.message : "Could not save note.");
    } finally {
      setIsSavingNote(false);
    }
  };

  const handleCreateHighlight = async () => {
    const currentSelection = highlightSelection.selection || highlightSelection.captureSelection();
    if (!currentSelection?.selectedText.trim()) {
      setReviewToolError(t("runner.selectTextToHighlight"));
      return;
    }
    if (!currentSqlQuestionId) {
      console.warn("[Highlight] Missing SQL question id for current test question.", currentQ);
      setReviewToolError("Cannot save highlight: missing question id.");
      return;
    }
    setIsSavingHighlight(true);
    setReviewToolError(null);
    try {
      const highlight = await reviewService.createHighlight({
        questionId: currentSqlQuestionId,
        source: reviewToolSource,
        runtimeQuestionId: currentSqlQuestionId,
        targetType: currentSelection.targetType || "question",
        targetKey: currentSelection.targetKey || null,
        selectedText: currentSelection.selectedText.trim(),
        startOffset: currentSelection.startOffset ?? null,
        endOffset: currentSelection.endOffset ?? null,
        color: "yellow",
      });
      setSavedHighlights((prev) => [highlight, ...prev]);
      setNotebookStatusByNumber((prev) => ({
        ...prev,
        [currentQuestion]: {
          ...(prev[currentQuestion] || {}),
          hasHighlight: true,
        },
      }));
      highlightSelection.clearSelection();
    } catch (error) {
      setReviewToolError(error instanceof Error ? error.message : "Could not save highlight.");
    } finally {
      setIsSavingHighlight(false);
    }
  };

  const answerSheetItems = questions.map((question, index) => {
    const number = index + 1;
    return {
      id: number,
      label: String(number),
      part: question.part,
      section: question.part <= 4 ? "Listening" : "Reading",
      current: number === currentQuestion,
      answered: Boolean(answers[number]),
      bookmarked: Boolean(notebookStatusByNumber[number]?.bookmarked || flagged.includes(number)),
      hasNote: Boolean(notebookStatusByNumber[number]?.hasNote),
      hasHighlight: Boolean(notebookStatusByNumber[number]?.hasHighlight),
    };
  });

  return (
    <ProFeatureGuard
      feature="mockTestUnlimited"
      title={
        runnerType === "weekly"
          ? "Weekly Check la tinh nang Pro"
          : "Mock Test la tinh nang Pro"
      }
      description="Nang cap Pro de mo khoa de thi day du, mini test va bai kiem tra hang tuan."
    >
    <div className="flex h-[calc(100vh-4rem)]">
      <div className="flex flex-1 flex-col overflow-hidden">
        <div className="flex items-center justify-between border-b bg-card px-6 py-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" className="gap-2" asChild>
              <Link to="/mock-test">
                <ArrowLeft className="h-4 w-4" />
                Thoát
              </Link>
            </Button>

            <div className="h-6 w-px bg-border" />

            <div className="flex items-center gap-2">
              <Badge variant="outline">
                {runnerType === "weekly"
                  ? "Weekly Check"
                  : runnerType === "mini"
                    ? "Mini Test"
                    : "Full Test"}
              </Badge>
              <Badge variant="secondary">Exam Mode</Badge>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <Progress value={progress} className="h-2 w-32" />
              <span className="text-sm text-muted-foreground">
                {answeredCount}/{totalQuestions}
              </span>
            </div>

            <div
              className={`flex items-center gap-2 rounded-lg px-4 py-2 ${
                timeLeft < 300 ? "bg-red-100 text-red-700" : "bg-muted"
              }`}
            >
              <Clock className="h-4 w-4" />
              <span className="font-mono font-bold">
                {formatTime(timeLeft)}
              </span>
            </div>

            <AlertDialog
              open={showSubmitDialog}
              onOpenChange={setShowSubmitDialog}
            >
              <AlertDialogTrigger asChild>
                <Button>Nộp bài</Button>
              </AlertDialogTrigger>

              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Xác nhận nộp bài?</AlertDialogTitle>
                  <AlertDialogDescription asChild>
                    <div className="mt-4 space-y-3">
                      <div className="flex items-center justify-between rounded-lg bg-muted p-3">
                        <span>Đã trả lời</span>
                        <span className="font-bold text-primary">
                          {answeredCount}/{totalQuestions}
                        </span>
                      </div>

                      <div className="flex items-center justify-between rounded-lg bg-muted p-3">
                        <span>Chưa trả lời</span>
                        <span className="font-bold text-orange-600">
                          {totalQuestions - answeredCount}
                        </span>
                      </div>

                      <div className="flex items-center justify-between rounded-lg bg-muted p-3">
                        <span>Đánh dấu xem lại</span>
                        <span className="font-bold text-yellow-600">
                          {flagged.length}
                        </span>
                      </div>

                      {totalQuestions - answeredCount > 0 && (
                        <div className="flex items-center gap-2 rounded-lg bg-orange-50 p-3 text-sm text-orange-700">
                          <AlertCircle className="h-4 w-4" />
                          <span>
                            Bạn còn {totalQuestions - answeredCount} câu chưa trả lời!
                          </span>
                        </div>
                      )}
                      {submitError && (
                        <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
                          <AlertCircle className="h-4 w-4" />
                          <span>{submitError}</span>
                        </div>
                      )}
                    </div>
                  </AlertDialogDescription>
                </AlertDialogHeader>

                <AlertDialogFooter>
                  <AlertDialogCancel>Quay lại làm bài</AlertDialogCancel>
                  <AlertDialogAction
                    disabled={isSubmitting}
                    onClick={(event) => {
                      event.preventDefault();
                      void handleSubmit();
                    }}
                  >
                      Xác nhận nộp bài
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>

        {(isLoadingQuestions || questionError) && (
          <div className="border-b bg-[#F8FBFF] px-6 py-3 text-sm text-muted-foreground">
            {isLoadingQuestions
              ? "Loading test questions from FastAPI..."
              : `Using local fallback questions: ${questionError}`}
          </div>
        )}

        <div className="flex-1 overflow-auto p-6">
          <div className="mx-auto max-w-3xl space-y-6">
            <div className="flex items-center gap-3">
              <Badge
                variant={isListeningSection ? "default" : "secondary"}
                className="gap-1"
              >
                {isListeningSection ? (
                  <>
                    <Volume2 className="h-3 w-3" />
                    LISTENING
                  </>
                ) : (
                  <>
                    <FileText className="h-3 w-3" />
                    READING
                  </>
                )}
              </Badge>

              <span className="text-sm text-muted-foreground">
                Part {currentQ.part}
              </span>

              <Badge variant="outline" className="ml-auto">
                Question {currentQuestion}/{totalQuestions}
              </Badge>

              <Badge variant="outline" className="ml-auto hidden">
                Câu {currentQuestion}/{totalQuestions}
              </Badge>
            </div>

            {(currentAudioUrl || (isListeningSection && questionSource === "local")) && (
              <AudioPlayerBar
                src={currentAudioUrl}
                currentTimeSeconds={0}
                durationSeconds={18}
                className="border-[#ececec] bg-[#f4f4f4]"
              />
            )}

            <Card className="shadow-lg" data-highlight-root>
              <CardHeader className="pb-4">
                <div className="flex items-start justify-between">
                  <CardTitle
                    className="text-lg leading-relaxed"
                    data-highlight-target="question"
                    data-highlight-key="question"
                    onMouseUp={handleTextSelect}
                    onKeyUp={handleTextSelect}
                  >
                    {renderHighlightedText(currentQ.question)}
                  </CardTitle>

                  <RunnerActionButtons
                    bookmarked={isBookmarked || flagged.includes(currentQuestion)}
                    hasNote={Boolean(currentNotebookStatus.hasNote || savedNotes.length)}
                    hasHighlight={Boolean(currentNotebookStatus.hasHighlight || savedHighlights.length)}
                    canHighlight={Boolean(selectedTextForHighlight)}
                    labels={{
                      mark: t("runner.mark"),
                      marked: t("runner.marked"),
                      note: t("runner.note"),
                      highlight: t("runner.highlight"),
                      highlightHint: t("runner.selectTextToHighlight"),
                    }}
                    onToggleBookmark={() => void handleToggleBookmark()}
                    onOpenNote={() => setNoteFocusKey((value) => value + 1)}
                    onHighlight={() => void handleCreateHighlight()}
                  />
                </div>
              </CardHeader>

              <CardContent
                className="space-y-3"
                data-highlight-root
                onMouseUp={handleTextSelect}
                onKeyUp={handleTextSelect}
              >
                {currentImageUrl ? (
                  <div className="overflow-hidden rounded-xl border border-[#dfe7f5] bg-[#f8fbff]">
                    <img
                      src={currentImageUrl}
                      alt={`TOEIC Part ${currentQ.part}`}
                      className="max-h-[420px] w-full object-contain"
                    />
                  </div>
                ) : null}

                {currentPassageText ? (
                  <div
                    className="rounded-xl border border-[#E6EDF8] bg-[#F8FBFF] p-4 text-sm leading-relaxed text-foreground"
                    data-highlight-target="passage"
                    data-highlight-key="passage"
                    onMouseUp={handleTextSelect}
                    onKeyUp={handleTextSelect}
                  >
                    {currentPassageTitle ? (
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        {currentPassageTitle}
                      </p>
                    ) : null}
                    {renderHighlightedText(currentPassageText)}
                  </div>
                ) : null}

                {currentQ.options.map((option) => (
                  <button
                    key={option.id}
                    onClick={() => handleAnswer(currentQuestion, option.id)}
                    className={`flex w-full items-center gap-4 rounded-xl border-2 p-4 text-left transition-all ${
                      answers[currentQuestion] === option.id
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/50"
                    }`}
                  >
                    <div
                      className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold ${
                        answers[currentQuestion] === option.id
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted"
                      }`}
                    >
                      {option.id}
                    </div>

                    <span
                      className="flex-1"
                      data-highlight-target="option"
                      data-highlight-key={option.id}
                      onMouseUp={handleTextSelect}
                      onKeyUp={handleTextSelect}
                    >
                      {renderHighlightedText(option.text)}
                    </span>

                    {answers[currentQuestion] === option.id && (
                      <Check className="h-5 w-5 text-primary" />
                    )}
                  </button>
                ))}
              </CardContent>
            </Card>

            <div className="flex items-center justify-between pt-4">
              <Button
                variant="outline"
                onClick={() =>
                  setCurrentQuestion((prev) => Math.max(1, prev - 1))
                }
                disabled={currentQuestion === 1}
                className="gap-2"
              >
                <ChevronLeft className="h-4 w-4" />
                Câu trước
              </Button>

              <span className="text-sm text-muted-foreground">
                Câu {currentQuestion} / {totalQuestions}
              </span>

              <Button
                onClick={() =>
                  setCurrentQuestion((prev) => Math.min(totalQuestions, prev + 1))
                }
                disabled={currentQuestion === totalQuestions}
                className="gap-2"
              >
                Câu sau
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>

          </div>
        </div>
      </div>

      <aside className="hidden w-[390px] shrink-0 overflow-y-auto border-l border-[#DDE7F7] bg-[#F8FAFC] p-4 lg:block">
        <div className="sticky top-4 space-y-4">
          <RunnerNotebookPanel
            noteValue={questionNote}
            onNoteChange={(value) => {
              setQuestionNote(value);
              setNoteSaved(false);
            }}
            onSaveNote={() => void handleSaveNote()}
            highlights={savedHighlights}
            focusKey={noteFocusKey}
            saving={isSavingNote}
            saved={noteSaved}
            disabled={!currentSqlQuestionId}
            error={reviewToolError}
            labels={{
              notebook: t("runner.notebook"),
              notesForQuestion: t("runner.notesForQuestion"),
              saveNote: t("runner.saveNote"),
              saved: t("runner.saved"),
              notePlaceholder: t("runner.notePlaceholder"),
              noQuestionSelected: t("runner.noQuestionSelected"),
              loading: t("common.loading"),
              highlights: t("runner.highlights"),
            }}
          />

          <RightAnswerSheet
            items={answerSheetItems}
            answeredCount={answeredCount}
            totalCount={totalQuestions}
            groupByPart={runnerType === "full"}
            labels={{
              title: t("runner.questionList"),
              answered: t("runner.answered"),
              unanswered: t("runner.unanswered"),
              all: t("runner.all"),
              marked: t("runner.marked"),
              hasNote: t("runner.hasNote"),
              hasHighlight: t("runner.hasHighlight"),
              listening: t("runner.listening"),
              reading: t("runner.reading"),
              part: t("runner.part"),
            }}
            onSelect={(item) => goToQuestion(Number(item.id))}
          />
        </div>
      </aside>

      {false ? (
      <div className="flex w-80 flex-col border-l bg-card">
        <div className="border-b p-4">
          <h3 className="font-semibold">Danh sách câu hỏi</h3>
        </div>

        <div className="flex-1 overflow-auto p-4">
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="rounded-lg bg-primary/10 p-2">
                <p className="text-lg font-bold text-primary">
                  {answeredCount}
                </p>
                <p className="text-xs text-muted-foreground">Đã làm</p>
              </div>

              <div className="rounded-lg bg-orange-100 p-2">
                <p className="text-lg font-bold text-orange-600">
                  {totalQuestions - answeredCount}
                </p>
                <p className="text-xs text-muted-foreground">Chưa làm</p>
              </div>

              <div className="rounded-lg bg-yellow-100 p-2">
                <p className="text-lg font-bold text-yellow-600">
                  {flagged.length}
                </p>
                <p className="text-xs text-muted-foreground">Đánh dấu</p>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="flex items-center gap-2 text-sm font-medium">
                <Volume2 className="h-4 w-4" />
                Listening ({listeningQuestionNumbers.length})
              </h4>

              <div className="grid grid-cols-10 gap-1">
                {listeningQuestionNumbers.map(({ number: num }) => {
                  const status = getQuestionStatus(num);

                  return (
                    <button
                      key={num}
                      onClick={() => goToQuestion(num)}
                      className={`h-6 w-6 rounded text-xs font-medium transition-all ${
                        status === "current"
                          ? "bg-primary text-primary-foreground ring-2 ring-primary ring-offset-2"
                          : status === "flagged"
                            ? "border border-yellow-300 bg-yellow-100 text-yellow-700"
                            : status === "answered"
                              ? "bg-primary/20 text-primary"
                              : "bg-muted hover:bg-muted-foreground/20"
                      }`}
                    >
                      {num}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="flex items-center gap-2 text-sm font-medium">
                <FileText className="h-4 w-4" />
                Reading ({readingQuestionNumbers.length})
              </h4>

              <div className="grid grid-cols-10 gap-1">
                {readingQuestionNumbers.map(({ number: num }) => {
                  const status = getQuestionStatus(num);

                  return (
                    <button
                      key={num}
                      onClick={() => goToQuestion(num)}
                      className={`h-6 w-6 rounded text-xs font-medium transition-all ${
                        status === "current"
                          ? "bg-primary text-primary-foreground ring-2 ring-primary ring-offset-2"
                          : status === "flagged"
                            ? "border border-yellow-300 bg-yellow-100 text-yellow-700"
                            : status === "answered"
                              ? "bg-primary/20 text-primary"
                              : "bg-muted hover:bg-muted-foreground/20"
                      }`}
                    >
                      {num}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex items-center gap-4 border-t pt-2 text-xs">
              <div className="flex items-center gap-1">
                <div className="h-4 w-4 rounded bg-primary/20" />
                <span>Đã làm</span>
              </div>

              <div className="flex items-center gap-1">
                <div className="h-4 w-4 rounded border border-yellow-300 bg-yellow-100" />
                <span>Đánh dấu</span>
              </div>

              <div className="flex items-center gap-1">
                <div className="h-4 w-4 rounded bg-muted" />
                <span>Chưa làm</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      ) : null}
    </div>
    </ProFeatureGuard>
  );
}
