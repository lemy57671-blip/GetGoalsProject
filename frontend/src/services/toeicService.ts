import { API_BASE_URL, ApiError, apiRequest } from "@src/services/apiClient";

export type ToeicPartItem = {
  id: string;
  number: number;
  name: string;
  tag: "listening" | "reading";
  description: string;
  count: number;
  audioReady: boolean;
  testsAvailable: number[];
};

export type ToeicRecommendationPack = {
  id: string;
  part: number;
  title: string;
  skill: string;
  why: string;
  difficulty: string;
  suggestedQuestionCount: number;
  audioReady: boolean;
};

export type ToeicRecommendations = {
  track: string;
  reason: string;
  recommendedPacks: ToeicRecommendationPack[];
};

export type ToeicRunnerQuestion = {
  id: number;
  questionId?: number | null;
  dbId?: number | null;
  sqlId?: number | null;
  docxQuestionId?: number | null;
  sourceQuestionId?: number | null;
  section: "Listening" | "Reading";
  partNumber: number;
  part: string;
  type: string;
  question: string;
  hasAudio: boolean;
  hasImage: boolean;
  audioPath?: string;
  imagePath?: string;
  graphicPath?: string;
  audioUrl?: string;
  imageUrl?: string;
  graphicUrl?: string;
  passage?: {
    id?: number | null;
    groupCode?: string | null;
    title?: string;
    text?: string;
    audioPath?: string;
    imagePath?: string;
    audioUrl?: string;
    imageUrl?: string;
  } | null;
  passageTitle?: string;
  passageText?: string;
  test: number;
  questionNumber: number;
  options: string[];
  correctAnswer?: string | null;
  correct: number;
  explanation: string;
  explanationDetail?: string | null;
  explanationText?: string | null;
  rawExplanation?: string | null;
  rawBlock?: string | null;
  optionAnalysis?: string | null;
  vocabularyNotes?: string | null;
  skill: string;
  subskill?: string | null;
  groupId?: string | null;
};

type ToeicSummaryResponse = {
  inventory?: {
    mappingRows?: number;
    audioFiles?: number;
    detectedParts?: number[];
  };
  parts?: Array<{
    part: number;
    name: string;
    skill: string;
    audioCount: number;
    count: number;
    testsAvailable: number[];
    sampleQuestionRange: string;
    audioReady: boolean;
  }>;
};

type ToeicRecommendationResponse = {
  track?: string;
  reason?: string;
  recommendedPacks?: ToeicRecommendationPack[];
};

type ToeicRunnerAssetResponse = {
  path?: string;
};

export type ToeicRunnerQuestionResponse = {
  id: number;
  questionId?: number | null;
  dbId?: number | null;
  sqlId?: number | null;
  docxQuestionId?: number | null;
  sourceQuestionId?: number | null;
  section?: string;
  part?: number;
  partLabel?: string;
  type?: string;
  question?: string;
  skill?: string;
  subskill?: string | null;
  options?: string[];
  correctAnswerIndex?: number | null;
  correctAnswer?: string | null;
  explanation?: string | null;
  explanationDetail?: string | null;
  explanationText?: string | null;
  explanation_detail?: string | null;
  explanation_text?: string | null;
  rawExplanation?: string | null;
  rawBlock?: string | null;
  raw_explanation?: string | null;
  raw_block?: string | null;
  optionAnalysis?: string | null;
  vocabularyNotes?: string | null;
  option_analysis?: string | null;
  vocabulary_notes?: string | null;
  image?: ToeicRunnerAssetResponse | null;
  graphic?: ToeicRunnerAssetResponse | null;
  audio?: ToeicRunnerAssetResponse | null;
  audioUrl?: string | null;
  passageTitle?: string | null;
  passageText?: string | null;
  passage_title?: string | null;
  passage_text?: string | null;
  passage?: {
    id?: number | null;
    groupCode?: string | null;
    group_code?: string | null;
    title?: string;
    text?: string;
    passageText?: string;
    PassageText?: string;
    audio?: ToeicRunnerAssetResponse | null;
    image?: ToeicRunnerAssetResponse | null;
  } | null;
  test?: number;
  questionNumber?: number;
  groupId?: string | null;
};

type ToeicReviewFocusRunnerResponse = {
  items?: ToeicRunnerQuestionResponse[];
  matchStrategy?: string;
  matchStrategiesUsed?: string[];
  sourceQuestionId?: number | null;
  excludedOriginal?: boolean;
  requestedCount?: number;
  returnedCount?: number;
  usedPart?: number | null;
  usedSkill?: string | null;
  usedSubskill?: string | null;
  usedDifficulty?: string | null;
};

export type ToeicReviewFocusRunnerResult = {
  questions: ToeicRunnerQuestion[];
  matchStrategy: string;
  matchStrategiesUsed: string[];
  sourceQuestionId?: number | null;
  excludedOriginal: boolean;
  requestedCount: number;
  returnedCount: number;
  usedPart?: number | null;
  usedSkill?: string | null;
  usedSubskill?: string | null;
  usedDifficulty: string;
};

const fallbackPartDescriptions: Record<number, string> = {
  1: "Photographs",
  2: "Question-Response",
  3: "Conversations",
  4: "Short Talks",
  5: "Incomplete Sentences",
  6: "Text Completion",
  7: "Reading Comprehension",
};

function toAssetUrl(path?: string | null) {
  if (!path) return undefined;
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

function firstNonEmpty(...values: Array<string | null | undefined>) {
  return values.find((value) => typeof value === "string" && value.trim().length > 0);
}

function normalizeRunnerPassage(
  passage?: ToeicRunnerQuestionResponse["passage"],
  fallbackTitle?: string | null,
  fallbackText?: string | null,
) {
  const text = firstNonEmpty(passage?.text, passage?.passageText, passage?.PassageText, fallbackText) || "";
  const title = firstNonEmpty(passage?.title, fallbackTitle) || "";
  const audioPath = passage?.audio?.path;
  const imagePath = passage?.image?.path;
  const groupCode = passage?.groupCode || passage?.group_code || null;

  if (!text && !title && !audioPath && !imagePath && !groupCode) {
    return null;
  }

  return {
    id: passage?.id,
    groupCode,
    title,
    text,
    audioPath,
    imagePath,
    audioUrl: toAssetUrl(audioPath),
    imageUrl: toAssetUrl(imagePath),
  };
}

function parseQuestionCount(sampleQuestionRange?: string) {
  if (!sampleQuestionRange) return 0;

  const [startRaw, endRaw] = sampleQuestionRange.split("-");
  const start = Number(startRaw);
  const end = Number(endRaw);

  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) {
    return 0;
  }

  return end - start + 1;
}

function mapSummaryPart(part: NonNullable<ToeicSummaryResponse["parts"]>[number]): ToeicPartItem {
  const number = part.part;
  const tag = number <= 4 ? "listening" : "reading";

  return {
    id: `part${number}`,
    number,
    name: `Part ${number}`,
    tag,
    description: part.name || fallbackPartDescriptions[number] || `Part ${number}`,
    count: part.count || 0,
    audioReady: part.audioReady,
    testsAvailable: part.testsAvailable || [],
  };
}

export function mapToeicRunnerQuestion(question: ToeicRunnerQuestionResponse): ToeicRunnerQuestion {
  const partNumber = question.part || 1;
  const section = partNumber <= 4 ? "Listening" : "Reading";
  const passage = normalizeRunnerPassage(
    question.passage,
    question.passageTitle || question.passage_title,
    question.passageText || question.passage_text,
  );
  const imageUrl = toAssetUrl(question.image?.path || passage?.imagePath);
  const graphicUrl = toAssetUrl(question.graphic?.path);
  const audioUrl = toAssetUrl(question.audio?.path || question.audioUrl || passage?.audioPath);

  return {
    id: question.id,
    questionId: question.questionId,
    dbId: question.dbId,
    sqlId: question.sqlId,
    docxQuestionId: question.docxQuestionId,
    sourceQuestionId: question.sourceQuestionId,
    section,
    partNumber,
    part: question.partLabel || `Part ${partNumber}`,
    type: question.type || "question",
    question: question.question || "",
    hasAudio: Boolean(audioUrl),
    hasImage: Boolean(imageUrl || graphicUrl),
    audioPath: question.audio?.path || question.audioUrl || undefined,
    imagePath: question.image?.path,
    graphicPath: question.graphic?.path,
    audioUrl,
    imageUrl,
    graphicUrl,
    passage,
    passageTitle: passage?.title,
    passageText: passage?.text,
    test: question.test || 0,
    questionNumber: question.questionNumber || 0,
    options: question.options || [],
    correctAnswer: question.correctAnswer,
    correct: typeof question.correctAnswerIndex === "number" ? question.correctAnswerIndex : -1,
    explanation: question.explanation || "No explanation is available for this question yet.",
    explanationDetail:
      question.explanationDetail ||
      question.explanation_detail ||
      question.explanationText ||
      question.explanation_text ||
      question.explanation ||
      null,
    explanationText: question.explanationText || question.explanation_text || null,
    rawExplanation: question.rawExplanation || question.raw_explanation || null,
    rawBlock: question.rawBlock || question.raw_block || null,
    optionAnalysis: question.optionAnalysis || question.option_analysis || null,
    vocabularyNotes: question.vocabularyNotes || question.vocabulary_notes || null,
    skill: question.skill || question.subskill || "TOEIC practice",
    subskill: question.subskill,
    groupId: question.groupId || passage?.groupCode,
  };
}

export const toeicService = {
  async getSummary() {
    const summary = await apiRequest<ToeicSummaryResponse>("/api/toeic/summary");
    return {
      inventory: summary.inventory,
      parts: (summary.parts || []).map(mapSummaryPart),
    };
  },

  async getRecommendationsForCurrentUser(): Promise<ToeicRecommendations | null> {
    try {
      const raw = await apiRequest<ToeicRecommendationResponse>(
        "/api/toeic/recommendations",
        { auth: true },
      );
      return {
        track: raw.track ?? "",
        reason: raw.reason ?? "",
        recommendedPacks: raw.recommendedPacks ?? [],
      };
    } catch (error) {
      if (error instanceof ApiError && [401, 403, 404].includes(error.status)) {
        return null;
      }

      throw error;
    }
  },

  async getPartRunner(part: number, limit: number, difficulty: string) {
    const params = new URLSearchParams({
      limit: String(limit),
      difficulty,
    });

    const questions = await apiRequest<ToeicRunnerQuestionResponse[]>(
      `/api/toeic/runner/part/${part}?${params.toString()}`,
      { auth: true },
    );

    return questions.map(mapToeicRunnerQuestion);
  },

  async getMixedRunner(parts: number[], count: number, difficulty: string) {
    const params = new URLSearchParams({
      parts: parts.join(","),
      count: String(count),
      difficulty,
    });

    const questions = await apiRequest<ToeicRunnerQuestionResponse[]>(
      `/api/toeic/runner/mixed?${params.toString()}`,
      { auth: true },
    );

    return questions.map(mapToeicRunnerQuestion);
  },

  async getQuestionsByIds(questionIds: number[]) {
    const params = new URLSearchParams({
      question_ids: questionIds.join(","),
    });

    const questions = await apiRequest<ToeicRunnerQuestionResponse[]>(
      `/api/toeic/runner/questions?${params.toString()}`,
      { auth: true },
    );

    return questions.map(mapToeicRunnerQuestion);
  },

  async getMiniTestRunner(test: number, parts: number[] | null, count: number | null) {
    const params = new URLSearchParams({
      test: String(test),
    });

    if (parts && parts.length > 0) {
      params.set("parts", parts.join(","));
    }

    if (count && count > 0) {
      params.set("count", String(count));
    }

    const questions = await apiRequest<ToeicRunnerQuestionResponse[]>(
      `/api/toeic/runner/minitest?${params.toString()}`,
      { auth: true },
    );

    return questions.map(mapToeicRunnerQuestion);
  },

  async getFullTestRunner(test: number) {
    const params = new URLSearchParams({
      test: String(test),
    });

    const questions = await apiRequest<ToeicRunnerQuestionResponse[]>(
      `/api/toeic/runner/fulltest?${params.toString()}`,
      { auth: true },
    );

    return questions.map(mapToeicRunnerQuestion);
  },

  async getReviewFocusRunner(
    reviewItemId: number,
    count: number,
    difficulty: string,
  ): Promise<ToeicReviewFocusRunnerResult> {
    const params = new URLSearchParams({
      reviewItemId: String(reviewItemId),
      count: String(count),
      difficulty,
    });

    const response = await apiRequest<ToeicReviewFocusRunnerResponse>(
      `/api/toeic/runner/review-focus?${params.toString()}`,
      { auth: true },
    );

    const questions = (response.items || []).map(mapToeicRunnerQuestion);

    return {
      questions,
      matchStrategy: response.matchStrategy || "no_match",
      matchStrategiesUsed: response.matchStrategiesUsed || [],
      sourceQuestionId: response.sourceQuestionId,
      excludedOriginal: response.excludedOriginal ?? true,
      requestedCount: response.requestedCount || count,
      returnedCount: response.returnedCount ?? questions.length,
      usedPart: response.usedPart,
      usedSkill: response.usedSkill,
      usedSubskill: response.usedSubskill,
      usedDifficulty: response.usedDifficulty || difficulty,
    };
  },
};
