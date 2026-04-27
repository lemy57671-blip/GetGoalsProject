"use client";

import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ProFeatureGuard } from "@/components/pro-feature-guard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  ChevronRight,
  Highlighter,
  BookMarked,
  MessageSquare,
  Languages,
  Sparkles,
  Search,
  Filter,
  Volume2,
  BookOpen,
  Play,
  Plus,
  FileText,
  X,
  Send,
} from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

import {
  initialAiMessages,
  notebookItems,
  type ReviewChatMessage,
} from "@src/data/review";
import {
  reviewService,
  ReviewQueueQuestion,
  ReviewSummaryView,
} from "@src/services/reviewService";

const emptyReviewQuestion: ReviewQueueQuestion = {
  id: 0,
  queueId: 0,
  questionId: 0,
  question: "No review items are available yet.",
  options: [],
  userAnswer: "",
  correctAnswer: "",
  isCorrect: true,
  explanation:
    "Complete a practice attempt with wrong answers to populate the review queue.",
  skill: "TOEIC review",
  subskill: "practice",
  part: 0,
  difficulty: "medium",
  status: "empty",
};

function buildReviewPracticeUrl(question: ReviewQueueQuestion) {
  const part = question.part >= 1 && question.part <= 7 ? question.part : 5;
  const params = new URLSearchParams({
    parts: String(part),
    count: "15",
    difficulty: "mixed",
    mode: "review-focus",
    reviewItemId: String(question.queueId || question.id || 0),
  });

  if (question.skill) {
    params.set("skill", question.skill);
  }

  if (question.subskill) {
    params.set("subskill", question.subskill);
  }

  return `/practice/runner?${params.toString()}`;
}

export function ReviewPage() {
  const [reviewSummary, setReviewSummary] = useState<ReviewSummaryView | null>(null);
  const [selectedQuestionState, setSelectedQuestion] =
    useState<ReviewQueueQuestion | null>(null);
  const [isLoadingReview, setIsLoadingReview] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isMarkingReviewed, setIsMarkingReviewed] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [showToolbar, setShowToolbar] = useState(false);
  const [toolbarPosition, setToolbarPosition] = useState({ x: 0, y: 0 });
  const [searchQuery, setSearchQuery] = useState("");
  const [newNote, setNewNote] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [messages, setMessages] = useState<ReviewChatMessage[]>(initialAiMessages.slice());

  const reviewQuestions = reviewSummary?.questions || [];
  const reviewSkillBreakdown = reviewSummary?.skillBreakdown || [];
  const reviewPartBreakdown = reviewSummary?.partBreakdown || [];
  const selectedQuestion =
    selectedQuestionState || reviewQuestions[0] || emptyReviewQuestion;
  const correctCount = reviewSummary?.reviewedCount || 0;
  const incorrectCount = reviewSummary?.pendingCount || 0;
  const totalReviewCount = correctCount + incorrectCount;
  const accuracy =
    totalReviewCount > 0 ? Math.round((correctCount / totalReviewCount) * 100) : 0;

  useEffect(() => {
    let cancelled = false;

    async function loadReview() {
      setIsLoadingReview(true);
      setReviewError(null);

      try {
        const summary = await reviewService.getSummary();

        if (cancelled) return;

        setReviewSummary(summary);
        setSelectedQuestion(summary.questions[0] || null);
      } catch (error) {
        if (!cancelled) {
          setReviewError(
            error instanceof Error
              ? error.message
              : "Could not load review data from FastAPI.",
          );
          setReviewSummary(null);
          setSelectedQuestion(null);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingReview(false);
        }
      }
    }

    loadReview();

    return () => {
      cancelled = true;
    };
  }, []);

  const filteredQuestions = useMemo(() => {
    if (!searchQuery.trim()) return reviewQuestions;
    const q = searchQuery.toLowerCase();
    return reviewQuestions.filter(
      (item) =>
        item.question.toLowerCase().includes(q) ||
        item.skill.toLowerCase().includes(q) ||
        item.subskill.toLowerCase().includes(q) ||
        String(item.part).includes(q) ||
        String(item.id).includes(q),
    );
  }, [searchQuery]);

  const handleTextSelect = () => {
    const selection = window.getSelection();
    if (selection && selection.toString().trim()) {
      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      setToolbarPosition({
        x: rect.left + rect.width / 2,
        y: rect.top - 10,
      });
      setShowToolbar(true);
    } else {
      setShowToolbar(false);
    }
  };

  const sendMessage = () => {
    if (!chatInput.trim()) return;

    const userMessage = chatInput.trim();
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setChatInput("");

    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            selectedQuestion.id === 1
              ? "Ở câu này, chỗ trống đứng trước tính từ 'successful', nên cần một trạng từ để bổ nghĩa. 'Remarkably' là trạng từ, còn 'remarkable' là tính từ nên không phù hợp."
              : "Mình đã phân tích thêm cho câu này. Bạn có thể hỏi tiếp về từ vựng, ngữ pháp hoặc mẹo tránh bẫy dạng câu tương tự.",
        },
      ]);
    }, 800);
  };

  const askQuickPrompt = (prompt: string) => {
    setMessages((prev) => [...prev, { role: "user", content: prompt }]);

    let response =
      "Mình đã phân tích thêm cho câu này. Bạn có thể tiếp tục hỏi sâu hơn về ngữ pháp, từ vựng hoặc cách tránh bẫy.";

    if (prompt.includes("Giải thích")) {
      response = selectedQuestion.explanation;
    } else if (prompt.includes("Vì sao đáp án đúng")) {
      response =
        "Đáp án đúng vì nó phù hợp với chức năng ngữ pháp của vị trí chỗ trống trong câu và đúng ngữ nghĩa của toàn câu.";
    } else if (prompt.includes("Phân tích đáp án sai")) {
      response =
        "Các đáp án sai thường rơi vào bẫy sai loại từ, sai hòa hợp chủ ngữ - động từ, hoặc sai nghĩa trong ngữ cảnh.";
    } else if (prompt.includes("Dịch câu hỏi")) {
      response = "Chiến lược marketing mới của công ty đã _______ thành công trong việc thu hút khách hàng trẻ hơn.";
    } else if (prompt.includes("Mẹo làm dạng này")) {
      response =
        "Với dạng câu này, hãy nhìn vào từ đứng trước và sau chỗ trống để xác định loại từ cần điền: danh từ, động từ, tính từ hay trạng từ.";
    }

    setTimeout(() => {
      setMessages((prev) => [...prev, { role: "assistant", content: response }]);
    }, 500);
  };

  const refreshReviewSummary = async () => {
    const summary = await reviewService.getSummary();
    setReviewSummary(summary);
    return summary;
  };

  const handleSelectQuestion = async (q: ReviewQueueQuestion) => {
    setSelectedQuestion(q);
    setDetailError(null);
    setIsLoadingDetail(true);

    try {
      const detail = await reviewService.getItem(q.queueId);
      setSelectedQuestion(detail);
    } catch (error) {
      setDetailError(
        error instanceof Error
          ? error.message
          : "Could not load this review item detail.",
      );
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleMarkReviewed = async () => {
    if (!selectedQuestion.queueId || selectedQuestion.status === "empty") return;
    setIsMarkingReviewed(true);
    setDetailError(null);

    try {
      const updated = await reviewService.markReviewed(selectedQuestion.queueId);
      setSelectedQuestion(updated);
      await refreshReviewSummary();
    } catch (error) {
      setDetailError(
        error instanceof Error
          ? error.message
          : "Could not mark this item as reviewed.",
      );
    } finally {
      setIsMarkingReviewed(false);
    }
  };

  const renderQuestionButton = (q: ReviewQueueQuestion) => (
    <button
      key={q.id}
      onClick={() => void handleSelectQuestion(q)}
      className={`w-full rounded-xl border p-3 text-left transition-all ${
        selectedQuestion.id === q.id ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
      }`}
    >
      <div className="flex items-center gap-3">
        <div className={`rounded-full p-1.5 ${q.isCorrect ? "bg-green-100" : "bg-red-100"}`}>
          {q.isCorrect ? (
            <CheckCircle className="h-4 w-4 text-green-600" />
          ) : (
            <XCircle className="h-4 w-4 text-red-600" />
          )}
        </div>

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">Câu {q.id}</p>
          <p className="text-xs text-muted-foreground">
            Part {q.part} - {q.skill}
          </p>
        </div>

        <ChevronRight className="h-4 w-4 text-muted-foreground" />
      </div>
    </button>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Ôn tập</h1>
          <p className="mt-1 text-muted-foreground">Xem lại và học từ những lỗi sai</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Tìm câu hỏi..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-64 pl-9"
            />
          </div>

          <Button variant="outline" className="gap-2">
            <Filter className="h-4 w-4" />
            Lọc
          </Button>

          <Sheet>
            <SheetTrigger asChild>
              <Button className="gap-2">
                <BookMarked className="h-4 w-4" />
                Sổ tay từ mới
              </Button>
            </SheetTrigger>

            <SheetContent className="w-[450px] sm:max-w-[450px]">
              <SheetHeader>
                <SheetTitle>Sổ tay từ mới</SheetTitle>
                <SheetDescription>Từ vựng và cụm từ bạn đã lưu</SheetDescription>
              </SheetHeader>

              <div className="mt-6 space-y-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input placeholder="Tìm từ..." className="pl-9" />
                </div>

                <div className="space-y-3">
                  {notebookItems.map((item) => (
                    <Card key={item.id} className="cursor-pointer transition-shadow hover:shadow-md">
                      <CardContent className="space-y-2 p-4">
                        <div className="flex items-start justify-between">
                          <div>
                            <h4 className="font-semibold text-primary">{item.word}</h4>
                            <p className="text-sm text-muted-foreground">{item.meaning}</p>
                          </div>

                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <Volume2 className="h-4 w-4" />
                          </Button>
                        </div>

                        <p className="text-sm italic text-muted-foreground">{`"${item.example}"`}</p>

                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-1">
                            {item.tags.map((tag) => (
                              <Badge key={tag} variant="secondary" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                          <span className="text-xs text-muted-foreground">{item.source}</span>
                        </div>

                        {item.note ? <p className="rounded bg-muted p-2 text-xs text-muted-foreground">{item.note}</p> : null}
                      </CardContent>
                    </Card>
                  ))}
                </div>

                <Button variant="outline" className="w-full gap-2">
                  <Plus className="h-4 w-4" />
                  Thêm từ mới
                </Button>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>

      {(isLoadingReview || reviewError || reviewQuestions.length === 0) && (
        <Card className="border-[#E7EEF9] bg-[#F8FBFF]">
          <CardContent className="py-4 text-sm text-muted-foreground">
            {isLoadingReview
              ? "Loading review queue from FastAPI..."
              : reviewError
                ? `Could not load review data: ${reviewError}`
                : "No review items yet. Submit a practice attempt with incorrect answers to populate this queue."}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-4">
        <Card className="bg-gradient-to-br from-primary/10 to-transparent">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Review done</p>
                <p className="text-3xl font-bold text-primary">{accuracy}%</p>
              </div>

              <div className="relative h-16 w-16">
                <svg className="-rotate-90 transform" viewBox="0 0 36 36">
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    className="text-muted"
                  />
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    strokeDasharray={`${accuracy}, 100`}
                    className="text-primary"
                  />
                </svg>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="rounded-xl bg-green-100 p-3">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Reviewed</p>
                <p className="text-2xl font-bold text-green-600">{correctCount}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="rounded-xl bg-red-100 p-3">
                <XCircle className="h-6 w-6 text-red-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Pending</p>
                <p className="text-2xl font-bold text-red-600">{incorrectCount}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="rounded-xl bg-yellow-100 p-3">
                <AlertCircle className="h-6 w-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Queued</p>
                <p className="text-2xl font-bold text-yellow-600">{reviewQuestions.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Theo kỹ năng</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {reviewSkillBreakdown.map((skill) => (
              <div key={skill.name} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>{skill.name}</span>
                  <span className="text-muted-foreground">
                    {skill.correct}/{skill.total}
                  </span>
                </div>
                <Progress value={(skill.correct / skill.total) * 100} className="h-2" />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Theo Part</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {reviewPartBreakdown.map((part) => (
              <div key={part.name} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>{part.name}</span>
                  <span className="text-muted-foreground">
                    {part.correct}/{part.total}
                  </span>
                </div>
                <Progress value={(part.correct / part.total) * 100} className="h-2" />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card className="border-primary/20 bg-primary/5">
        <CardContent className="flex flex-col gap-4 py-4 sm:flex-row sm:items-center">
          <div className="rounded-xl bg-primary/10 p-3">
            <Sparkles className="h-6 w-6 text-primary" />
          </div>

          <div className="flex-1">
            <h3 className="font-semibold">Gợi ý tiếp theo</h3>
            <p className="text-sm text-muted-foreground">
              Bạn đang yếu ở phần Grammar - Adverbs. Hãy luyện thêm 15 câu để cải thiện.
            </p>
          </div>

          <Button className="gap-2">
            <Play className="h-4 w-4" />
            Luyện ngay
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-12">
        <Card className="xl:col-span-3">
          <CardHeader>
            <CardTitle className="text-base">Danh sách câu hỏi</CardTitle>
          </CardHeader>

          <CardContent className="space-y-2">
            <Tabs defaultValue="all">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="all">Tất cả</TabsTrigger>
                <TabsTrigger value="wrong">Sai</TabsTrigger>
                <TabsTrigger value="correct">Đúng</TabsTrigger>
              </TabsList>

              <TabsContent value="all" className="mt-4 space-y-2">
                {filteredQuestions.map(renderQuestionButton)}
              </TabsContent>

              <TabsContent value="wrong" className="mt-4 space-y-2">
                {filteredQuestions.filter((q) => !q.isCorrect).map(renderQuestionButton)}
              </TabsContent>

              <TabsContent value="correct" className="mt-4 space-y-2">
                {filteredQuestions.filter((q) => q.isCorrect).map(renderQuestionButton)}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        <Card className="xl:col-span-6">
          <CardHeader>
            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <CardTitle>Câu {selectedQuestion.id}</CardTitle>

                  <div className={`rounded-full p-1 ${selectedQuestion.isCorrect ? "bg-green-100" : "bg-red-100"}`}>
                    {selectedQuestion.isCorrect ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-600" />
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline">Part {selectedQuestion.part}</Badge>
                  <Badge variant="secondary">{selectedQuestion.skill}</Badge>
                  <Badge variant="secondary">{selectedQuestion.subskill}</Badge>
                  <Badge
                    className={
                      selectedQuestion.difficulty === "easy"
                        ? "bg-green-100 text-green-700"
                        : selectedQuestion.difficulty === "medium"
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-red-100 text-red-700"
                    }
                  >
                    {selectedQuestion.difficulty === "easy"
                      ? "Dễ"
                      : selectedQuestion.difficulty === "medium"
                        ? "TB"
                        : "Khó"}
                  </Badge>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <Button variant="outline" size="icon" className="rounded-2xl shadow-sm" title="Highlight">
                  <Highlighter className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="icon" className="rounded-2xl shadow-sm" title="Ghi chú">
                  <MessageSquare className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="icon" className="rounded-2xl shadow-sm" title="Dịch">
                  <Languages className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="icon" className="rounded-2xl shadow-sm" title="Lưu vào sổ tay">
                  <BookMarked className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="icon" className="rounded-2xl shadow-sm" title="Hỏi AI">
                  <Sparkles className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-6">
            {(isLoadingDetail || detailError) && (
              <div className="rounded-xl border border-[#E7EEF9] bg-[#F8FBFF] p-4 text-sm text-muted-foreground">
                {isLoadingDetail
                  ? "Loading full review detail from FastAPI..."
                  : `Could not load review detail: ${detailError}`}
              </div>
            )}

            {(selectedQuestion.passageTitle || selectedQuestion.passageText) && (
              <div className="rounded-xl border border-[#E7EEF9] bg-[#F8FBFF] p-4">
                {selectedQuestion.passageTitle && (
                  <p className="mb-2 font-semibold text-foreground">
                    {selectedQuestion.passageTitle}
                  </p>
                )}
                {selectedQuestion.passageText && (
                  <p className="whitespace-pre-line text-sm leading-relaxed text-foreground">
                    {selectedQuestion.passageText}
                  </p>
                )}
              </div>
            )}

            {(selectedQuestion.audioUrl ||
              selectedQuestion.imageUrl ||
              selectedQuestion.graphicUrl) && (
              <div className="space-y-3 rounded-xl border border-[#E7EEF9] bg-[#F8FBFF] p-4">
                {selectedQuestion.audioUrl && (
                  <audio controls src={selectedQuestion.audioUrl} className="w-full" />
                )}
                {(selectedQuestion.imageUrl || selectedQuestion.graphicUrl) && (
                  <img
                    src={selectedQuestion.imageUrl ?? selectedQuestion.graphicUrl ?? undefined}
                    alt={`Review item ${selectedQuestion.id}`}
                    className="max-h-[360px] w-full rounded-lg object-contain"
                  />
                )}
              </div>
            )}

            <div className="flex justify-end">
              <Button
                className="gap-2"
                onClick={() => void handleMarkReviewed()}
                disabled={
                  isMarkingReviewed ||
                  selectedQuestion.status === "reviewed" ||
                  selectedQuestion.status === "empty"
                }
              >
                <CheckCircle className="h-4 w-4" />
                {selectedQuestion.status === "reviewed"
                  ? "Reviewed"
                  : isMarkingReviewed
                    ? "Marking..."
                    : "Mark reviewed"}
              </Button>
            </div>
            <div className="rounded-xl bg-muted/50 p-4 text-lg leading-relaxed" onMouseUp={handleTextSelect}>
              {selectedQuestion.question}
            </div>

            {showToolbar ? (
              <div
                className="fixed z-50 flex items-center gap-1 rounded-2xl border bg-card p-2 shadow-lg"
                style={{ left: toolbarPosition.x - 145, top: toolbarPosition.y - 54 }}
              >
                <Button variant="ghost" size="icon" className="h-9 w-9 rounded-xl" title="Highlight">
                  <Highlighter className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" className="h-9 w-9 rounded-xl" title="Lưu vào sổ tay">
                  <BookMarked className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" className="h-9 w-9 rounded-xl" title="Ghi chú">
                  <MessageSquare className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" className="h-9 w-9 rounded-xl" title="Dịch">
                  <Languages className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" className="h-9 w-9 rounded-xl" title="Hỏi AI">
                  <Sparkles className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-9 w-9 rounded-xl"
                  onClick={() => setShowToolbar(false)}
                  title="Đóng"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ) : null}

            <div className="space-y-3">
              {selectedQuestion.options.length === 0 && (
                <div className="rounded-xl border border-[#E7EEF9] bg-[#F8FBFF] p-4 text-sm text-muted-foreground">
                  Full question choices are not exposed by the current review API yet.
                  Showing review queue metadata from FastAPI instead.
                </div>
              )}

              {selectedQuestion.options.map((option, idx) => {
                const optionLetter = String.fromCharCode(65 + idx);
                const isUserAnswer =
                  selectedQuestion.userAnswerIndex === idx ||
                  selectedQuestion.userAnswer === option ||
                  selectedQuestion.userAnswer === optionLetter;
                const isCorrectAnswer =
                  selectedQuestion.correctAnswerIndex === idx ||
                  selectedQuestion.correctAnswer === option ||
                  selectedQuestion.correctAnswer === optionLetter;

                return (
                  <div
                    key={idx}
                    className={`flex items-center gap-4 rounded-xl border-2 p-4 ${
                      isCorrectAnswer
                        ? "border-green-500 bg-green-50"
                        : isUserAnswer && !selectedQuestion.isCorrect
                          ? "border-red-500 bg-red-50"
                          : "border-border"
                    }`}
                  >
                    <div
                      className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold ${
                        isCorrectAnswer
                          ? "bg-green-500 text-white"
                          : isUserAnswer && !selectedQuestion.isCorrect
                            ? "bg-red-500 text-white"
                            : "bg-muted"
                      }`}
                    >
                      {optionLetter}
                    </div>

                    <span className="flex-1">{option}</span>

                    {isCorrectAnswer ? <Badge className="bg-green-500">Đáp án đúng</Badge> : null}
                    {isUserAnswer && !selectedQuestion.isCorrect ? <Badge variant="destructive">Bạn chọn</Badge> : null}
                    {isUserAnswer && selectedQuestion.isCorrect ? <Badge className="bg-green-500">Bạn chọn</Badge> : null}
                  </div>
                );
              })}
            </div>

            <div className="rounded-xl border bg-primary/5 p-4">
              <div className="mb-3 flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                <h4 className="font-semibold">Giải thích</h4>
              </div>
              <p className="leading-relaxed text-muted-foreground">{selectedQuestion.explanation}</p>
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-2">
              {selectedQuestion.status === "empty" ? (
                <Button variant="outline" className="gap-2" disabled>
                  <BookOpen className="h-4 w-4" />
                  Practice this type again
                </Button>
              ) : (
                <Button variant="outline" className="gap-2" asChild>
                  <Link to={buildReviewPracticeUrl(selectedQuestion)}>
                    <BookOpen className="h-4 w-4" />
                    Practice this type again
                  </Link>
                </Button>
              )}
              <Button variant="outline" className="gap-2">
                <Sparkles className="h-4 w-4" />
                Hỏi AI thêm
              </Button>
              <Button variant="outline" className="gap-2">
                <BookMarked className="h-4 w-4" />
                Lưu vào sổ tay
              </Button>
              <Button variant="outline" className="hidden gap-2">
                <BookOpen className="h-4 w-4" />
                Luyện dạng này
              </Button>
            </div>

            <div className="space-y-3 border-t pt-4">
              <h4 className="flex items-center gap-2 font-medium">
                <FileText className="h-4 w-4" />
                Ghi chú cá nhân
              </h4>

              <Textarea
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                placeholder="Thêm ghi chú cho câu hỏi này..."
                className="min-h-[100px]"
              />

              <Button size="sm">Lưu ghi chú</Button>
            </div>
          </CardContent>
        </Card>

        <div className="xl:col-span-3">
          <ProFeatureGuard
            feature="aiChatUnlimited"
            compact
            title="AI Tutor trong Review la tinh nang Pro"
            description="Free van xem review va dap an. Nang cap Pro de hoi AI Tutor theo tung loi sai."
          >
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Sparkles className="h-4 w-4 text-primary" />
              AI Tutor
            </CardTitle>
          </CardHeader>

          <CardContent className="flex h-[700px] flex-col">
            <div className="flex-1 space-y-3 overflow-auto rounded-xl border bg-muted/20 p-3">
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[90%] rounded-2xl p-3 text-sm ${
                      msg.role === "user"
                        ? "rounded-br-md bg-primary text-primary-foreground"
                        : "rounded-bl-md bg-muted"
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 space-y-3">
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => askQuickPrompt("Giải thích bằng tiếng Việt")}
                >
                  Giải thích tiếng Việt
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => askQuickPrompt("Vì sao đáp án đúng?")}
                >
                  Vì sao đúng?
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => askQuickPrompt("Phân tích đáp án sai")}
                >
                  Đáp án sai
                </Button>
                <Button variant="outline" size="sm" className="text-xs" onClick={() => askQuickPrompt("Dịch câu hỏi")}>
                  Dịch câu hỏi
                </Button>
                <Button variant="outline" size="sm" className="text-xs" onClick={() => askQuickPrompt("Mẹo làm dạng này")}>
                  Mẹo làm bài
                </Button>
              </div>

              <div className="flex items-end gap-2">
                <Textarea
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Hỏi AI về câu này..."
                  className="min-h-[70px] resize-none"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      sendMessage();
                    }
                  }}
                />
                <Button size="icon" onClick={sendMessage}>
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
          </ProFeatureGuard>
        </div>
      </div>
    </div>
  );
}
