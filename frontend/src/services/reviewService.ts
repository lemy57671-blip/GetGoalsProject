import { API_BASE_URL, ApiError, apiRequest } from "@src/services/apiClient";

export type ReviewQueueQuestion = {
  id: number;
  queueId: number;
  questionId: number;
  question: string;
  options: string[];
  userAnswer: string;
  correctAnswer: string;
  isCorrect: boolean;
  explanation: string;
  skill: string;
  subskill: string;
  part: number;
  difficulty: "easy" | "medium" | "hard";
  status: string;
  sourceAttemptType?: string | null;
  sourceAttemptId?: number | null;
  addedAtUtc?: string;
  reviewedAtUtc?: string | null;
  userAnswerIndex?: number | null;
  correctAnswerIndex?: number | null;
  passageTitle?: string | null;
  passageText?: string | null;
  audioUrl?: string | null;
  imageUrl?: string | null;
  graphicUrl?: string | null;
};

export type ReviewSummaryView = {
  pendingCount: number;
  reviewedCount: number;
  topWeakSkills: Array<{
    skill: string;
    accuracy: number;
    attemptCount: number;
  }>;
  questions: ReviewQueueQuestion[];
  skillBreakdown: Array<{
    name: string;
    correct: number;
    total: number;
  }>;
  partBreakdown: Array<{
    name: string;
    correct: number;
    total: number;
  }>;
};

type ReviewSummaryResponse = {
  pendingCount?: number;
  reviewedCount?: number;
  topWeakSkills?: Array<{
    skill?: string;
    accuracy?: number;
    attemptCount?: number;
  }>;
  recentReviewItems?: Array<{
    id: number;
    questionId: number;
    part?: number | null;
    skill?: string | null;
    status?: string;
    sourceAttemptType?: string | null;
    sourceAttemptId?: number | null;
    note?: string | null;
    addedAtUtc?: string;
    reviewedAtUtc?: string | null;
  }>;
};

type ReviewQuestionDetailResponse = {
  id: number;
  queueId: number;
  questionId: number;
  question?: string;
  options?: string[];
  userAnswer?: string | null;
  userAnswerIndex?: number | null;
  correctAnswer?: string | null;
  correctAnswerIndex?: number | null;
  isCorrect?: boolean;
  explanation?: string | null;
  skill?: string | null;
  subskill?: string | null;
  part?: number | null;
  difficulty?: string | null;
  status?: string;
  sourceAttemptType?: string | null;
  sourceAttemptId?: number | null;
  note?: string | null;
  addedAtUtc?: string;
  reviewedAtUtc?: string | null;
  passageTitle?: string | null;
  passageText?: string | null;
  audioUrl?: string | null;
  imageUrl?: string | null;
  graphicUrl?: string | null;
};

function toAssetUrl(path?: string | null) {
  if (!path) return undefined;
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

function normalizeDifficulty(value?: string | null): ReviewQueueQuestion["difficulty"] {
  const normalized = (value || "").toLowerCase();
  if (normalized === "easy" || normalized === "hard") return normalized;
  return "medium";
}

function mapQuestion(item: NonNullable<ReviewSummaryResponse["recentReviewItems"]>[number]): ReviewQueueQuestion {
  const status = item.status || "pending";
  const part = item.part || 0;
  const source =
    item.sourceAttemptType && item.sourceAttemptId
      ? `${item.sourceAttemptType} #${item.sourceAttemptId}`
      : "review queue";

  return {
    id: item.id,
    queueId: item.id,
    questionId: item.questionId,
    question: `Question #${item.questionId} from ${source}`,
    options: [],
    userAnswer: "Not available in review summary",
    correctAnswer: "Open the original attempt for full answer detail",
    isCorrect: status !== "pending",
    explanation:
      item.note ||
      "This item was queued from a missed practice answer. The current review API exposes queue metadata, but not the full question/options yet.",
    skill: item.skill || "TOEIC review",
    subskill: item.sourceAttemptType || "practice",
    part,
    difficulty: "medium",
    status,
    sourceAttemptType: item.sourceAttemptType,
    sourceAttemptId: item.sourceAttemptId,
    addedAtUtc: item.addedAtUtc,
    reviewedAtUtc: item.reviewedAtUtc,
  };
}

function mapDetail(item: ReviewQuestionDetailResponse): ReviewQueueQuestion {
  return {
    id: item.id,
    queueId: item.queueId || item.id,
    questionId: item.questionId,
    question: item.question || `Question #${item.questionId}`,
    options: item.options || [],
    userAnswer: item.userAnswer || "",
    userAnswerIndex: item.userAnswerIndex,
    correctAnswer: item.correctAnswer || "",
    correctAnswerIndex: item.correctAnswerIndex,
    isCorrect: Boolean(item.isCorrect),
    explanation:
      item.explanation ||
      item.note ||
      "No explanation is available for this review item yet.",
    skill: item.skill || "TOEIC review",
    subskill: item.subskill || item.sourceAttemptType || "practice",
    part: item.part || 0,
    difficulty: normalizeDifficulty(item.difficulty),
    status: item.status || "pending",
    sourceAttemptType: item.sourceAttemptType,
    sourceAttemptId: item.sourceAttemptId,
    addedAtUtc: item.addedAtUtc,
    reviewedAtUtc: item.reviewedAtUtc,
    passageTitle: item.passageTitle,
    passageText: item.passageText,
    audioUrl: toAssetUrl(item.audioUrl),
    imageUrl: toAssetUrl(item.imageUrl),
    graphicUrl: toAssetUrl(item.graphicUrl),
  };
}

function buildSkillBreakdown(summary: ReviewSummaryResponse) {
  const topWeakSkills = summary.topWeakSkills || [];

  if (topWeakSkills.length > 0) {
    return topWeakSkills.map((item) => ({
      name: item.skill || "TOEIC review",
      correct: 0,
      total: item.attemptCount || 0,
    }));
  }

  return [];
}

function buildPartBreakdown(questions: ReviewQueueQuestion[]) {
  const grouped = new Map<number, ReviewQueueQuestion[]>();

  questions.forEach((question) => {
    if (question.part > 0) {
      grouped.set(question.part, [...(grouped.get(question.part) || []), question]);
    }
  });

  return Array.from(grouped.entries())
    .sort(([left], [right]) => left - right)
    .map(([part, items]) => ({
      name: `Part ${part}`,
      correct: items.filter((item) => item.status !== "pending").length,
      total: items.length,
    }));
}

export const reviewService = {
  async getSummary(): Promise<ReviewSummaryView> {
    try {
      const summary = await apiRequest<ReviewSummaryResponse>("/api/review/summary", {
        auth: true,
      });
      const questions = (summary.recentReviewItems || []).map(mapQuestion);

      return {
        pendingCount: summary.pendingCount || 0,
        reviewedCount: summary.reviewedCount || 0,
        topWeakSkills: (summary.topWeakSkills || []).map((item) => ({
          skill: item.skill || "TOEIC review",
          accuracy: item.accuracy || 0,
          attemptCount: item.attemptCount || 0,
        })),
        questions,
        skillBreakdown: buildSkillBreakdown(summary),
        partBreakdown: buildPartBreakdown(questions),
      };
    } catch (error) {
      if (error instanceof ApiError && [401, 403].includes(error.status)) {
        return {
          pendingCount: 0,
          reviewedCount: 0,
          topWeakSkills: [],
          questions: [],
          skillBreakdown: [],
          partBreakdown: [],
        };
      }

      throw error;
    }
  },

  async getItem(itemId: number): Promise<ReviewQueueQuestion> {
    const detail = await apiRequest<ReviewQuestionDetailResponse>(
      `/api/review/item/${itemId}`,
      { auth: true },
    );

    return mapDetail(detail);
  },

  async markReviewed(itemId: number): Promise<ReviewQueueQuestion> {
    const detail = await apiRequest<ReviewQuestionDetailResponse>(
      `/api/review/item/${itemId}/mark-reviewed`,
      {
        method: "POST",
        auth: true,
      },
    );

    return mapDetail(detail);
  },
};
