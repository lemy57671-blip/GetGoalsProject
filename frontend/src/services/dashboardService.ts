import { ApiError, apiRequest } from "@src/services/apiClient";

export type DashboardSummary = {
  completed: number;
  inProgress: number;
};

export type DashboardCourse = {
  id: number;
  title: string;
  author: string;
  rating: number;
  progress: number;
};

export type WeeklyHoursItem = {
  day: string;
  hours: number;
};

export type WeakMetric = {
  skill: string;
  accuracy: number;
  attemptCount: number;
};

export type WeakPartMetric = {
  part: number;
  accuracy: number;
  attemptCount: number;
};

export type LatestMockTest = {
  title: string;
  totalScaledScore: number;
  listeningScaledScore: number;
  readingScaledScore: number;
  accuracy: number;
  submittedAtUtc?: string | null;
};

export type LatestDiagnostic = {
  estimatedScore: number;
  estimatedLevel?: string | null;
  levelRange?: string | null;
  theta?: number | null;
  submittedAtUtc?: string | null;
  weakSubskills: string[];
};

export type ProgressHistoryItem = {
  date: string;
  studyMinutes: number;
  attemptsCount: number;
  correctAnswers: number;
  wrongAnswers: number;
  accuracy: number;
};

export type AnalyticsBreakdownItem = {
  code: string;
  label: string;
  accuracy: number;
  correctCount: number;
  attemptCount: number;
};

export type AnalyticsPartBreakdownItem = {
  part: number;
  accuracy: number;
  correctCount: number;
  attemptCount: number;
};

export type UserSkillAnalytics = {
  userId: number;
  weakestSkill: string;
  weakestSkillLabel: string;
  weakestPart?: number | null;
  topWeakSubskills: string[];
  skillBreakdown: AnalyticsBreakdownItem[];
  subskillBreakdown: AnalyticsBreakdownItem[];
  partBreakdown: AnalyticsPartBreakdownItem[];
  basedOnAttemptId?: number | null;
  updatedAtUtc?: string | null;
};

export type RoadmapSuggestedSetCriteria = {
  strategy: string;
  focusSkill: string;
  focusPart?: number | null;
  includeParts: number[];
  subskills: string[];
  difficulty: string;
  questionCount: number;
  tags: string[];
};

export type RoadmapSuggestedSet = {
  id: number;
  setKey: string;
  itemType: string;
  title: string;
  description: string;
  focusSkill: string;
  focusPart?: number | null;
  subskills: string[];
  questionCount: number;
  difficulty: string;
  tags: string[];
  criteria: RoadmapSuggestedSetCriteria;
};

export type RoadmapWeek = {
  id: number;
  weekNumber: number;
  title: string;
  description: string;
  focusSkill: string;
  focusPart?: number | null;
  subskills: string[];
  recommendedQuestionCount: number;
  estimatedMinutes: number;
  status: string;
  startedAtUtc?: string | null;
  completedAtUtc?: string | null;
  suggestedSets: RoadmapSuggestedSet[];
};

export type RoadmapCurrent = {
  id: number;
  userId: number;
  title: string;
  sourceType: string;
  weakestSkill: string;
  weakestSkillLabel: string;
  weakestPart?: number | null;
  totalWeeks: number;
  isActive: boolean;
  basedOnAttemptId?: number | null;
  createdAtUtc: string;
  updatedAtUtc: string;
  analytics?: UserSkillAnalytics | null;
  weeks: RoadmapWeek[];
};

export type DashboardOverviewView = {
  totalPracticeAttempts: number;
  recentAccuracy: number;
  totalStudyMinutes: number;
  pendingReviewCount: number;
  recentActiveDays: number;
  streakDays: number;
  weakestSkill?: WeakMetric | null;
  weakestPart?: WeakPartMetric | null;
  latestMockTest?: LatestMockTest | null;
  latestDiagnostic?: LatestDiagnostic | null;
  activeRoadmap?: RoadmapCurrent | null;
};

const emptyOverview: DashboardOverviewView = {
  totalPracticeAttempts: 0,
  recentAccuracy: 0,
  totalStudyMinutes: 0,
  pendingReviewCount: 0,
  recentActiveDays: 0,
  streakDays: 0,
  weakestSkill: null,
  weakestPart: null,
  latestMockTest: null,
  latestDiagnostic: null,
  activeRoadmap: null,
};

function isUnauthorized(error: unknown) {
  return error instanceof ApiError && [401, 403].includes(error.status);
}

export const dashboardService = {
  async getOverview(): Promise<DashboardOverviewView> {
    try {
      return await apiRequest<DashboardOverviewView>("/api/dashboard/overview", {
        auth: true,
      });
    } catch (error) {
      if (isUnauthorized(error)) {
        return emptyOverview;
      }

      throw error;
    }
  },

  async getProgressHistory(days = 7): Promise<ProgressHistoryItem[]> {
    try {
      return await apiRequest<ProgressHistoryItem[]>(
        `/api/progress/history?days=${days}`,
        { auth: true },
      );
    } catch (error) {
      if (isUnauthorized(error)) {
        return [];
      }

      throw error;
    }
  },

  async getSummary(userId: number | string): Promise<DashboardSummary> {
    return apiRequest<DashboardSummary>(`/api/dashboard/summary?userId=${userId}`);
  },

  async getCourses(userId: number | string): Promise<DashboardCourse[]> {
    return apiRequest<DashboardCourse[]>(`/api/dashboard/courses?userId=${userId}`);
  },

  async getWeeklyHours(userId: number | string): Promise<WeeklyHoursItem[]> {
    return apiRequest<WeeklyHoursItem[]>(
      `/api/dashboard/weekly-hours?userId=${userId}`,
    );
  },
};
