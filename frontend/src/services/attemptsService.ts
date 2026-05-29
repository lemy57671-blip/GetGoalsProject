import { apiRequest } from "@src/services/apiClient";
import { ToeicRunnerQuestion } from "@src/services/toeicService";

export type PracticeAttemptResultQuestion = {
  questionId: number;
  runtimeQuestionId?: number | null;
  docxQuestionId?: number | null;
  sourceQuestionId?: number | null;
  missingReason?: string | null;
  questionNumber: number;
  test: number;
  part: number;
  section: string;
  partLabel?: string | null;
  type?: string | null;
  groupId?: string | null;
  skill: string;
  subskill?: string | null;
  question: string;
  questionText?: string | null;
  options: string[];
  optionRows?: Array<{
    key: string;
    text: string;
    isCorrect?: boolean;
    sortOrder?: number;
  }>;
  userAnswer?: string | null;
  userAnswerIndex?: number | null;
  selectedOptionKey?: string | null;
  selectedOptionText?: string | null;
  correctAnswer?: string | null;
  correctAnswerIndex?: number | null;
  correctOptionKey?: string | null;
  correctOptionText?: string | null;
  isCorrect: boolean;
  explanation?: string | null;
  explanationDetail?: string | null;
  explanationText?: string | null;
  rawExplanation?: string | null;
  rawBlock?: string | null;
  rawText?: string | null;
  optionAnalysis?: string | null;
  vocabularyNotes?: string | null;
  passage?: {
    id?: number | null;
    groupCode?: string | null;
    title?: string | null;
    text?: string | null;
    audioPath?: string | null;
    imagePath?: string | null;
    audio?: { path?: string | null } | null;
    image?: { path?: string | null } | null;
  } | null;
  audio?: { path?: string | null } | null;
  audioPath?: string | null;
  graphic?: { path?: string | null } | null;
  image?: { path?: string | null } | null;
  imagePath?: string | null;
};

export type PracticeAttemptResult = {
  attemptId: number;
  attemptType: string;
  title: string;
  totalQuestions: number;
  correctCount: number;
  wrongCount: number;
  unansweredCount: number;
  accuracyPct: number;
  weight_score?: number | null;
  weighted_correct?: number;
  weighted_total?: number;
  weight_score_ratio?: number;
  durationSeconds: number;
  durationMinutes?: number | null;
  scaledScore?: number | null;
  listeningScore?: number | null;
  readingScore?: number | null;
  skillBreakdown: Array<{
    skill: string;
    total: number;
    correct: number;
    accuracyPct: number;
  }>;
  partBreakdown: Array<{
    part: number;
    total: number;
    correct: number;
    accuracyPct: number;
  }>;
  weakAreas: Array<{
    type: string;
    label: string;
    accuracyPct: number;
    total: number;
    correct: number;
    suggestion: string;
  }>;
  questions: PracticeAttemptResultQuestion[];
};

export type SavePracticeAttemptResponse = {
  attemptId: number;
  reviewQueuedCount: number;
  skillStatsUpdated: number;
  partStatsUpdated: number;
  result: PracticeAttemptResult | null;
};

type SubmitPracticeAttemptInput = {
  questions: ToeicRunnerQuestion[];
  answers: Record<number, number>;
  flaggedQuestions: number[];
  timeSpentSeconds: number;
  source?: "practice" | "weeklycheck";
  mode: string;
  difficulty: string;
  title?: string;
  subtitle?: string;
  startedAtUtc?: string;
};

type MockTestRunnerQuestionInput = {
  id: number;
  attemptId?: number | null;
  sourceQuestionId?: number;
  part: number;
  type: string;
  question: string;
  options: Array<{ id: string; text: string }>;
  correctAnswer: string;
  skill: string;
  subskill: string;
  section?: string;
  partLabel?: string;
  test?: number;
  questionNumber?: number;
  correctAnswerIndex?: number | null;
  explanation?: string;
  difficulty?: string | null;
  itemDifficulty?: number | null;
  groupId?: string | null;
  audioPath?: string;
  graphicPath?: string;
  imagePath?: string;
};

type SubmitMockTestAttemptInput = {
  questions: MockTestRunnerQuestionInput[];
  answers: Record<number, string>;
  flaggedQuestions: number[];
  timeSpentSeconds: number;
  title?: string;
  source?: "fulltest" | "minitest";
  attemptType?: string;
  startedAtUtc?: string;
};

function estimatePracticeScore(accuracyPct: number) {
  return Math.max(10, Math.min(990, Math.round((accuracyPct / 100) * 990)));
}

function estimateToeicSectionScore(correct: number, total: number) {
  if (total <= 0) return 0;
  return Math.max(5, Math.min(495, Math.round((correct / total) * 495)));
}

function getChoiceIndex(choiceId?: string | null) {
  if (!choiceId) return null;
  const normalized = choiceId.trim().toUpperCase();
  if (!/^[A-Z]$/.test(normalized)) return null;
  return normalized.charCodeAt(0) - "A".charCodeAt(0);
}

function toAnswerPayload(
  question: ToeicRunnerQuestion,
  index: number,
  answers: Record<number, number>,
  flaggedQuestions: number[],
) {
  const selectedAnswerIndex = answers[index];
  const hasAnswer = typeof selectedAnswerIndex === "number";
  const correctAnswerIndex = question.correct >= 0 ? question.correct : null;
  const selectedAnswerText = hasAnswer ? question.options[selectedAnswerIndex] : null;
  const correctAnswerText =
    correctAnswerIndex !== null ? question.options[correctAnswerIndex] : null;
  const sqlQuestionId =
    question.docxQuestionId ||
    question.sourceQuestionId ||
    question.sqlId ||
    question.dbId ||
    question.questionId ||
    question.id;

  return {
    questionId: sqlQuestionId,
    questionNumber: question.questionNumber || index + 1,
    part: question.partNumber,
    test: question.test,
    section: question.section,
    partLabel: question.part,
    skill: question.skill,
    subskill: question.subskill,
    type: question.type,
    groupId: question.groupId,
    question: question.question,
    options: question.options,
    selectedAnswerIndex: hasAnswer ? selectedAnswerIndex : null,
    selectedAnswerText,
    correctAnswerIndex,
    correctAnswer: question.correctAnswer,
    correctAnswerText,
    isCorrect: hasAnswer && selectedAnswerIndex === correctAnswerIndex,
    isFlagged: flaggedQuestions.includes(index),
    difficulty: question.difficulty || "mixed",
    explanation: question.explanation,
    audio: question.audioPath ? { path: question.audioPath } : null,
    graphic: question.graphicPath ? { path: question.graphicPath } : null,
    image: question.imagePath ? { path: question.imagePath } : null,
  };
}

function toMockTestAnswerPayload(
  question: MockTestRunnerQuestionInput,
  index: number,
  answers: Record<number, string>,
  flaggedQuestions: number[],
) {
  const selectedAnswer = answers[index + 1] || null;
  const selectedAnswerIndex = getChoiceIndex(selectedAnswer);
  const correctAnswerIndex =
    typeof question.correctAnswerIndex === "number"
      ? question.correctAnswerIndex
      : getChoiceIndex(question.correctAnswer);
  const optionTexts = question.options.map((option) => option.text);
  const selectedAnswerText =
    selectedAnswerIndex !== null ? optionTexts[selectedAnswerIndex] : null;
  const correctAnswerText =
    correctAnswerIndex !== null ? optionTexts[correctAnswerIndex] : null;

  return {
    questionId: question.sourceQuestionId || question.id,
    questionNumber: question.questionNumber || index + 1,
    part: question.part,
    test: question.test || 0,
    section: question.section || (question.part <= 4 ? "Listening" : "Reading"),
    partLabel: question.partLabel || `Part ${question.part}`,
    skill: question.skill,
    subskill: question.subskill,
    type: question.type,
    groupId: question.groupId,
    question: question.question,
    options: optionTexts,
    selectedAnswerIndex,
    selectedAnswerText,
    correctAnswerIndex,
    correctAnswer: question.correctAnswer,
    correctAnswerText,
    isCorrect: selectedAnswerIndex !== null && selectedAnswerIndex === correctAnswerIndex,
    isFlagged: flaggedQuestions.includes(index + 1),
    difficulty: question.difficulty || "mixed",
    itemDifficulty: question.itemDifficulty ?? null,
    explanation: question.explanation,
    audio: question.audioPath ? { path: question.audioPath } : null,
    graphic: question.graphicPath ? { path: question.graphicPath } : null,
    image: question.imagePath ? { path: question.imagePath } : null,
  };
}

export const attemptsService = {
  async getPracticeAttemptResult(attemptId: number) {
    return apiRequest<PracticeAttemptResult>(`/api/attempts/practice/${attemptId}`, {
      auth: true,
    });
  },

  async getMockTestAttemptResult(attemptId: number) {
    return apiRequest<PracticeAttemptResult>(`/api/attempts/mock-test/${attemptId}`, {
      auth: true,
    });
  },

  async submitPracticeAttempt({
    questions,
    answers,
    flaggedQuestions,
    timeSpentSeconds,
    source,
    mode,
    difficulty,
    title,
    subtitle,
    startedAtUtc,
  }: SubmitPracticeAttemptInput) {
    const answerPayloads = questions.map((question, index) =>
      toAnswerPayload(question, index, answers, flaggedQuestions),
    );
    const answeredCount = answerPayloads.filter(
      (answer) => answer.selectedAnswerIndex !== null,
    ).length;
    const correctCount = answerPayloads.filter((answer) => answer.isCorrect).length;
    const accuracyPct =
      questions.length > 0 ? Number(((correctCount / questions.length) * 100).toFixed(2)) : 0;
    const selectedParts = Array.from(
      new Set(questions.map((question) => question.partNumber)),
    ).sort((a, b) => a - b);

    return apiRequest<SavePracticeAttemptResponse>("/api/attempts/practice", {
      method: "POST",
      auth: true,
      body: JSON.stringify({
        title:
          title ||
          (selectedParts.length === 1
            ? `TOEIC Part ${selectedParts[0]} Practice`
            : "TOEIC Mixed Practice"),
        subtitle: subtitle || `${questions.length} questions`,
        attemptId: questions[0]?.attemptId ?? null,
        source: source || (mode === "weekly-check" ? "weeklycheck" : "practice"),
        mode,
        parts: selectedParts.join(","),
        difficulty,
        totalQuestions: questions.length,
        answeredCount,
        correctCount,
        accuracyPct,
        score: estimatePracticeScore(accuracyPct),
        timeSpentSeconds,
        startedAtUtc,
        submittedAtUtc: new Date().toISOString(),
        answers: answerPayloads,
      }),
    });
  },

  async submitMockTestAttempt({
    questions,
    answers,
    flaggedQuestions,
    timeSpentSeconds,
    title,
    source,
    attemptType = "mock-test",
    startedAtUtc,
  }: SubmitMockTestAttemptInput) {
    const answerPayloads = questions.map((question, index) =>
      toMockTestAnswerPayload(question, index, answers, flaggedQuestions),
    );
    const answeredCount = answerPayloads.filter(
      (answer) => answer.selectedAnswerIndex !== null,
    ).length;
    const correctCount = answerPayloads.filter((answer) => answer.isCorrect).length;
    const accuracyPct =
      questions.length > 0 ? Number(((correctCount / questions.length) * 100).toFixed(2)) : 0;
    const listeningAnswers = answerPayloads.filter((answer) => answer.part <= 4);
    const readingAnswers = answerPayloads.filter((answer) => answer.part >= 5);
    const listeningScore = estimateToeicSectionScore(
      listeningAnswers.filter((answer) => answer.isCorrect).length,
      listeningAnswers.length,
    );
    const readingScore = estimateToeicSectionScore(
      readingAnswers.filter((answer) => answer.isCorrect).length,
      readingAnswers.length,
    );

    return apiRequest<SavePracticeAttemptResponse>("/api/attempts/mock-test", {
      method: "POST",
      auth: true,
      body: JSON.stringify({
        attemptType,
        attemptId: questions[0]?.attemptId ?? null,
        source: source || (attemptType === "mini-test" || attemptType === "minitest" ? "minitest" : "fulltest"),
        title: title || (attemptType === "mini-test" ? "TOEIC Mini Test" : "TOEIC Mock Test"),
        totalQuestions: questions.length,
        answeredCount,
        correctCount,
        listeningScore,
        readingScore,
        totalScore: listeningScore + readingScore,
        accuracyPct,
        timeSpentSeconds,
        status: "submitted",
        startedAtUtc,
        submittedAtUtc: new Date().toISOString(),
        answers: answerPayloads,
      }),
    });
  },
};
