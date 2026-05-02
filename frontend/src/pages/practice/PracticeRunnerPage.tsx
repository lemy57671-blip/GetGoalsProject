"use client";

import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  BookOpen,
  Brain,
  Check,
  CheckCircle2,
  ChevronLeft,
  Clock,
  Flag,
  Highlighter,
  Headphones,
  Pause,
  Play,
  Send,
  Sparkles,
  X,
} from "lucide-react";

import { AudioPlayerBar } from "@/components/audio-player-bar";
import { ProFeatureGuard } from "@/components/pro-feature-guard";
import { ChatPanel } from "@src/components/chat/ChatPanel";
import { IntegratedQuestionBar } from "@src/components/runner/IntegratedQuestionBar";
import { RunnerActionButtons } from "@src/components/runner/RunnerActionButtons";
import { RunnerRightPanel, type RunnerRightPanelTab } from "@src/components/runner/RunnerRightPanel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { attemptsService } from "@src/services/attemptsService";
import { ApiError } from "@src/services/apiClient";
import { chatService } from "@src/services/chatService";
import { useLanguage } from "@src/contexts/LanguageContext";
import { roadmapService } from "@src/services/roadmapService";
import { reviewService, type ReviewHighlight, type ReviewNote } from "@src/services/reviewService";
import { toeicService, ToeicRunnerQuestion } from "@src/services/toeicService";

type TutorMessage = {
  role: "user" | "assistant";
  content: string;
};

function parsePositiveInteger(value: string | null) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function formatReviewFocusLabel({
  matchStrategy,
  usedPart,
  usedSkill,
  usedSubskill,
  usedDifficulty,
}: {
  matchStrategy?: string;
  usedPart?: number | null;
  usedSkill?: string | null;
  usedSubskill?: string | null;
  usedDifficulty?: string | null;
}) {
  const partLabel = usedPart ? `Part ${usedPart}` : "the same TOEIC part";
  const focusLabel = usedSubskill || usedSkill;
  const levelLabel =
    usedDifficulty && usedDifficulty !== "mixed" ? ` at a ${usedDifficulty} level` : "";

  if (!matchStrategy || matchStrategy === "no_match") {
    return "Backend-selected similar questions";
  }

  if (matchStrategy.includes("skill_subskill")) {
    return focusLabel
      ? `Similar ${partLabel} questions from the same focus area${levelLabel}`
      : `Similar questions from ${partLabel}${levelLabel}`;
  }

  if (matchStrategy.includes("skill")) {
    return usedSkill
      ? `Similar ${partLabel} questions for ${usedSkill}${levelLabel}`
      : `Similar questions from ${partLabel}${levelLabel}`;
  }

  if (matchStrategy.includes("difficulty")) {
    return `Same part practice${levelLabel || " at a similar level"}`;
  }

  if (matchStrategy.includes("same_part")) {
    return `Practice from ${partLabel}`;
  }

  return "Backend-selected similar questions";
}

function normalizePart(part: unknown) {
  if (typeof part === "number") return part;

  if (typeof part === "string") {
    const matched = part.match(/\d+/);
    if (matched) return Number(matched[0]);
  }

  return null;
}

function getSqlQuestionId(question?: ToeicRunnerQuestion | null) {
  if (!question) return null;
  return (
    question.docxQuestionId ||
    question.sourceQuestionId ||
    question.sqlId ||
    question.dbId ||
    question.questionId ||
    question.id ||
    null
  );
}

export function PracticeRunnerPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { t } = useLanguage();

  const roadmapWeekId = parsePositiveInteger(
    searchParams.get("weekId") || searchParams.get("roadmapWeekId"),
  );
  const roadmapSetId = parsePositiveInteger(searchParams.get("setId"));
  const isRoadmapSetRunner = Boolean(roadmapWeekId && roadmapSetId);
  const runnerMode = (searchParams.get("mode") || "exam").trim().toLowerCase();
  const currentAttemptId = parsePositiveInteger(
    searchParams.get("attempt_id") || searchParams.get("attemptId"),
  );
  const isReviewFocusRunner = runnerMode === "review-focus";
  const isQuestionIdRunner = Boolean((searchParams.get("question_ids") || "").trim());

  const reviewFocusParts = (searchParams.get("parts") || "5")
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((part) => Number.isFinite(part) && part >= 1 && part <= 7);

  const reviewFocusItemId = parsePositiveInteger(searchParams.get("reviewItemId"));
  const reviewFocusSkill = searchParams.get("skill") || "";
  const reviewFocusSubskill = searchParams.get("subskill") || "";

  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [selectedAnswer, setSelectedAnswer] = useState<string>("");
  const [flaggedQuestions, setFlaggedQuestions] = useState<number[]>([]);
  const [showExplanation, setShowExplanation] = useState(false);
  const isSmartMode = runnerMode === "smart" || runnerMode === "review-focus";

  const [showSubmitDialog, setShowSubmitDialog] = useState(false);
  const [timeElapsed, setTimeElapsed] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [questions, setQuestions] = useState<ToeicRunnerQuestion[]>([]);
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(true);
  const [questionError, setQuestionError] = useState<string | null>(null);
  const [startedAtUtc, setStartedAtUtc] = useState(() => new Date().toISOString());
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [tutorInput, setTutorInput] = useState("");
  const [tutorLoading, setTutorLoading] = useState(false);
  const [tutorConversationId, setTutorConversationId] = useState<number | null>(null);
  const [tutorMessages, setTutorMessages] = useState<TutorMessage[]>([]);
  const [savedNotes, setSavedNotes] = useState<ReviewNote[]>([]);
  const [savedHighlights, setSavedHighlights] = useState<ReviewHighlight[]>([]);
  const [questionNote, setQuestionNote] = useState("");
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [selectedTextForHighlight, setSelectedTextForHighlight] = useState("");
  const [isSavingNote, setIsSavingNote] = useState(false);
  const [isSavingHighlight, setIsSavingHighlight] = useState(false);
  const [reviewToolError, setReviewToolError] = useState<string | null>(null);
  const [rightPanelTab, setRightPanelTab] = useState<RunnerRightPanelTab>("ai");
  const [noteSaved, setNoteSaved] = useState(false);
  const [notebookStatusByIndex, setNotebookStatusByIndex] = useState<
    Record<number, { bookmarked?: boolean; hasNote?: boolean; hasHighlight?: boolean }>
  >({});

  const [runnerContext, setRunnerContext] = useState<{
    title?: string;
    subtitle?: string;
    note?: string;
  } | null>(null);

  const question = questions[currentQuestion];
  const questionSqlId = getSqlQuestionId(question);
  const progress = questions.length > 0 ? ((currentQuestion + 1) / questions.length) * 100 : 0;
  const answeredCount = Object.keys(answers).length;
  const currentNotebookStatus = notebookStatusByIndex[currentQuestion] || {};
  const highlightTerms = useMemo(
    () =>
      Array.from(
        new Set(
          savedHighlights
            .map((highlight) => highlight.selectedText.trim())
            .filter((text) => text.length > 0),
        ),
      ),
    [savedHighlights],
  );

  const renderHighlightedText = (text?: string | null) => {
    const value = text || "";
    if (!value || highlightTerms.length === 0) return value;
    const escapedTerms = highlightTerms
      .map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
      .filter(Boolean);
    if (escapedTerms.length === 0) return value;
    const regex = new RegExp(`(${escapedTerms.join("|")})`, "gi");
    return value.split(regex).map((part, index) => {
      const matched = highlightTerms.some((term) => term.toLowerCase() === part.toLowerCase());
      return matched ? (
        <mark key={`${part}-${index}`} className="rounded bg-yellow-200 px-0.5 text-foreground">
          {part}
        </mark>
      ) : (
        part
      );
    });
  };

  useEffect(() => {
    let cancelled = false;

    async function loadQuestions() {
      setIsLoadingQuestions(true);
      setQuestionError(null);

      try {
        let usedReviewFocusEndpoint = false;
        let usedReviewFocusFallback = false;
        let reviewFocusLabel = "";

        const result =
          roadmapWeekId && roadmapSetId
            ? await roadmapService.getSetRunner(roadmapWeekId, roadmapSetId)
            : null;

        const loadedQuestions =
          result?.questions ||
          (await (async () => {
            const parts = (searchParams.get("parts") || "1")
              .split(",")
              .map((item) => Number(item.trim()))
              .filter((part) => Number.isFinite(part) && part >= 1 && part <= 7);

            const selectedParts = parts.length > 0 ? parts : [1];
            const difficulty = searchParams.get("difficulty") || "mixed";
            const requestedCount = Number(searchParams.get("count") || "30");
            const count =
              Number.isFinite(requestedCount) && requestedCount > 0 ? requestedCount : 30;
            const questionIds = (searchParams.get("question_ids") || "")
              .split(",")
              .map((item) => Number(item.trim()))
              .filter((item) => Number.isInteger(item) && item > 0);

            const loadPartBasedQuestions = () =>
              selectedParts.length === 1
                ? toeicService.getPartRunner(selectedParts[0], count, difficulty)
                : toeicService.getMixedRunner(selectedParts, count, difficulty);

            if (questionIds.length > 0) {
              return toeicService.getQuestionsByIds(questionIds);
            }

            if (isReviewFocusRunner && reviewFocusItemId) {
              try {
                const focusedResult = await toeicService.getReviewFocusRunner(
                  reviewFocusItemId,
                  count,
                  difficulty,
                );

                if (focusedResult.questions.length > 0) {
                  usedReviewFocusEndpoint = true;
                  reviewFocusLabel = formatReviewFocusLabel({
                    matchStrategy: focusedResult.matchStrategy,
                    usedPart: focusedResult.usedPart,
                    usedSkill: focusedResult.usedSkill,
                    usedSubskill: focusedResult.usedSubskill,
                    usedDifficulty: focusedResult.usedDifficulty,
                  });
                  return focusedResult.questions;
                }

                usedReviewFocusFallback = true;
              } catch {
                usedReviewFocusFallback = true;
              }
            }

            return loadPartBasedQuestions();
          })());

        if (cancelled) return;

        if (loadedQuestions.length > 0) {
          setQuestions(loadedQuestions);
          setCurrentQuestion(0);
          setAnswers({});
          setFlaggedQuestions([]);
          setShowExplanation(false);
          setTutorConversationId(null);
          setStartedAtUtc(new Date().toISOString());

          setRunnerContext(
            result
              ? {
                  title: result.title || `Roadmap set ${result.setId}`,
                  subtitle: `Roadmap week ${result.weekId} - set ${result.setId}`,
                }
              : isReviewFocusRunner
                ? {
                    title: `Review focus - Part ${
                      (reviewFocusParts.length > 0 ? reviewFocusParts : [5]).join(", ")
                    }`,
                    subtitle: [
                      usedReviewFocusEndpoint
                        ? "Backend-selected similar questions"
                        : usedReviewFocusFallback
                          ? "Part-based fallback practice"
                          : "Part-based review practice",
                      reviewFocusSkill,
                      reviewFocusSubskill,
                    ]
                      .filter(Boolean)
                      .join(" / "),
                    note: reviewFocusLabel || undefined,
                  }
                : isQuestionIdRunner
                  ? {
                      title: "Review questions",
                      subtitle: "Practice from selected review question ids",
                    }
                : null,
          );
        } else {
          if (isRoadmapSetRunner) {
            setQuestions([]);
            setRunnerContext(null);
          }

          setQuestionError(
            isRoadmapSetRunner
              ? "The roadmap set API returned an empty question set."
              : "Chưa có bài tập phù hợp với lựa chọn này.",
          );
        }
      } catch (error) {
        if (!cancelled) {
          if (isRoadmapSetRunner) {
            setQuestions([]);
            setRunnerContext(null);
          }

          setQuestionError(
            error instanceof Error
              ? error.message
              : isRoadmapSetRunner
                ? "Could not load roadmap set questions."
                : "Could not load TOEIC runner questions.",
          );
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
  }, [searchParams]);

  useEffect(() => {
    const timer = setInterval(() => {
      if (!isPaused) {
        setTimeElapsed((prev) => prev + 1);
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [isPaused]);

  useEffect(() => {
    setSelectedAnswer(answers[currentQuestion]?.toString() || "");
  }, [currentQuestion, answers]);

  useEffect(() => {
    let cancelled = false;

    async function loadReviewTools() {
      if (!questionSqlId) {
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
          reviewService.getNotes(questionSqlId),
          reviewService.getHighlights(questionSqlId),
          reviewService.getBookmark(questionSqlId),
        ]);

        if (cancelled) return;
        setSavedNotes(notes);
        setSavedHighlights(highlights);
        setQuestionNote(notes[0]?.noteText || "");
        setNoteSaved(false);
        setIsBookmarked(bookmarked);
        setNotebookStatusByIndex((prev) => ({
          ...prev,
          [currentQuestion]: {
            bookmarked,
            hasNote: notes.length > 0,
            hasHighlight: highlights.length > 0,
          },
        }));
        setFlaggedQuestions((prev) =>
          bookmarked
            ? Array.from(new Set([...prev, currentQuestion]))
            : prev.filter((index) => index !== currentQuestion),
        );
      } catch (error) {
        if (!cancelled) {
          setSavedNotes([]);
          setSavedHighlights([]);
          setQuestionNote("");
          setNoteSaved(false);
          setIsBookmarked(false);
          setNotebookStatusByIndex((prev) => ({
            ...prev,
            [currentQuestion]: { bookmarked: false, hasNote: false, hasHighlight: false },
          }));
          setReviewToolError(
            error instanceof Error ? error.message : "Khong tai duoc so tay cho cau nay.",
          );
        }
      }
    }

    void loadReviewTools();

    return () => {
      cancelled = true;
    };
  }, [questionSqlId]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;

    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const handleAnswer = (answer: string) => {
    setSelectedAnswer(answer);
    setAnswers((prev) => ({ ...prev, [currentQuestion]: parseInt(answer) }));
  };

  const handleNext = () => {
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion((prev) => prev + 1);
      setShowExplanation(false);
    }
  };

  const handlePrev = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion((prev) => prev - 1);
      setShowExplanation(false);
    }
  };

  const handleFlag = async () => {
    if (!questionSqlId) return;
    const nextBookmarked = !isBookmarked;
    setIsBookmarked(nextBookmarked);
    setFlaggedQuestions((prev) =>
      nextBookmarked
        ? Array.from(new Set([...prev, currentQuestion]))
        : prev.filter((q) => q !== currentQuestion),
    );

    try {
      const saved = await reviewService.toggleBookmark(questionSqlId, currentAttemptId);
      setIsBookmarked(saved);
      setNotebookStatusByIndex((prev) => ({
        ...prev,
        [currentQuestion]: {
          ...(prev[currentQuestion] || {}),
          bookmarked: saved,
        },
      }));
      setFlaggedQuestions((prev) =>
        saved
          ? Array.from(new Set([...prev, currentQuestion]))
          : prev.filter((q) => q !== currentQuestion),
      );
    } catch (error) {
      setIsBookmarked(!nextBookmarked);
      setNotebookStatusByIndex((prev) => ({
        ...prev,
        [currentQuestion]: {
          ...(prev[currentQuestion] || {}),
          bookmarked: !nextBookmarked,
        },
      }));
      setFlaggedQuestions((prev) =>
        !nextBookmarked
          ? Array.from(new Set([...prev, currentQuestion]))
          : prev.filter((q) => q !== currentQuestion),
      );
      setReviewToolError(error instanceof Error ? error.message : "Khong luu duoc danh dau.");
    }
  };

  const handleTextSelect = () => {
    const selection = window.getSelection();
    const selectedText = selection?.toString().trim() || "";
    if (selectedText) {
      setSelectedTextForHighlight(selectedText.slice(0, 2000));
    }
  };

  const handleSaveNote = async () => {
    if (!questionSqlId || !questionNote.trim()) return;
    setIsSavingNote(true);
    setReviewToolError(null);
    try {
      const note = await reviewService.saveNote(questionSqlId, questionNote.trim(), currentAttemptId);
      setSavedNotes([note]);
      setQuestionNote(note.noteText);
      setNoteSaved(true);
      setNotebookStatusByIndex((prev) => ({
        ...prev,
        [currentQuestion]: {
          ...(prev[currentQuestion] || {}),
          hasNote: true,
        },
      }));
    } catch (error) {
      setReviewToolError(error instanceof Error ? error.message : "Khong luu duoc ghi chu.");
    } finally {
      setIsSavingNote(false);
    }
  };

  const handleCreateHighlight = async (selectedText = selectedTextForHighlight) => {
    if (!selectedText.trim()) {
      setReviewToolError(t("runner.highlightHint"));
      return;
    }
    if (!questionSqlId) return;
    setIsSavingHighlight(true);
    setReviewToolError(null);
    try {
      const highlight = await reviewService.createHighlight({
        question_id: questionSqlId,
        attempt_id: currentAttemptId,
        target_type: "question_text",
        selected_text: selectedText.trim(),
        color: "yellow",
      });
      setSavedHighlights((prev) => [highlight, ...prev]);
      setNotebookStatusByIndex((prev) => ({
        ...prev,
        [currentQuestion]: {
          ...(prev[currentQuestion] || {}),
          hasHighlight: true,
        },
      }));
      setSelectedTextForHighlight("");
      window.getSelection()?.removeAllRanges();
    } catch (error) {
      setReviewToolError(error instanceof Error ? error.message : "Khong luu duoc highlight.");
    } finally {
      setIsSavingHighlight(false);
    }
  };

  const goToQuestion = (index: number) => {
    setCurrentQuestion(index);
    setShowExplanation(false);
  };

  const handleAskTutor = async (messageOverride?: string) => {
    if (!question || tutorLoading) return;

    const userMessage = (messageOverride || tutorInput).trim();
    if (!userMessage) return;
    setRightPanelTab("ai");

    const selectedAnswerIndex = answers[currentQuestion] ?? null;
    const correctAnswerIndex =
      typeof question.correct === "number" ? question.correct : null;

    const selectedAnswerText =
      typeof selectedAnswerIndex === "number"
        ? question.options[selectedAnswerIndex] ?? null
        : null;
    const selectedOptionLabel =
      typeof selectedAnswerIndex === "number"
        ? String.fromCharCode(65 + selectedAnswerIndex)
        : null;

    const correctAnswerText =
      typeof correctAnswerIndex === "number"
        ? question.options[correctAnswerIndex] ?? null
        : null;

    const questionNumber = currentQuestion + 1;
    const part = normalizePart(question.part);
    const questionSqlId =
      question.docxQuestionId ||
      question.sourceQuestionId ||
      question.sqlId ||
      question.dbId ||
      question.questionId ||
      question.id;

    const currentQuestionPayload = {
      id: questionSqlId,
      questionId: questionSqlId,
      question_id: questionSqlId,
      sqlId: questionSqlId,
      runnerQuestionId: question.id,

      questionNumber,
      question_number: questionNumber,

      part,
      Part: part,

      section: question.section,
      skill: question.skill,

      questionText: question.question,
      question_text: question.question,
      text: question.question,
      content: question.question,
      prompt: question.question,

      passageTitle: question.passageTitle || null,
      passageText: question.passageText || null,
      passage_text: question.passageText || null,
      passage: question.passageText || null,

      options: question.options.map((option, index) => ({
        id: index,
        label: String.fromCharCode(65 + index),
        text: option,
        content: option,
        value: option,
        isCorrect: index === correctAnswerIndex,
      })),
      choices: question.options,

      selectedAnswerIndex,
      selected_answer_index: selectedAnswerIndex,
      selectedAnswer: selectedAnswerText,
      selected_answer: selectedAnswerText,

      correctAnswerIndex,
      correct_answer_index: correctAnswerIndex,
      correctAnswer: correctAnswerText,
      correct_answer: correctAnswerText,

      explanation: question.explanation || null,
    };

    setTutorInput("");
    setTutorMessages((current) => [...current, { role: "user", content: userMessage }]);
    setTutorLoading(true);

    try {
      const chatPayload = {
        message: userMessage,

        conversation_id: tutorConversationId,
        conversationId: tutorConversationId,

        question_id: questionSqlId,
        questionId: questionSqlId,
        currentQuestionId: questionSqlId,
        sqlId: questionSqlId,
        runner_question_id: question.id,
        runnerQuestionId: question.id,

        context_type: "practice_runner",
        contextType: "practice_runner",

        selected_answer_index: selectedAnswerIndex,
        selectedAnswerIndex,
        selected_option_label: selectedOptionLabel,
        selectedOptionLabel,

        questionNumber,
        question_number: questionNumber,
        part,

        questionText: question.question,
        question_text: question.question,
        passageText: question.passageText || null,
        passage_text: question.passageText || null,

        options: currentQuestionPayload.options,
        choices: question.options,

        selectedAnswer: selectedAnswerText,
        selected_answer: selectedAnswerText,

        correctAnswer: correctAnswerText,
        correct_answer: correctAnswerText,

        explanation: question.explanation || null,

        currentQuestion: currentQuestionPayload,
        current_question: currentQuestionPayload,
        question: currentQuestionPayload,

        context: {
          type: "practice_question",
          runnerMode,
          currentQuestionIndex: currentQuestion,
          totalQuestions: questions.length,
          isSmartMode,
        },
      };

      console.log("[AI Tutor payload]", {
        message: chatPayload.message,
        question_id: chatPayload.question_id,
        context_type: chatPayload.context_type,
        selected_answer_index: chatPayload.selected_answer_index,
        selected_option_label: chatPayload.selected_option_label,
        conversation_id: chatPayload.conversation_id,
      });

      const response = await chatService.sendDetailed(chatPayload);

      const nextConversationId =
        typeof response.conversation_id === "number"
          ? response.conversation_id
          : typeof response.conversationId === "number"
            ? response.conversationId
            : null;

      if (nextConversationId) {
        setTutorConversationId(nextConversationId);
      }

      setTutorMessages((current) => [
        ...current,
        {
          role: "assistant",
          content:
            response.reply ||
            response.answer ||
            response.content ||
            response.message ||
            "AI Tutor chưa tạo được phản hồi.",
        },
      ]);
    } catch (error) {
      const message =
        error instanceof ApiError && [401, 403].includes(error.status)
          ? "AI Tutor là tính năng Pro. Vui lòng nâng cấp hoặc đăng nhập tài khoản Pro để dùng chatbox trong lúc luyện."
          : error instanceof Error
            ? `Không gọi được AI Tutor: ${error.message}`
            : "Không gọi được AI Tutor.";

      setTutorMessages((current) => [...current, { role: "assistant", content: message }]);
    } finally {
      setTutorLoading(false);
    }
  };

  const handleSubmitPractice = async () => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const result = await attemptsService.submitPracticeAttempt({
        questions,
        answers,
        flaggedQuestions,
        timeSpentSeconds: timeElapsed,
        mode: runnerMode,
        difficulty: searchParams.get("difficulty") || "mixed",
        title: runnerContext?.title,
        subtitle: runnerContext?.subtitle,
        startedAtUtc,
      });

      setShowSubmitDialog(false);
      navigate(`/practice/summary?attemptId=${result.attemptId}`, {
        state: {
          attempt: result,
          retryUrl:
            isReviewFocusRunner && reviewFocusItemId
              ? `/practice/runner?${searchParams.toString()}`
              : undefined,
        },
      });
    } catch (error) {
      setSubmitError(
        error instanceof Error ? error.message : "Could not submit this practice attempt.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!question) {
    return (
      <div className="min-h-screen bg-background -m-4 lg:-m-6">
        <div className="container mx-auto px-4 py-10">
          <Card className="mx-auto max-w-2xl rounded-3xl border-border bg-card shadow-sm">
            <CardHeader>
              <CardTitle>Could not load this practice set</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                {questionError || "This runner does not have any questions to display yet."}
              </p>
              <div className="flex flex-wrap gap-3">
                <Button asChild>
                  <Link to={isRoadmapSetRunner ? "/roadmap" : "/practice"}>
                    Back to {isRoadmapSetRunner ? "roadmap" : "practice"}
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background -m-4 lg:-m-6">
      <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur">
        <div className="container mx-auto px-4">
          <div className="flex h-14 items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="sm" asChild>
                <Link to={isRoadmapSetRunner ? "/roadmap" : "/practice"}>
                  <ChevronLeft className="mr-1 h-4 w-4" />
                  {t("runner.exit")}
                </Link>
              </Button>

              <div className="flex items-center gap-2">
                <Badge variant={question.section === "Listening" ? "default" : "secondary"}>
                  {question.section === "Listening" ? (
                    <Headphones className="mr-1 h-3 w-3" />
                  ) : (
                    <BookOpen className="mr-1 h-3 w-3" />
                  )}
                  {question.section}
                </Badge>

                <Badge variant="outline">{question.part}</Badge>

                {isSmartMode && (
                  <Badge className="border-0 bg-primary/10 text-primary">
                    <Brain className="mr-1 h-3 w-3" />
                    Smart Mode
                  </Badge>
                )}
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-sm">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span className="font-mono text-foreground">{formatTime(timeElapsed)}</span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setIsPaused(!isPaused)}
                >
                  {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
                </Button>
              </div>

              <span className="text-sm text-muted-foreground">
                {currentQuestion + 1} / {questions.length}
              </span>

              <Button onClick={() => setShowSubmitDialog(true)}>
                <Send className="mr-2 h-4 w-4" />
                {t("runner.submit")}
              </Button>
            </div>
          </div>

          <Progress value={progress} className="h-1" />
        </div>
      </header>

      <div className="container mx-auto px-4 py-6">
        {isReviewFocusRunner && (
          <div className="mb-4 rounded-2xl border border-[#E7EEF9] bg-[#F8FBFF] px-4 py-3 text-sm text-muted-foreground">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="border-0 bg-primary/10 text-primary">Review focus</Badge>
              <span>
                Practicing Part {(reviewFocusParts.length > 0 ? reviewFocusParts : [5]).join(", ")}
                {reviewFocusSkill ? ` / ${reviewFocusSkill}` : ""}
                {reviewFocusSubskill ? ` / ${reviewFocusSubskill}` : ""}.
                {runnerContext?.subtitle?.includes("Backend-selected")
                  ? " Questions are selected from the review-focus backend endpoint."
                  : " Skill context is shown from the review item; questions fall back to the part-based TOEIC runner."}
                {runnerContext?.note ? ` ${runnerContext.note}.` : ""}
              </span>
            </div>
          </div>
        )}

        {(isLoadingQuestions || questionError) && (
          <div className="mb-4 rounded-2xl border border-[#E7EEF9] bg-[#F8FBFF] px-4 py-3 text-sm text-muted-foreground">
            {isLoadingQuestions
              ? "Loading runner questions from FastAPI..."
              : `Using local fallback because TOEIC runner API failed: ${questionError}`}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-4">
          <div className="space-y-6 lg:col-span-3">
            <Card className="rounded-xl border-border">
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">
                      {t("runner.question")} {currentQuestion + 1}
                    </Badge>
                    <Badge variant="secondary" className="text-xs">
                      {question.skill}
                    </Badge>
                  </div>

                  <RunnerActionButtons
                    bookmarked={isBookmarked || flaggedQuestions.includes(currentQuestion)}
                    hasNote={Boolean(currentNotebookStatus.hasNote || savedNotes.length)}
                    hasHighlight={Boolean(currentNotebookStatus.hasHighlight || savedHighlights.length)}
                    canHighlight={Boolean(selectedTextForHighlight)}
                    labels={{
                      mark: t("runner.mark"),
                      marked: t("runner.marked"),
                      note: t("runner.note"),
                      highlight: t("runner.highlight"),
                      highlightHint: t("runner.highlightHint"),
                    }}
                    onToggleBookmark={() => void handleFlag()}
                    onOpenNote={() => setRightPanelTab("notes")}
                    onHighlight={() => void handleCreateHighlight()}
                  />
                </div>
              </CardHeader>

              <CardContent className="space-y-6" onMouseUp={handleTextSelect}>
                {(question.hasAudio || question.hasImage) && (
                  <div className="space-y-4">
                    {question.hasAudio && (
                      <AudioPlayerBar
                        src={question.audioUrl}
                        durationSeconds={32}
                        className="border-[#e5eaf4] bg-[#f5f9ff]"
                      />
                    )}

                    {question.hasImage && (
                      <div className="overflow-hidden rounded-xl border border-[#dfe7f5] bg-[#f8fbff]">
                        <img
                          src={question.imageUrl || question.graphicUrl}
                          alt={`TOEIC ${question.part}`}
                          className="max-h-[420px] w-full object-contain"
                        />
                      </div>
                    )}
                  </div>
                )}

                {(question.passageTitle || question.passageText) && (
                  <Card className="rounded-xl border-[#dfe7f5] bg-[#f8fbff]">
                    <CardContent className="space-y-2 pt-6">
                      {question.passageTitle && (
                        <p className="font-semibold text-foreground">{question.passageTitle}</p>
                      )}
                      {question.passageText && (
                        <p className="whitespace-pre-line text-sm leading-relaxed text-foreground">
                          {renderHighlightedText(question.passageText)}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                )}

                <div>
                  <p className="text-lg font-medium leading-relaxed text-foreground">
                    {renderHighlightedText(question.question)}
                  </p>
                </div>

                <div className="space-y-3">
                  {question.options.map((option, index) => {
                    const isSelected = selectedAnswer === index.toString();
                    const isCorrect = showExplanation && index === question.correct;
                    const isWrong = showExplanation && isSelected && index !== question.correct;

                    return (
                      <label
                        key={index}
                        className={`flex w-full items-center gap-4 rounded-xl border-2 p-4 text-left transition-all ${
                          isCorrect
                            ? "border-green-500 bg-green-500/10"
                            : isWrong
                              ? "border-destructive bg-destructive/10"
                              : isSelected
                                ? "border-primary bg-primary/5"
                                : "border-border bg-background hover:border-primary/50"
                        } ${showExplanation ? "cursor-default" : "cursor-pointer"}`}
                      >
                        <input
                          type="radio"
                          name={`practice-question-${currentQuestion}`}
                          value={index.toString()}
                          checked={isSelected}
                          onChange={() => !showExplanation && handleAnswer(index.toString())}
                          disabled={showExplanation}
                          className="sr-only"
                        />

                        <div
                          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                            isCorrect
                              ? "bg-green-500 text-white"
                              : isWrong
                                ? "bg-destructive text-destructive-foreground"
                                : isSelected
                                  ? "bg-primary text-primary-foreground"
                                  : "bg-muted text-foreground"
                          }`}
                        >
                          {String.fromCharCode(65 + index)}
                        </div>

                        <span className="flex-1 text-foreground">{renderHighlightedText(option)}</span>

                        {isCorrect && <CheckCircle2 className="h-5 w-5 shrink-0 text-green-500" />}
                        {isWrong && <X className="h-5 w-5 shrink-0 text-destructive" />}
                        {!showExplanation && isSelected && (
                          <Check className="h-5 w-5 shrink-0 text-primary" />
                        )}
                      </label>
                    );
                  })}
                </div>

                {isSmartMode && showExplanation && (
                  <Card className="rounded-xl border-primary bg-primary/5">
                    <CardHeader className="pb-2">
                      <CardTitle className="flex items-center gap-2 text-sm text-primary">
                        <Sparkles className="h-4 w-4" />
                        Giải thích từ AI
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm leading-relaxed text-foreground">
                        {question.explanation}
                      </p>
                    </CardContent>
                  </Card>
                )}

                {false ? (
                  <div className="rounded-xl border border-[#DDE7F7] bg-[#F8FBFF] p-4">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <p className="flex items-center gap-2 text-sm font-semibold text-foreground">
                        <BookOpen className="h-4 w-4 text-primary" />
                        {t("runner.note")}
                      </p>
                      {reviewToolError ? (
                        <p className="text-xs text-destructive">{reviewToolError}</p>
                      ) : null}
                    </div>
                    <Textarea
                      value={questionNote}
                      onChange={(event) => setQuestionNote(event.target.value)}
                      placeholder={t("runner.notePlaceholder")}
                      className="min-h-[88px] resize-none bg-white text-sm"
                    />
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                      <Button
                        size="sm"
                        onClick={() => void handleSaveNote()}
                        disabled={!questionSqlId || !questionNote.trim() || isSavingNote}
                      >
                        {isSavingNote
                          ? t("common.loading")
                          : savedNotes.length > 0
                            ? t("runner.updateNote")
                            : t("runner.saveNote")}
                      </Button>
                      {savedHighlights.length > 0 ? (
                        <p className="text-xs text-muted-foreground">
                          {t("runner.highlights")}: {savedHighlights.length}
                        </p>
                      ) : null}
                    </div>
                  </div>
                ) : null}

                {isSmartMode && selectedAnswer && !showExplanation ? (
                  <div className="flex justify-center border-t border-border pt-4">
                    <Button variant="outline" onClick={() => setShowExplanation(true)}>
                      <Brain className="mr-2 h-4 w-4" />
                      {t("runner.showExplanation")}
                    </Button>
                  </div>
                ) : null}

                <IntegratedQuestionBar
                  currentLabel={`${currentQuestion + 1} / ${questions.length}`}
                  answeredCount={answeredCount}
                  markedCount={flaggedQuestions.length}
                  previousDisabled={currentQuestion === 0}
                  nextDisabled={currentQuestion === questions.length - 1}
                  onPrevious={handlePrev}
                  onNext={handleNext}
                  items={questions.map((item, index) => ({
                    id: index,
                    label: String(index + 1),
                    part: item.partNumber,
                    current: index === currentQuestion,
                    answered: answers[index] !== undefined,
                    bookmarked: Boolean(notebookStatusByIndex[index]?.bookmarked || flaggedQuestions.includes(index)),
                    hasNote: Boolean(notebookStatusByIndex[index]?.hasNote),
                    hasHighlight: Boolean(notebookStatusByIndex[index]?.hasHighlight),
                  }))}
                  labels={{
                    previous: t("runner.previous"),
                    next: t("runner.next"),
                    questionList: t("runner.questionList"),
                    answered: t("runner.answered"),
                    marked: t("runner.marked"),
                    notes: t("runner.notes"),
                    highlights: t("runner.highlights"),
                    all: t("runner.all"),
                    part: t("runner.part"),
                    progress: t("runner.progress"),
                  }}
                  onSelect={(item) => goToQuestion(Number(item.id))}
                />
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4 lg:col-span-1">
            {false ? (
            <Card className="rounded-xl border-[#E6EDF8] bg-white shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm text-foreground">
                  <BookOpen className="h-4 w-4 text-primary" />
                  Ghi chú của bạn
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Textarea
                  value={questionNote}
                  onChange={(event) => setQuestionNote(event.target.value)}
                  placeholder="Ghi lại mẹo, cấu trúc hoặc lỗi cần nhớ..."
                  className="min-h-[96px] resize-none text-sm"
                />
                <Button
                  size="sm"
                  className="w-full"
                  onClick={() => void handleSaveNote()}
                  disabled={!questionSqlId || !questionNote.trim() || isSavingNote}
                >
                  {isSavingNote ? "Đang lưu..." : savedNotes.length > 0 ? "Cập nhật ghi chú" : "Lưu ghi chú"}
                </Button>

                {false ? (
                <div className="rounded-lg border border-dashed border-[#D9E4F4] bg-[#F8FBFF] p-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                      <Highlighter className="h-3.5 w-3.5 text-yellow-600" />
                      Highlight
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 px-2 text-xs"
                      onClick={() => void handleCreateHighlight()}
                      disabled={!questionSqlId || !selectedTextForHighlight || isSavingHighlight}
                    >
                      {isSavingHighlight ? "Đang lưu" : "Lưu"}
                    </Button>
                  </div>
                  <p className="min-h-5 break-words text-xs text-muted-foreground">
                    {selectedTextForHighlight
                      ? `Đã chọn: "${selectedTextForHighlight}"`
                      : "Bôi chọn text trong câu hỏi rồi bấm Lưu."}
                  </p>
                </div>
                ) : null}

                {savedHighlights.length > 0 ? (
                  <div className="space-y-2">
                    {savedHighlights.slice(0, 4).map((highlight) => (
                      <div
                        key={highlight.id}
                        className="rounded-lg bg-yellow-50 px-3 py-2 text-xs text-yellow-900"
                      >
                        {highlight.selectedText}
                      </div>
                    ))}
                  </div>
                ) : null}

                {reviewToolError ? (
                  <p className="text-xs text-destructive">{reviewToolError}</p>
                ) : null}
              </CardContent>
            </Card>
            ) : null}

            <RunnerRightPanel
              activeTab={rightPanelTab}
              onTabChange={setRightPanelTab}
              labels={{
                notes: t("runner.notes"),
                aiTutor: t("runner.aiTutor"),
                notesForQuestion: t("runner.notesForQuestion"),
                saveNote: t("runner.saveNote"),
                saved: t("runner.saved"),
                notePlaceholder: t("runner.notePlaceholder"),
                noQuestionSelected: t("runner.noQuestionSelected"),
                askAiTutor: t("runner.askAiTutor"),
                typeYourQuestion: t("runner.typeYourQuestion"),
                loading: t("common.loading"),
              }}
              noteValue={questionNote}
              onNoteChange={(value) => {
                setQuestionNote(value);
                setNoteSaved(false);
              }}
              onSaveNote={() => void handleSaveNote()}
              noteSaving={isSavingNote}
              noteSaved={noteSaved}
              noteError={reviewToolError}
              noteDisabled={!questionSqlId}
              messages={tutorMessages}
              tutorValue={tutorInput}
              onTutorValueChange={setTutorInput}
              onTutorSend={() => void handleAskTutor()}
              tutorLoading={tutorLoading}
            />

            {false ? (
            <Card className="sticky top-20 rounded-xl border-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-foreground">{t("runner.questionList")}</CardTitle>
              </CardHeader>

              <CardContent>
                <ScrollArea className="h-64">
                  <div className="grid grid-cols-5 gap-2">
                    {questions.map((_, index) => {
                      const isAnswered = answers[index] !== undefined;
                      const isFlagged = flaggedQuestions.includes(index);
                      const isCurrent = index === currentQuestion;

                      return (
                        <button
                          key={index}
                          onClick={() => goToQuestion(index)}
                          className={`relative h-9 w-9 rounded-lg text-sm font-medium transition-colors ${
                            isCurrent
                              ? "bg-primary text-primary-foreground"
                              : isAnswered
                                ? "bg-accent text-foreground"
                                : "bg-muted text-muted-foreground hover:bg-accent"
                          }`}
                        >
                          {index + 1}
                          {isFlagged && (
                            <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-orange-500" />
                          )}
                        </button>
                      );
                    })}
                  </div>
                </ScrollArea>

                <div className="mt-4 space-y-2 border-t border-border pt-4 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">{t("runner.answered")}</span>
                    <span className="font-medium text-foreground">
                      {answeredCount} / {questions.length}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">{t("runner.flagged")}</span>
                    <span className="font-medium text-orange-500">
                      {flaggedQuestions.length}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
            ) : null}
          </div>
        </div>
      </div>

      <Dialog open={showSubmitDialog} onOpenChange={setShowSubmitDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-foreground">Nộp bài luyện tập?</DialogTitle>
            <DialogDescription className="text-muted-foreground">
              Bạn đã hoàn thành {answeredCount} / {questions.length} câu hỏi.
              {questions.length - answeredCount > 0 && (
                <span className="text-destructive">
                  {" "}
                  Còn {questions.length - answeredCount} câu chưa trả lời.
                </span>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Thời gian làm bài</span>
              <span className="font-medium text-foreground">{formatTime(timeElapsed)}</span>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSubmitDialog(false)}>
              Tiếp tục làm
            </Button>

            <Button asChild disabled={isSubmitting}>
              <Link
                to="/practice/summary"
                onClick={(event) => {
                  event.preventDefault();
                  if (isSubmitting) return;
                  void handleSubmitPractice();
                }}
              >
                <Send className="mr-2 h-4 w-4" />
                {t("runner.submit")}
              </Link>
            </Button>
          </DialogFooter>

          {submitError && <p className="text-sm text-destructive">{submitError}</p>}
        </DialogContent>
      </Dialog>
    </div>
  );
}
