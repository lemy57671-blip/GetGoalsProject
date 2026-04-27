import { ApiError, apiRequest } from "@src/services/apiClient";
import {
  mapToeicRunnerQuestion,
  type ToeicRunnerQuestion,
  type ToeicRunnerQuestionResponse,
} from "@src/services/toeicService";

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
  criteria: {
    strategy: string;
    focusSkill: string;
    focusPart?: number | null;
    includeParts: number[];
    subskills: string[];
    difficulty: string;
    questionCount: number;
    tags: string[];
  };
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
  weeks: RoadmapWeek[];
};

export type RoadmapSetRunner = {
  weekId: number;
  setId: number;
  setKey: string;
  title: string;
  description: string;
  focusSkill: string;
  focusPart?: number | null;
  tags: string[];
  questions: ToeicRunnerQuestion[];
};

export type RoadmapWeekSetsResponse = {
  roadmapId: number;
  weekId: number;
  weekNumber: number;
  title: string;
  description: string;
  focusSkill: string;
  focusPart?: number | null;
  subskills: string[];
  status: string;
  suggestedSets: RoadmapSuggestedSet[];
};

export type RoadmapSetEvidence = {
  weekId: number;
  setId: number;
  attemptId: number;
  title: string;
  subtitle?: string | null;
  accuracy: number;
  correctCount: number;
  totalQuestions: number;
  submittedAtUtc?: string | null;
  confidence: "heuristic";
  reason: string;
};

type RoadmapSetQuestionsResponse = Omit<RoadmapSetRunner, "questions"> & {
  questions?: ToeicRunnerQuestionResponse[];
};

type RoadmapEvidenceResponse = {
  items?: RoadmapSetEvidence[];
  skippedUnparseableCount?: number;
  matchRule?: string;
};

function practiceUrlForSet(weekId: number, set: RoadmapSuggestedSet) {
  const params = new URLSearchParams({
    weekId: String(weekId),
    setId: String(set.id),
    difficulty: set.difficulty || set.criteria.difficulty || "mixed",
    mode: "roadmap-set",
  });

  return `/practice/runner?${params.toString()}`;
}

function mapRoadmapSetRunner(payload: RoadmapSetQuestionsResponse): RoadmapSetRunner {
  return {
    ...payload,
    questions: (payload.questions || []).map(mapToeicRunnerQuestion),
  };
}

function evidenceKey(weekId: number, setId: number) {
  return `${weekId}:${setId}`;
}

function mapEvidence(items: RoadmapSetEvidence[] = []) {
  const evidence: Record<string, RoadmapSetEvidence> = {};

  for (const item of items) {
    const key = evidenceKey(item.weekId, item.setId);
    const existing = evidence[key];
    const existingTime = existing?.submittedAtUtc
      ? new Date(existing.submittedAtUtc).getTime()
      : 0;
    const currentTime = item.submittedAtUtc
      ? new Date(item.submittedAtUtc).getTime()
      : 0;

    if (existing && existingTime > currentTime) continue;

    evidence[key] = item;
  }

  return evidence;
}

export const roadmapService = {
  async getCurrent(): Promise<RoadmapCurrent | null> {
    try {
      return await apiRequest<RoadmapCurrent>("/api/roadmap/current", {
        auth: true,
      });
    } catch (error) {
      if (error instanceof ApiError && [401, 403, 404].includes(error.status)) {
        return null;
      }

      throw error;
    }
  },

  async generateCurrent(): Promise<RoadmapCurrent> {
    return apiRequest<RoadmapCurrent>("/api/roadmap/generate", {
      method: "POST",
      auth: true,
    });
  },

  async startWeek(weekId: number): Promise<RoadmapWeek> {
    return apiRequest<RoadmapWeek>(`/api/roadmap/week/${weekId}/start`, {
      method: "POST",
      auth: true,
    });
  },

  async completeWeek(weekId: number): Promise<RoadmapWeek> {
    return apiRequest<RoadmapWeek>(`/api/roadmap/week/${weekId}/complete`, {
      method: "POST",
      auth: true,
    });
  },

  async getWeekSets(weekId: number): Promise<RoadmapWeekSetsResponse> {
    return apiRequest<RoadmapWeekSetsResponse>(
      `/api/roadmap/week/${weekId}/sets`,
      { auth: true },
    );
  },

  async getSetRunner(weekId: number, setId: number): Promise<RoadmapSetRunner> {
    const payload = await apiRequest<RoadmapSetQuestionsResponse>(
      `/api/roadmap/week/${weekId}/set/${setId}`,
      { auth: true },
    );

    return mapRoadmapSetRunner(payload);
  },

  async getSetEvidence(): Promise<Record<string, RoadmapSetEvidence>> {
    try {
      const response = await apiRequest<RoadmapEvidenceResponse>(
        "/api/roadmap/evidence?limit=100",
        { auth: true },
      );

      return mapEvidence(response.items);
    } catch (error) {
      if (error instanceof ApiError && [401, 403].includes(error.status)) {
        return {};
      }

      throw error;
    }
  },

  getEvidenceKey(weekId: number, setId: number) {
    return evidenceKey(weekId, setId);
  },

  getPracticeUrl(weekId: number, set: RoadmapSuggestedSet) {
    return practiceUrlForSet(weekId, set);
  },
};
