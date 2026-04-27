import { apiRequest } from "@src/services/apiClient";

export type DiagnosticQuestion = {
  id: number;
  question: string;
  options: string[];
  correct?: number | null;
  skill?: string | null;
  subskill?: string | null;
  image?: { path?: string | null } | null;
  audio?: { path?: string | null } | null;
};

export type DiagnosticQuestionsResponse = {
  test_info?: {
    name?: string;
    duration_minutes?: number;
    total_questions?: number;
  };
  questions: DiagnosticQuestion[];
};

export type DiagnosticSubmitResponse = {
  analysis: {
    score: number;
    level: {
      code: string;
      name: string;
      range: string;
    };
    accuracyPct: number;
    correctCount: number;
    answeredCount: number;
    total: number;
    weakSubskills: string[];
    topErrors: Array<{
      type: string;
      count: number;
    }>;
  };
  roadmap: Array<{
    week: number;
    focus: string;
    title: string;
    tasks: string[];
  }>;
};

export type SaveDiagnosticAttemptPayload = {
  targetScore?: number | null;
  weeks?: number | null;
  minutesPerDay?: number | null;
  score: number;
  accuracyPct: number;
  correctCount: number;
  totalQuestions: number;
  levelName?: string | null;
  levelRange?: string | null;
  weakSubskillsJson?: string | null;
  topErrorsJson?: string | null;
  answers: Array<{
    questionId: number;
    questionNumber: number;
    part?: number | null;
    skill?: string | null;
    subskill?: string | null;
    selectedAnswerIndex?: number | null;
    correctAnswerIndex?: number | null;
    isCorrect: boolean;
  }>;
};

export type SaveDiagnosticAttemptResponse = {
  attemptId: number;
  reviewQueuedCount: number;
  skillStatsUpdated: number;
  partStatsUpdated: number;
};

export const diagnosticService = {
  async getQuestions(): Promise<DiagnosticQuestionsResponse> {
    return apiRequest<DiagnosticQuestionsResponse>("/api/diagnostic/questions", {
      auth: true,
    });
  },

  async submitDiagnostic(payload: {
    answers: Record<string, number>;
    target_score: number;
    weeks: number;
    minutes_per_day: number;
  }): Promise<DiagnosticSubmitResponse> {
    return apiRequest<DiagnosticSubmitResponse>("/api/diagnostic/submit", {
      method: "POST",
      auth: true,
      body: JSON.stringify(payload),
    });
  },

  async saveAttempt(
    payload: SaveDiagnosticAttemptPayload,
  ): Promise<SaveDiagnosticAttemptResponse> {
    return apiRequest<SaveDiagnosticAttemptResponse>("/api/attempts/diagnostic", {
      method: "POST",
      auth: true,
      body: JSON.stringify(payload),
    });
  },
};
