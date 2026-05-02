"use client";

import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  BookMarked,
  BookOpen,
  CheckCircle,
  FileText,
  Highlighter,
  MessageSquare,
  Play,
  Search,
  Trash2,
  XCircle,
} from "lucide-react";

import { ProFeatureGuard } from "@/components/pro-feature-guard";
import { ChatPanel } from "@src/components/chat/ChatPanel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@src/services/apiClient";
import { chatService } from "@src/services/chatService";
import {
  reviewService,
  type ReviewFilter,
  type ReviewHighlight,
  type ReviewQueueQuestion,
} from "@src/services/reviewService";
import { useLanguage } from "@src/contexts/LanguageContext";
import type { TranslationKey } from "@src/i18n";

type ReviewChatMessage = {
  role: "user" | "assistant";
  content: string;
};

const filters: Array<{
  key: ReviewFilter;
  labelKey: TranslationKey;
  descriptionKey: TranslationKey;
}> = [
  { key: "all", labelKey: "review.all", descriptionKey: "review.subtitle" },
  { key: "wrong", labelKey: "review.wrong", descriptionKey: "review.reviewThisQuestion" },
  { key: "correct", labelKey: "review.correct", descriptionKey: "review.correctAnswer" },
  { key: "bookmarked", labelKey: "review.bookmarked", descriptionKey: "review.bookmarked" },
  { key: "notes", labelKey: "review.hasNote", descriptionKey: "review.personalNotebook" },
  { key: "highlights", labelKey: "review.hasHighlight", descriptionKey: "review.highlightText" },
  { key: "notebook", labelKey: "review.notebook", descriptionKey: "review.quickNotebook" },
];

function buildReviewPracticeUrl(question: ReviewQueueQuestion | null) {
  if (!question?.questionId) return "/practice?review=true";
  const params = new URLSearchParams({
    mode: "review",
    source: "review",
    question_ids: String(question.questionId),
    count: "1",
  });
  if (question.part) params.set("parts", String(question.part));
  return `/practice/runner?${params.toString()}`;
}

function optionLabel(index: number) {
  return String.fromCharCode(65 + index);
}

function renderOptionAnswer(label?: string | null, text?: string | null) {
  if (!label && !text) return "Chưa có dữ liệu";
  if (!label) return text || "";
  if (!text) return label;
  return `${label} — ${text}`;
}

function highlightText(text: string, highlights: ReviewHighlight[]) {
  if (!text || highlights.length === 0) return text;
  const terms = Array.from(
    new Set(
      highlights
        .map((highlight) => highlight.selectedText.trim())
        .filter((value) => value.length > 0),
    ),
  );
  if (terms.length === 0) return text;
  const escaped = terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const regex = new RegExp(`(${escaped.join("|")})`, "gi");
  return text.split(regex).map((part, index) => {
    const isMatch = terms.some((term) => term.toLowerCase() === part.toLowerCase());
    return isMatch ? (
      <mark key={`${part}-${index}`} className="rounded bg-yellow-200 px-0.5 text-foreground">
        {part}
      </mark>
    ) : (
      part
    );
  });
}

export function ReviewPage() {
  const { t } = useLanguage();
  const [activeFilter, setActiveFilter] = useState<ReviewFilter>("all");
  const [items, setItems] = useState<ReviewQueueQuestion[]>([]);
  const [selectedQuestion, setSelectedQuestion] = useState<ReviewQueueQuestion | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [noteDraft, setNoteDraft] = useState("");
  const [isSavingNote, setIsSavingNote] = useState(false);
  const [selectedTextForHighlight, setSelectedTextForHighlight] = useState("");
  const [isSavingHighlight, setIsSavingHighlight] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [messages, setMessages] = useState<ReviewChatMessage[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [chatConversationId, setChatConversationId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadItems() {
      setIsLoading(true);
      setReviewError(null);
      try {
        const data = await reviewService.getReviewItems(activeFilter, 80);
        if (cancelled) return;
        setItems(data);
        setSelectedQuestion((current) => {
          const stillExists = current && data.find((item) => item.questionId === current.questionId);
          return stillExists || data[0] || null;
        });
      } catch (error) {
        if (!cancelled) {
          setItems([]);
          setSelectedQuestion(null);
          setReviewError(error instanceof Error ? error.message : "Không tải được dữ liệu ôn tập.");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void loadItems();

    return () => {
      cancelled = true;
    };
  }, [activeFilter]);

  useEffect(() => {
    setMessages([]);
    setChatInput("");
    setChatConversationId(null);
    setSelectedTextForHighlight("");
    setNoteDraft(selectedQuestion?.notes[0]?.noteText || "");
  }, [selectedQuestion?.questionId]);

  const filteredItems = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return items;
    return items.filter((item) =>
      [
        item.question,
        item.correctAnswer,
        item.explanation,
        item.optionAnalysis || "",
        item.vocabularyNotes || "",
        item.skill,
        item.subskill,
        String(item.questionId),
        String(item.part),
      ]
        .join(" ")
        .toLowerCase()
        .includes(query),
    );
  }, [items, searchQuery]);

  const stats = useMemo(() => {
    const wrong = items.filter((item) => item.isCorrect === false).length;
    const correct = items.filter((item) => item.isCorrect === true).length;
    const bookmarked = items.filter((item) => item.bookmarked).length;
    const notes = items.filter((item) => item.notes.length > 0).length;
    const highlights = items.filter((item) => item.highlights.length > 0).length;
    const total = Math.max(correct + wrong, items.length);
    const accuracy = total > 0 ? Math.round((correct * 100) / total) : 0;
    return { wrong, correct, bookmarked, notes, highlights, total, accuracy };
  }, [items]);

  const refreshSelectedQuestion = async (questionId: number) => {
    const data = await reviewService.getReviewItems(activeFilter, 80);
    setItems(data);
    const updated = data.find((item) => item.questionId === questionId) || selectedQuestion;
    setSelectedQuestion(updated || null);
    return updated || null;
  };

  const handleTextSelect = () => {
    const selectedText = window.getSelection()?.toString().trim() || "";
    if (selectedText) setSelectedTextForHighlight(selectedText.slice(0, 2000));
  };

  const handleSaveNote = async () => {
    if (!selectedQuestion?.questionId || !noteDraft.trim()) return;
    setIsSavingNote(true);
    try {
      await reviewService.saveNote(
        selectedQuestion.questionId,
        noteDraft.trim(),
        selectedQuestion.sourceAttemptId,
      );
      await refreshSelectedQuestion(selectedQuestion.questionId);
    } finally {
      setIsSavingNote(false);
    }
  };

  const handleCreateHighlight = async () => {
    if (!selectedQuestion?.questionId || !selectedTextForHighlight.trim()) return;
    setIsSavingHighlight(true);
    try {
      await reviewService.createHighlight({
        question_id: selectedQuestion.questionId,
        attempt_id: selectedQuestion.sourceAttemptId,
        target_type: "question_text",
        selected_text: selectedTextForHighlight.trim(),
        color: "yellow",
      });
      window.getSelection()?.removeAllRanges();
      setSelectedTextForHighlight("");
      await refreshSelectedQuestion(selectedQuestion.questionId);
    } finally {
      setIsSavingHighlight(false);
    }
  };

  const handleDeleteHighlight = async (highlightId: number) => {
    if (!selectedQuestion) return;
    await reviewService.deleteHighlight(highlightId);
    await refreshSelectedQuestion(selectedQuestion.questionId);
  };

  const handleToggleBookmark = async () => {
    if (!selectedQuestion?.questionId) return;
    await reviewService.toggleBookmark(selectedQuestion.questionId, selectedQuestion.sourceAttemptId);
    await refreshSelectedQuestion(selectedQuestion.questionId);
  };

  const sendMessage = async (messageOverride?: string) => {
    if (!selectedQuestion || isChatLoading) return;
    const userMessage = (messageOverride || chatInput).trim();
    if (!userMessage) return;

    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setChatInput("");
    setIsChatLoading(true);

    try {
      const response = await chatService.sendDetailed({
        message: userMessage,
        question_id: selectedQuestion.questionId,
        attempt_id: selectedQuestion.sourceAttemptId || null,
        context_type: "review",
        conversation_id: chatConversationId,
        questionText: selectedQuestion.question,
        question_text: selectedQuestion.question,
        passageText: selectedQuestion.passageText || null,
        passage_text: selectedQuestion.passageText || null,
        options: selectedQuestion.optionRows.map((option) => ({
          label: option.optionLabel,
          text: option.optionTextEn,
          isCorrect: option.isCorrect,
        })),
        selected_option_label: selectedQuestion.userAnswerLabel || null,
        selectedAnswer: selectedQuestion.userAnswer,
        correctAnswer: selectedQuestion.correctAnswer,
        explanation: selectedQuestion.explanation,
        currentQuestion: {
          id: selectedQuestion.questionId,
          questionId: selectedQuestion.questionId,
          questionNumber: selectedQuestion.questionNumber,
          part: selectedQuestion.part,
          questionText: selectedQuestion.question,
          passageText: selectedQuestion.passageText,
          options: selectedQuestion.optionRows,
          selectedAnswer: selectedQuestion.userAnswer,
          correctAnswer: selectedQuestion.correctAnswer,
          explanation: selectedQuestion.explanation,
        },
      });

      if (typeof response.conversation_id === "number") {
        setChatConversationId(response.conversation_id);
      }

      setMessages((prev) => [
        ...prev,
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
          ? "AI Tutor là tính năng Pro. Vui lòng đăng nhập tài khoản Pro để hỏi theo câu ôn tập."
          : error instanceof Error
            ? `Không gọi được AI Tutor: ${error.message}`
            : "Không gọi được AI Tutor.";
      setMessages((prev) => [...prev, { role: "assistant", content: message }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const selectedCorrectText =
    selectedQuestion?.optionRows.find(
      (option) => option.optionLabel.toUpperCase() === (selectedQuestion.correctAnswerLabel || "").toUpperCase(),
    )?.optionTextEn || selectedQuestion?.correctAnswer;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t("review.title")}</h1>
          <p className="mt-1 text-muted-foreground">
            {t("review.subtitle")}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder={t("review.searchPlaceholder")}
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              className="w-72 pl-9"
            />
          </div>
          <Button asChild className="gap-2">
            <Link to={buildReviewPracticeUrl(selectedQuestion)}>
              <Play className="h-4 w-4" />
              {t("review.practiceNow")}
            </Link>
          </Button>
        </div>
      </div>

      {isLoading || reviewError ? (
        <Card className="border-[#E7EEF9] bg-[#F8FBFF]">
          <CardContent className="py-4 text-sm text-muted-foreground">
            {isLoading ? "Đang tải dữ liệu ôn tập..." : `Không tải được dữ liệu: ${reviewError}`}
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-5">
        <Card className="bg-gradient-to-br from-primary/10 to-transparent">
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Câu sai</p>
            <p className="mt-1 text-2xl font-bold text-red-600">{stats.wrong}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Đã đánh dấu</p>
            <p className="mt-1 text-2xl font-bold text-yellow-600">{stats.bookmarked}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Có ghi chú</p>
            <p className="mt-1 text-2xl font-bold text-primary">{stats.notes}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Có highlight</p>
            <p className="mt-1 text-2xl font-bold text-amber-600">{stats.highlights}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground">Độ ổn định</p>
            <div className="mt-2 flex items-center gap-3">
              <Progress value={stats.accuracy} className="h-2" />
              <span className="text-sm font-semibold">{stats.accuracy}%</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid items-stretch gap-4 lg:grid-cols-[260px_minmax(0,1fr)_320px] lg:grid-rows-[600px_auto]">
        <div className="order-3 min-w-0 space-y-4 lg:contents">
          {false ? (
          <Card className="lg:h-full lg:overflow-hidden">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Bộ lọc</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {filters.map((filter) => (
                <button
                  key={filter.key}
                  type="button"
                  onClick={() => setActiveFilter(filter.key)}
                  className={`w-full rounded-xl border px-3 py-2.5 text-left transition ${
                    activeFilter === filter.key
                      ? "border-primary bg-primary/5 text-primary"
                      : "border-border hover:border-primary/50"
                  }`}
                >
                  <p className="text-sm font-semibold">{t(filter.labelKey)}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{t(filter.descriptionKey)}</p>
                </button>
              ))}
            </CardContent>
          </Card>
          ) : null}

          <Card className="lg:col-start-1 lg:row-start-1 lg:h-full lg:min-h-0 lg:overflow-hidden">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">{t("review.questionList")}</CardTitle>
              <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
                {filters.map((filter) => (
                  <button
                    key={filter.key}
                    type="button"
                    onClick={() => setActiveFilter(filter.key)}
                    className={`shrink-0 rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                      activeFilter === filter.key
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border bg-white text-muted-foreground hover:border-primary/50"
                    }`}
                  >
                    {t(filter.labelKey)}
                  </button>
                ))}
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[360px] pr-3 lg:h-[440px]">
                <div className="space-y-2">
                  {filteredItems.length > 0 ? (
                    filteredItems.map((item) => (
                      <button
                        key={`${item.questionId}-${item.sourceAttemptId || "review"}`}
                        type="button"
                        onClick={() => setSelectedQuestion(item)}
                        className={`w-full rounded-xl border p-3 text-left transition ${
                          selectedQuestion?.questionId === item.questionId
                            ? "border-primary bg-primary/5"
                            : "border-border hover:border-primary/50"
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`rounded-full p-1.5 ${item.isCorrect ? "bg-green-100" : "bg-red-100"}`}>
                            {item.isCorrect ? (
                              <CheckCircle className="h-4 w-4 text-green-600" />
                            ) : (
                              <XCircle className="h-4 w-4 text-red-600" />
                            )}
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium">
                              Câu {item.questionNumber || item.questionId}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              Part {item.part || "?"} · {item.skill}
                            </p>
                            <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                              {item.question}
                            </p>
                          </div>
                        </div>
                      </button>
                    ))
                  ) : (
                    <div className="rounded-xl border border-dashed p-4 text-sm text-muted-foreground">
                      {t("review.noReviewData")}
                    </div>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          <Card className="lg:col-start-1 lg:row-start-2">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <BookMarked className="h-4 w-4 text-primary" />
                {t("review.quickNotebook")}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-3 gap-2 text-center">
                <button
                  type="button"
                  onClick={() => setActiveFilter("notes")}
                  className="rounded-xl border bg-[#F8FBFF] p-2 transition hover:border-primary/50"
                >
                  <p className="text-lg font-bold text-primary">{stats.notes}</p>
                  <p className="text-[11px] text-muted-foreground">{t("review.hasNote")}</p>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveFilter("highlights")}
                  className="rounded-xl border bg-yellow-50 p-2 transition hover:border-primary/50"
                >
                  <p className="text-lg font-bold text-amber-600">{stats.highlights}</p>
                  <p className="text-[11px] text-muted-foreground">{t("review.hasHighlight")}</p>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveFilter("bookmarked")}
                  className="rounded-xl border bg-white p-2 transition hover:border-primary/50"
                >
                  <p className="text-lg font-bold text-yellow-600">{stats.bookmarked}</p>
                  <p className="text-[11px] text-muted-foreground">{t("review.bookmarked")}</p>
                </button>
              </div>
              <Button
                type="button"
                variant="outline"
                className="w-full"
                onClick={() => setActiveFilter("notebook")}
              >
                {t("review.notebook")}
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="order-1 min-w-0 space-y-4 lg:contents">
          {selectedQuestion ? (
            <>
              <Card className="border-[#DCE7F7] lg:col-start-2 lg:row-start-1 lg:h-full lg:min-h-0 lg:overflow-hidden">
                <CardHeader className="pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">Part {selectedQuestion.part || "?"}</Badge>
                      <Badge variant="secondary">Câu {selectedQuestion.questionNumber || selectedQuestion.questionId}</Badge>
                      {selectedQuestion.bookmarked ? (
                        <Badge className="bg-yellow-500 text-white">Đã đánh dấu</Badge>
                      ) : null}
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Button size="sm" variant="outline" onClick={() => void handleToggleBookmark()}>
                        <BookMarked className="mr-1 h-4 w-4" />
                        {selectedQuestion.bookmarked ? "Bỏ đánh dấu" : "Đánh dấu"}
                      </Button>
                      <Button size="sm" asChild>
                        <Link to={buildReviewPracticeUrl(selectedQuestion)}>
                          <Play className="mr-1 h-4 w-4" />
                          Luyện lại câu này
                        </Link>
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-5 lg:max-h-[500px] lg:overflow-y-auto" onMouseUp={handleTextSelect}>
                  {selectedQuestion.passageText ? (
                    <div className="rounded-xl border border-[#DFE8F5] bg-[#F8FBFF] p-4">
                      <p className="whitespace-pre-line text-sm leading-relaxed text-foreground">
                        {highlightText(selectedQuestion.passageText, selectedQuestion.highlights)}
                      </p>
                    </div>
                  ) : null}

                  <div>
                    <p className="text-lg font-semibold leading-relaxed text-foreground">
                      {highlightText(selectedQuestion.question, selectedQuestion.highlights)}
                    </p>
                  </div>

                  <div className="space-y-3">
                    {selectedQuestion.optionRows.length > 0 ? (
                      selectedQuestion.optionRows.map((option, index) => {
                        const label = option.optionLabel || optionLabel(index);
                        const isUser = selectedQuestion.userAnswerLabel?.toUpperCase() === label.toUpperCase();
                        const isCorrect = option.isCorrect || selectedQuestion.correctAnswerLabel?.toUpperCase() === label.toUpperCase();
                        return (
                          <div
                            key={`${label}-${index}`}
                            className={`rounded-xl border p-4 ${
                              isCorrect
                                ? "border-green-300 bg-green-50"
                                : isUser
                                  ? "border-red-300 bg-red-50"
                                  : "border-border"
                            }`}
                          >
                            <div className="flex items-start gap-3">
                              <div
                                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                                  isCorrect
                                    ? "bg-green-600 text-white"
                                    : isUser
                                      ? "bg-red-600 text-white"
                                      : "bg-muted text-foreground"
                                }`}
                              >
                                {label}
                              </div>
                              <p className="flex-1 text-sm leading-relaxed">
                                {highlightText(option.optionTextEn, selectedQuestion.highlights)}
                              </p>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <div className="rounded-xl border border-dashed p-4 text-sm text-muted-foreground">
                        SQL chưa có lựa chọn A/B/C/D cho câu này.
                      </div>
                    )}
                  </div>

                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="rounded-xl border border-red-100 bg-red-50 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-red-700">Bạn đã chọn</p>
                      <p className="mt-1 text-sm text-foreground">
                        {renderOptionAnswer(selectedQuestion.userAnswerLabel, selectedQuestion.userAnswer)}
                      </p>
                    </div>
                    <div className="rounded-xl border border-green-100 bg-green-50 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-green-700">Đáp án đúng</p>
                      <p className="mt-1 text-sm text-foreground">
                        {renderOptionAnswer(selectedQuestion.correctAnswerLabel, selectedCorrectText)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="lg:col-start-2 lg:row-start-2">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <BookOpen className="h-4 w-4 text-primary" />
                    Notebook cá nhân
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Textarea
                      value={noteDraft}
                      onChange={(event) => setNoteDraft(event.target.value)}
                      placeholder="Viết ghi chú của bạn cho câu này..."
                      className="min-h-[110px]"
                    />
                    <Button onClick={() => void handleSaveNote()} disabled={!noteDraft.trim() || isSavingNote}>
                      {isSavingNote ? "Đang lưu..." : selectedQuestion.notes.length > 0 ? "Cập nhật ghi chú" : "Lưu ghi chú"}
                    </Button>
                  </div>

                  {selectedQuestion.notes.length > 0 ? (
                    <div className="space-y-2">
                      {selectedQuestion.notes.map((note) => (
                        <div key={note.id} className="rounded-xl border bg-[#F8FBFF] p-3">
                          <p className="whitespace-pre-line text-sm">{note.noteText}</p>
                        </div>
                      ))}
                    </div>
                  ) : null}

                  <div className="hidden rounded-xl border border-dashed bg-yellow-50/60 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2 text-sm font-semibold">
                        <Highlighter className="h-4 w-4 text-yellow-700" />
                        Highlight text
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void handleCreateHighlight()}
                        disabled={!selectedTextForHighlight || isSavingHighlight}
                      >
                        {isSavingHighlight ? "Đang lưu..." : "Lưu highlight"}
                      </Button>
                    </div>
                    <p className="mt-2 break-words text-xs text-muted-foreground">
                      {selectedTextForHighlight
                        ? `Đã chọn: "${selectedTextForHighlight}"`
                        : "Bôi chọn text trong câu hỏi, passage hoặc option để lưu highlight."}
                    </p>
                  </div>

                  {false && selectedQuestion.highlights.length > 0 ? (
                    <div className="space-y-2">
                      {selectedQuestion.highlights.map((highlight) => (
                        <div
                          key={highlight.id}
                          className="flex items-start justify-between gap-3 rounded-xl border bg-yellow-50 p-3"
                        >
                          <div>
                            <p className="text-sm font-medium text-yellow-950">{highlight.selectedText}</p>
                            {highlight.noteText ? (
                              <p className="mt-1 text-xs text-muted-foreground">{highlight.noteText}</p>
                            ) : null}
                          </div>
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-8 w-8 shrink-0"
                            onClick={() => void handleDeleteHighlight(highlight.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            </>
          ) : (
            <Card className="border-dashed lg:col-start-2 lg:row-start-1">
              <CardContent className="flex min-h-[420px] flex-col items-center justify-center text-center">
                <FileText className="mb-3 h-10 w-10 text-muted-foreground" />
                <p className="font-semibold">Chưa có dữ liệu ôn tập.</p>
                <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                  Hãy làm bài luyện, ghi chú, highlight hoặc đánh dấu câu để xem lại ở đây.
                </p>
                <Button asChild className="mt-4">
                  <Link to="/practice">{t("review.practiceNow")}</Link>
                </Button>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="order-5 min-w-0 space-y-4 lg:contents">
          {false ? (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <BookMarked className="h-4 w-4 text-primary" />
                Sổ tay nhanh
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[260px] pr-3">
                <div className="space-y-3">
                  {items
                    .filter((item) => item.notes.length > 0 || item.highlights.length > 0 || item.bookmarked)
                    .slice(0, 8)
                    .map((item) => (
                      <button
                        key={`notebook-${item.questionId}`}
                        type="button"
                        onClick={() => setSelectedQuestion(item)}
                        className="w-full rounded-xl border p-3 text-left transition hover:border-primary/50"
                      >
                        <div className="flex items-start gap-2">
                          <MessageSquare className="mt-0.5 h-4 w-4 text-primary" />
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold">
                              Câu {item.questionNumber || item.questionId}
                            </p>
                            <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                              {item.notes[0]?.noteText || item.highlights[0]?.selectedText || item.question}
                            </p>
                          </div>
                        </div>
                      </button>
                    ))}
                  {items.filter((item) => item.notes.length > 0 || item.highlights.length > 0 || item.bookmarked).length === 0 ? (
                    <p className="rounded-xl border border-dashed p-3 text-sm text-muted-foreground">
                      Chưa có ghi chú, highlight hoặc bookmark.
                    </p>
                  ) : null}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
          ) : null}

          <div className="lg:col-start-3 lg:row-start-1 lg:h-full lg:min-h-0 lg:[&>*]:h-full">
          <ProFeatureGuard
            feature="aiChatUnlimited"
            compact
            title="AI Tutor trong Review là tính năng Pro"
            description="Free vẫn xem review và đáp án. Nâng cấp Pro để hỏi AI Tutor theo từng lỗi sai."
          >
            <Card className="h-full rounded-xl border-[#CFE0FF] bg-[#F7FAFF] shadow-sm">
              <CardContent className="h-full p-4">
                <ChatPanel
                  title="AI Tutor Review"
                  description="Hỏi theo đúng câu đang chọn trong Review."
                  messages={messages}
                  value={chatInput}
                  onValueChange={setChatInput}
                  onSend={() => void sendMessage()}
                  loading={isChatLoading}
                  placeholder="Hỏi AI Tutor về câu này..."
                  className="h-full"
                  composerMode="textarea"
                />
              </CardContent>
            </Card>
          </ProFeatureGuard>
          </div>

          <Card className="lg:col-start-3 lg:row-start-2">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Highlighter className="h-4 w-4 text-yellow-700" />
                Highlight text
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="rounded-xl border border-dashed bg-yellow-50/60 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-foreground">Highlight text</p>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void handleCreateHighlight()}
                    disabled={!selectedQuestion || !selectedTextForHighlight || isSavingHighlight}
                  >
                    {isSavingHighlight ? t("common.loading") : t("runner.saveHighlight")}
                  </Button>
                </div>
                <p className="mt-2 break-words text-xs text-muted-foreground">
                  {selectedTextForHighlight
                    ? t("runner.highlightSelected", { text: selectedTextForHighlight })
                    : t("runner.selectToHighlight")}
                </p>
              </div>

              {selectedQuestion?.highlights.length ? (
                <ScrollArea className="max-h-[260px] pr-3">
                  <div className="space-y-2">
                    {selectedQuestion.highlights.map((highlight) => (
                      <div
                        key={highlight.id}
                        className="flex items-start justify-between gap-3 rounded-xl border bg-yellow-50 p-3"
                      >
                        <div className="min-w-0">
                          <p className="break-words text-sm font-medium text-yellow-950">{highlight.selectedText}</p>
                          {highlight.noteText ? (
                            <p className="mt-1 text-xs text-muted-foreground">{highlight.noteText}</p>
                          ) : null}
                        </div>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8 shrink-0"
                          onClick={() => void handleDeleteHighlight(highlight.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              ) : (
                <p className="rounded-xl border border-dashed p-3 text-sm text-muted-foreground">
                  {t("review.noNotebook")}
                </p>
              )}
            </CardContent>
          </Card>

          <Card className="hidden">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Highlighter className="h-4 w-4 text-yellow-700" />
                Highlight text
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="rounded-xl border border-dashed bg-yellow-50/60 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-foreground">Highlight text</p>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void handleCreateHighlight()}
                    disabled={!selectedQuestion || !selectedTextForHighlight || isSavingHighlight}
                  >
                    {isSavingHighlight ? "Äang lÆ°u..." : "LÆ°u highlight"}
                  </Button>
                </div>
                <p className="mt-2 break-words text-xs text-muted-foreground">
                  {selectedTextForHighlight
                    ? `ÄÃ£ chá»n: "${selectedTextForHighlight}"`
                    : "BÃ´i chá»n text trong cÃ¢u há»i, passage hoáº·c option Ä‘á»ƒ lÆ°u highlight."}
                </p>
              </div>

              {selectedQuestion?.highlights.length ? (
                <ScrollArea className="max-h-[260px] pr-3">
                  <div className="space-y-2">
                    {selectedQuestion.highlights.map((highlight) => (
                      <div
                        key={highlight.id}
                        className="flex items-start justify-between gap-3 rounded-xl border bg-yellow-50 p-3"
                      >
                        <div className="min-w-0">
                          <p className="break-words text-sm font-medium text-yellow-950">{highlight.selectedText}</p>
                          {highlight.noteText ? (
                            <p className="mt-1 text-xs text-muted-foreground">{highlight.noteText}</p>
                          ) : null}
                        </div>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8 shrink-0"
                          onClick={() => void handleDeleteHighlight(highlight.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              ) : (
                <p className="rounded-xl border border-dashed p-3 text-sm text-muted-foreground">
                  ChÆ°a cÃ³ highlight cho cÃ¢u nÃ y.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
