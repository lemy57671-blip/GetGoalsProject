import { ApiError, apiRequest } from "@src/services/apiClient";

export type ProgressHistoryPoint = {
  date: string;
  studyMinutes: number;
  attemptsCount: number;
  correctAnswers: number;
  wrongAnswers: number;
  accuracy: number;
};

export type ProgressSkill = {
  name: string;
  value: number;
  accuracy: number;
  change: string;
  trend: "up" | "down";
};

export type ProgressPart = {
  part: string;
  accuracy: number;
  speed: string;
  status: string;
};

export type ProgressRecentPracticeAttempt = {
  id: number;
  title: string;
  subtitle?: string | null;
  mode: string;
  parts: string;
  correctCount: number;
  totalQuestions: number;
  accuracy: number;
  timeSpentSeconds: number;
  submittedAtUtc?: string | null;
};

export type ProgressView = {
  totalAttempts: number;
  totalCorrectAnswers: number;
  totalWrongAnswers: number;
  averageAccuracy: number;
  pendingReviewCount: number;
  weeklyStudyMinutes: ProgressHistoryPoint[];
  scoreHistory: Array<{
    week: string;
    score: number;
  }>;
  weeklyActivity: Array<{
    day: string;
    minutes: number;
  }>;
  skillProgress: ProgressSkill[];
  partProgress: ProgressPart[];
  recentPracticeAttempts: ProgressRecentPracticeAttempt[];
  recentMockTestsCount: number;
  weeklyMinutes: number;
};

type ProgressSummaryResponse = {
  weeklyStudyMinutes?: ProgressHistoryPoint[];
  totalAttempts?: number;
  totalCorrectAnswers?: number;
  totalWrongAnswers?: number;
  averageAccuracy?: number;
  skillProfiles?: Array<{
    skillCode?: string;
    skillName?: string;
    accuracy?: number;
    correctCount?: number;
    attemptCount?: number;
  }>;
  partStats?: Array<{
    part?: number;
    accuracy?: number;
    correctCount?: number;
    attemptCount?: number;
    averageTimeSeconds?: number;
  }>;
  recentPracticeAttempts?: ProgressRecentPracticeAttempt[];
  recentMockTests?: unknown[];
  pendingReviewCount?: number;
};

const dayFormatter = new Intl.DateTimeFormat("en-US", { weekday: "short" });

function statusFromAccuracy(accuracy: number) {
  if (accuracy >= 80) return "Strong";
  if (accuracy >= 60) return "Improving";
  if (accuracy > 0) return "Needs work";
  return "No data";
}

function speedFromSeconds(seconds?: number) {
  if (!seconds) return "N/A";
  if (seconds <= 45) return "Fast";
  if (seconds <= 90) return "OK";
  return "Slow";
}

function mapScoreHistory(history: ProgressHistoryPoint[]) {
  const active = history.filter(
    (point) => point.attemptsCount > 0 || point.correctAnswers || point.wrongAnswers,
  );
  const source = active.length > 0 ? active : history.slice(-6);

  return source.slice(-6).map((point, index) => ({
    week: `D${index + 1}`,
    score: Math.round(point.accuracy || 0),
  }));
}

function mapWeeklyActivity(history: ProgressHistoryPoint[]) {
  return history.slice(-7).map((point) => ({
    day: dayFormatter.format(new Date(`${point.date}T00:00:00`)),
    minutes: point.studyMinutes || 0,
  }));
}

function mapProgress(summary: ProgressSummaryResponse): ProgressView {
  const weeklyStudyMinutes = summary.weeklyStudyMinutes || [];
  const totalCorrectAnswers = summary.totalCorrectAnswers || 0;
  const totalWrongAnswers = summary.totalWrongAnswers || 0;

  return {
    totalAttempts: summary.totalAttempts || 0,
    totalCorrectAnswers,
    totalWrongAnswers,
    averageAccuracy: summary.averageAccuracy || 0,
    pendingReviewCount: summary.pendingReviewCount || 0,
    weeklyStudyMinutes,
    scoreHistory: mapScoreHistory(weeklyStudyMinutes),
    weeklyActivity: mapWeeklyActivity(weeklyStudyMinutes),
    skillProgress: (summary.skillProfiles || []).map((skill) => {
      const accuracy = Math.round(skill.accuracy || 0);
      return {
        name: skill.skillName || skill.skillCode || "TOEIC skill",
        value: accuracy,
        accuracy,
        change: `${skill.correctCount || 0}/${skill.attemptCount || 0}`,
        trend: accuracy >= 60 ? "up" : "down",
      };
    }),
    partProgress: (summary.partStats || []).map((part) => {
      const accuracy = Math.round(part.accuracy || 0);
      return {
        part: `Part ${part.part || 0}`,
        accuracy,
        speed: speedFromSeconds(part.averageTimeSeconds),
        status: statusFromAccuracy(accuracy),
      };
    }),
    recentPracticeAttempts: summary.recentPracticeAttempts || [],
    recentMockTestsCount: (summary.recentMockTests || []).length,
    weeklyMinutes: weeklyStudyMinutes.reduce(
      (sum, point) => sum + (point.studyMinutes || 0),
      0,
    ),
  };
}

export const progressService = {
  async getSummary(): Promise<ProgressView> {
    try {
      const summary = await apiRequest<ProgressSummaryResponse>(
        "/api/progress/summary",
        { auth: true },
      );

      return mapProgress(summary);
    } catch (error) {
      if (error instanceof ApiError && [401, 403].includes(error.status)) {
        return mapProgress({});
      }

      throw error;
    }
  },
};
