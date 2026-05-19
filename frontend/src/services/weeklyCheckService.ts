import { apiRequest } from "@src/services/apiClient";
import type {
  PracticeAttemptResult,
  SavePracticeAttemptResponse,
} from "@src/services/attemptsService";
import {
  mapToeicRunnerQuestion,
  type ToeicRunnerQuestion,
  type ToeicRunnerQuestionResponse,
} from "@src/services/toeicService";

type WeeklyCheckCurrentResponse = {
  attemptId?: number | null;
  weeklyCheckId: string;
  title: string;
  description: string;
  totalQuestions: number;
  estimatedMinutes: number;
  focusSkill: string;
  focusSkillLabel: string;
  focusPart?: number | null;
  sourceAnalytics: string;
  difficulty: string;
  topWeakSubskills: string[];
  questions: ToeicRunnerQuestionResponse[];
};

export type WeeklyCheckCurrent = Omit<WeeklyCheckCurrentResponse, "questions"> & {
  questions: ToeicRunnerQuestion[];
};

type SubmitWeeklyCheckInput = {
  weeklyCheck: WeeklyCheckCurrent;
  answers: Record<number, string>;
  flaggedQuestions: number[];
  timeSpentSeconds: number;
  startedAtUtc?: string;
};

function getChoiceIndex(choiceId?: string | null) {
  if (!choiceId) return null;
  const normalized = choiceId.trim().toUpperCase();
  if (!/^[A-Z]$/.test(normalized)) return null;
  return normalized.charCodeAt(0) - "A".charCodeAt(0);
}

export const weeklyCheckService = {
  async getCurrent(): Promise<WeeklyCheckCurrent> {
    const response = await apiRequest<WeeklyCheckCurrentResponse>(
      "/api/weekly-check/current",
      { auth: true },
    );

    return {
      ...response,
      questions: (response.questions || []).map(mapToeicRunnerQuestion),
    };
  },

  async submitWeeklyCheck({
    weeklyCheck,
    answers,
    flaggedQuestions,
    timeSpentSeconds,
    startedAtUtc,
  }: SubmitWeeklyCheckInput): Promise<SavePracticeAttemptResponse> {
    const payloadAnswers = weeklyCheck.questions.map((question, index) => ({
      questionId: question.id,
      part: question.partNumber,
      selectedAnswerIndex: getChoiceIndex(answers[index + 1]),
      isFlagged: flaggedQuestions.includes(index + 1),
    }));

    return apiRequest<SavePracticeAttemptResponse>("/api/weekly-check/submit", {
      method: "POST",
      auth: true,
      body: JSON.stringify({
        weeklyCheckId: weeklyCheck.weeklyCheckId,
        attemptId: weeklyCheck.attemptId ?? weeklyCheck.questions[0]?.attemptId ?? null,
        title: weeklyCheck.title,
        description: weeklyCheck.description,
        totalQuestions: weeklyCheck.totalQuestions || weeklyCheck.questions.length,
        estimatedMinutes: weeklyCheck.estimatedMinutes,
        focusSkill: weeklyCheck.focusSkill,
        focusPart: weeklyCheck.focusPart,
        sourceAnalytics: weeklyCheck.sourceAnalytics,
        startedAtUtc,
        timeSpentSeconds,
        answers: payloadAnswers,
      }),
    });
  },

  async getResult(attemptId: number): Promise<PracticeAttemptResult> {
    return apiRequest<PracticeAttemptResult>(
      `/api/weekly-check/result/${attemptId}`,
      { auth: true },
    );
  },
};
