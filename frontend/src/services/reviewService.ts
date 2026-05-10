import { ApiError, apiRequest } from "@src/services/apiClient";

export type ReviewFilter =
  | "all"
  | "wrong"
  | "skipped"
  | "correct"
  | "bookmarked"
  | "noted"
  | "highlighted"
  | "notes"
  | "highlights"
  | "notebook";

export type ReviewSourceFilter =
  | "all"
  | "practice"
  | "fulltest"
  | "minitest"
  | "weeklycheck"
  | "diagnostic";

export type ReviewOption = {
  optionLabel: string;
  optionTextEn: string;
  isCorrect: boolean | null;
  sortOrder: number;
  optionKey?: string | null;
  optionText?: string | null;
};

export type ReviewAsset = {
  path?: string | null;
};

export type ReviewPassage = {
  id?: number | null;
  groupCode?: string | null;
  title?: string | null;
  text?: string | null;
  passageText?: string | null;
  audioPath?: string | null;
  imagePath?: string | null;
  audio?: ReviewAsset | null;
  image?: ReviewAsset | null;
};

export type ReviewNote = {
  id: number;
  questionId: number;
  source?: string | null;
  attemptId?: number | null;
  runtimeQuestionId?: number | null;
  diagnosticQuestionId?: number | null;
  noteText: string;
  createdAt: string;
  updatedAt: string;
};

export type ReviewHighlight = {
  id: number;
  questionId: number;
  source?: string | null;
  attemptId?: number | null;
  runtimeQuestionId?: number | null;
  diagnosticQuestionId?: number | null;
  targetType: string;
  targetKey?: string | null;
  selectedText: string;
  startOffset?: number | null;
  endOffset?: number | null;
  color: string;
  noteText?: string | null;
  createdAt: string;
  updatedAt: string;
};

export type ReviewQueueQuestion = {
  id: number;
  missingReason?: string | null;
  queueId: number;
  questionId: number;
  runtimeQuestionId?: number | null;
  diagnosticQuestionId?: number | null;
  docxQuestionId?: number | null;
  sourceQuestionId?: number | null;
  questionNumber?: number | null;
  section?: string | null;
  partLabel?: string | null;
  questionType?: string | null;
  question: string;
  questionText?: string | null;
  skillCode?: string | null;
  subskillCode?: string | null;
  topic?: string | null;
  passageText?: string | null;
  passage?: ReviewPassage | null;
  audio?: ReviewAsset | null;
  image?: ReviewAsset | null;
  options: string[];
  optionRows: ReviewOption[];
  userAnswer: string;
  userAnswerLabel?: string | null;
  selectedOptionKey?: string | null;
  correctAnswer: string;
  correctAnswerLabel?: string | null;
  correctOptionKey?: string | null;
  isCorrect: boolean;
  isSkipped?: boolean;
  reviewReason?: string | null;
  reviewReasons?: string[];
  hasNote?: boolean;
  hasHighlight?: boolean;
  isBookmarked?: boolean;
  explanation: string;
  optionAnalysis?: string | null;
  vocabularyNotes?: string | null;
  rawExplanation?: string | null;
  rawBlock?: string | null;
  translationVi?: string | null;
  finalTranslationVi?: string | null;
  skill: string;
  subskill: string;
  part: number;
  difficulty: "easy" | "medium" | "hard" | "mixed";
  status: string;
  sourceAttemptType?: string | null;
  sourceType?: ReviewSourceFilter | string | null;
  sourceLabel?: string | null;
  attemptType?: string | null;
  source?: string | null;
  sourceAttemptId?: number | null;
  notes: ReviewNote[];
  highlights: ReviewHighlight[];
  bookmarked: boolean;
  addedAtUtc?: string;
  reviewedAtUtc?: string | null;
  userAnswerIndex?: number | null;
  correctAnswerIndex?: number | null;
  passageTitle?: string | null;
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

export type ReviewSummaryStats = {
  wrongCount: number;
  skippedCount: number;
  wrongCardCount: number;
  notedCount: number;
  highlightedCount: number;
  bookmarkedCount: number;
  totalReviewQuestions: number;
  stabilityPercent: number;
};

type ReviewOptionResponse = {
  option_label?: string;
  optionLabel?: string;
  option_key?: string | null;
  optionKey?: string | null;
  key?: string | null;
  option_text_en?: string;
  optionTextEn?: string;
  option_text?: string | null;
  optionText?: string | null;
  text?: string | null;
  is_correct?: boolean;
  isCorrect?: boolean;
  sort_order?: number;
  sortOrder?: number;
};

type ReviewAssetResponse = {
  path?: string | null;
};

type ReviewPassageResponse = {
  id?: number | null;
  group_code?: string | null;
  groupCode?: string | null;
  title?: string | null;
  text?: string | null;
  passage_text?: string | null;
  passageText?: string | null;
  audio_path?: string | null;
  audioPath?: string | null;
  image_path?: string | null;
  imagePath?: string | null;
  audio?: ReviewAssetResponse | null;
  image?: ReviewAssetResponse | null;
};

type NoteResponse = {
  id: number;
  question_id?: number;
  questionId?: number;
  source?: string | null;
  attempt_id?: number | null;
  attemptId?: number | null;
  runtime_question_id?: number | null;
  runtimeQuestionId?: number | null;
  diagnostic_question_id?: number | null;
  diagnosticQuestionId?: number | null;
  note_text?: string;
  noteText?: string;
  created_at?: string;
  createdAt?: string;
  updated_at?: string;
  updatedAt?: string;
};

type HighlightResponse = {
  id: number;
  question_id?: number;
  questionId?: number;
  source?: string | null;
  attempt_id?: number | null;
  attemptId?: number | null;
  runtime_question_id?: number | null;
  runtimeQuestionId?: number | null;
  diagnostic_question_id?: number | null;
  diagnosticQuestionId?: number | null;
  target_type?: string;
  targetType?: string;
  target_key?: string | null;
  targetKey?: string | null;
  selected_text?: string;
  selectedText?: string;
  start_offset?: number | null;
  startOffset?: number | null;
  end_offset?: number | null;
  endOffset?: number | null;
  color?: string;
  note_text?: string | null;
  noteText?: string | null;
  created_at?: string;
  createdAt?: string;
  updated_at?: string;
  updatedAt?: string;
};

type ReviewItemResponse = {
  id?: number | null;
  question_id?: number;
  questionId?: number;
  missing_reason?: string | null;
  missingReason?: string | null;
  runtime_question_id?: number | null;
  runtimeQuestionId?: number | null;
  diagnostic_question_id?: number | null;
  diagnosticQuestionId?: number | null;
  docx_question_id?: number | null;
  docxQuestionId?: number | null;
  source_question_id?: number | null;
  sourceQuestionId?: number | null;
  question_number?: number | null;
  questionNumber?: number | null;
  part?: number | null;
  part_number?: number | null;
  partNumber?: number | null;
  section?: string | null;
  part_label?: string | null;
  partLabel?: string | null;
  question_type?: string | null;
  questionType?: string | null;
  skill_code?: string | null;
  skillCode?: string | null;
  subskill_code?: string | null;
  subskillCode?: string | null;
  topic?: string | null;
  difficulty?: string | null;
  test_number?: number | null;
  testNumber?: number | null;
  question_text_en?: string;
  questionTextEn?: string;
  question_text?: string;
  questionText?: string;
  passage_text?: string | null;
  passageText?: string | null;
  passage?: ReviewPassageResponse | null;
  audio?: ReviewAssetResponse | null;
  image?: ReviewAssetResponse | null;
  options?: ReviewOptionResponse[];
  correct_option_label?: string | null;
  correctOptionLabel?: string | null;
  correct_option_key?: string | null;
  correctOptionKey?: string | null;
  correct_answer_text?: string | null;
  correctAnswerText?: string | null;
  explanation_detail?: string | null;
  explanationDetail?: string | null;
  option_analysis?: string | null;
  optionAnalysis?: string | null;
  vocabulary_notes?: string | null;
  vocabularyNotes?: string | null;
  raw_explanation?: string | null;
  rawExplanation?: string | null;
  raw_block?: string | null;
  rawBlock?: string | null;
  translation_vi?: string | null;
  translationVi?: string | null;
  final_translation_vi?: string | null;
  finalTranslationVi?: string | null;
  user_selected_option_label?: string | null;
  userSelectedOptionLabel?: string | null;
  selected_option_key?: string | null;
  selectedOptionKey?: string | null;
  is_correct?: boolean | null;
  isCorrect?: boolean | null;
  is_skipped?: boolean;
  isSkipped?: boolean;
  review_reason?: string | null;
  reviewReason?: string | null;
  review_reasons?: string[];
  reviewReasons?: string[];
  has_note?: boolean;
  hasNote?: boolean;
  has_highlight?: boolean;
  hasHighlight?: boolean;
  is_bookmarked?: boolean;
  isBookmarked?: boolean;
  bookmarked?: boolean;
  notes?: NoteResponse[];
  highlights?: HighlightResponse[];
  source_attempt_id?: number | null;
  sourceAttemptId?: number | null;
  source_type?: string | null;
  sourceType?: string | null;
  source_label?: string | null;
  sourceLabel?: string | null;
  attempt_type?: string | null;
  attemptType?: string | null;
  source?: string | null;
  source_queue_id?: number | null;
  sourceQueueId?: number | null;
  status?: string;
};

type ReviewSummaryStatsResponse = {
  wrongCount?: number;
  wrong_count?: number;
  skippedCount?: number;
  skipped_count?: number;
  wrongCardCount?: number;
  wrong_card_count?: number;
  wrongReviewCount?: number;
  wrong_review_count?: number;
  noteCount?: number;
  note_count?: number;
  notedCount?: number;
  noted_count?: number;
  highlightCount?: number;
  highlight_count?: number;
  highlightedCount?: number;
  highlighted_count?: number;
  bookmarkCount?: number;
  bookmark_count?: number;
  bookmarkedCount?: number;
  bookmarked_count?: number;
  totalReviewQuestions?: number;
  total_review_questions?: number;
  stabilityPercent?: number;
  stability_percent?: number;
};

export type HighlightCreatePayload = {
  question_id?: number;
  questionId?: number;
  source?: ReviewSourceFilter | string | null;
  attempt_id?: number | null;
  attemptId?: number | null;
  runtime_question_id?: number | null;
  runtimeQuestionId?: number | null;
  diagnostic_question_id?: number | null;
  diagnosticQuestionId?: number | null;
  target_type?: string;
  targetType?: string;
  target_key?: string | null;
  targetKey?: string | null;
  selected_text?: string;
  selectedText?: string;
  start_offset?: number | null;
  startOffset?: number | null;
  end_offset?: number | null;
  endOffset?: number | null;
  color?: string;
  note_text?: string | null;
  noteText?: string | null;
};

type ReviewIdentityOptions = {
  source?: ReviewSourceFilter | string | null;
  attemptId?: number | null;
  runtimeQuestionId?: number | null;
  diagnosticQuestionId?: number | null;
};

function appendIdentityParams(params: URLSearchParams, questionId: number, options: ReviewIdentityOptions = {}) {
  if (options.source && options.source !== "all") params.set("source", String(options.source));
  if (options.attemptId && options.attemptId > 0) params.set("attemptId", String(options.attemptId));
  const runtimeQuestionId = runtimeIdForPayload(options.source, options.runtimeQuestionId, questionId);
  const diagnosticQuestionId = diagnosticIdForPayload(options.source, options.diagnosticQuestionId, questionId);
  if (runtimeQuestionId) params.set("runtimeQuestionId", String(runtimeQuestionId));
  if (diagnosticQuestionId) params.set("diagnosticQuestionId", String(diagnosticQuestionId));
}

function runtimeIdForPayload(source: ReviewSourceFilter | string | null | undefined, provided: number | null | undefined, questionId: number) {
  return normalizeReviewSource(source) === "diagnostic" ? null : (provided ?? questionId);
}

function diagnosticIdForPayload(source: ReviewSourceFilter | string | null | undefined, provided: number | null | undefined, questionId: number) {
  return normalizeReviewSource(source) === "diagnostic" ? (provided ?? questionId) : (provided ?? null);
}

function normalizeDifficulty(): ReviewQueueQuestion["difficulty"] {
  return "mixed";
}

function mapOption(option: ReviewOptionResponse): ReviewOption {
  const optionLabel = option.option_label || option.optionLabel || option.option_key || option.optionKey || option.key || "";
  const rawOptionText = option.option_text_en || option.optionTextEn || option.option_text || option.optionText || option.text || "";
  const optionText = rawOptionText && rawOptionText.trim() ? rawOptionText : optionLabel || "[Missing option text]";
  return {
    optionLabel,
    optionTextEn: optionText,
    isCorrect: Boolean(option.is_correct ?? option.isCorrect),
    sortOrder: Number(option.sort_order ?? option.sortOrder ?? 0),
    optionKey: option.option_key ?? option.optionKey ?? optionLabel,
    optionText: option.option_text ?? option.optionText ?? option.text ?? optionText,
  };
}

function mapAsset(asset?: ReviewAssetResponse | null): ReviewAsset | null {
  const path = asset?.path || null;
  return path ? { path } : null;
}

function mapPassage(
  passage?: ReviewPassageResponse | null,
  fallbackText?: string | null,
): ReviewPassage | null {
  const text = passage?.text ?? passage?.passage_text ?? passage?.passageText ?? fallbackText ?? null;
  const audioPath = passage?.audio_path ?? passage?.audioPath ?? passage?.audio?.path ?? null;
  const imagePath = passage?.image_path ?? passage?.imagePath ?? passage?.image?.path ?? null;
  const audio = mapAsset(passage?.audio ?? (audioPath ? { path: audioPath } : null));
  const image = mapAsset(passage?.image ?? (imagePath ? { path: imagePath } : null));
  const groupCode = passage?.group_code ?? passage?.groupCode ?? null;
  const id = passage?.id ?? null;
  const title = passage?.title ?? groupCode ?? null;

  if (!id && !groupCode && !title && !text && !audio && !image) return null;

  return {
    id,
    groupCode,
    title,
    text,
    passageText: text,
    audioPath,
    imagePath,
    audio,
    image,
  };
}

function mapNote(note: NoteResponse): ReviewNote {
  return {
    id: note.id,
    questionId: Number(note.question_id ?? note.questionId ?? 0),
    source: note.source ?? null,
    attemptId: note.attempt_id ?? note.attemptId ?? null,
    runtimeQuestionId: note.runtime_question_id ?? note.runtimeQuestionId ?? null,
    diagnosticQuestionId: note.diagnostic_question_id ?? note.diagnosticQuestionId ?? null,
    noteText: note.note_text ?? note.noteText ?? "",
    createdAt: note.created_at ?? note.createdAt ?? "",
    updatedAt: note.updated_at ?? note.updatedAt ?? "",
  };
}

function mapHighlight(highlight: HighlightResponse): ReviewHighlight {
  return {
    id: highlight.id,
    questionId: Number(highlight.question_id ?? highlight.questionId ?? 0),
    source: highlight.source ?? null,
    attemptId: highlight.attempt_id ?? highlight.attemptId ?? null,
    runtimeQuestionId: highlight.runtime_question_id ?? highlight.runtimeQuestionId ?? null,
    diagnosticQuestionId: highlight.diagnostic_question_id ?? highlight.diagnosticQuestionId ?? null,
    targetType: highlight.target_type ?? highlight.targetType ?? "question_text",
    targetKey: highlight.target_key ?? highlight.targetKey ?? null,
    selectedText: highlight.selected_text ?? highlight.selectedText ?? "",
    startOffset: highlight.start_offset ?? highlight.startOffset ?? null,
    endOffset: highlight.end_offset ?? highlight.endOffset ?? null,
    color: highlight.color || "yellow",
    noteText: highlight.note_text ?? highlight.noteText ?? null,
    createdAt: highlight.created_at ?? highlight.createdAt ?? "",
    updatedAt: highlight.updated_at ?? highlight.updatedAt ?? "",
  };
}

function optionIndexFromLabel(label?: string | null) {
  const normalized = (label || "").trim().toUpperCase();
  if (!/^[A-Z]$/.test(normalized)) return null;
  return normalized.charCodeAt(0) - "A".charCodeAt(0);
}

function answerTextFromLabel(options: ReviewOption[], label?: string | null) {
  if (!label) return "";
  const option = options.find((item) => item.optionLabel.toUpperCase() === label.toUpperCase());
  return option ? option.optionTextEn : label;
}

function reviewUniqueKey(item: ReviewQueueQuestion) {
  return `${item.sourceType || item.source || "all"}:${item.sourceAttemptId ?? "all"}:${
    item.runtimeQuestionId ?? item.diagnosticQuestionId ?? item.questionId
  }`;
}

const reviewSourceOrder: Record<string, number> = {
  practice: 0,
  fulltest: 1,
  minitest: 2,
  weeklycheck: 3,
  diagnostic: 4,
};

function getReviewOrder(item: ReviewQueueQuestion) {
  return item.questionNumber ?? item.runtimeQuestionId ?? item.diagnosticQuestionId ?? item.questionId ?? item.id ?? 0;
}

function sortReviewItems(items: ReviewQueueQuestion[]) {
  return [...items].sort((left, right) => {
    const leftSource = normalizeReviewSource(left.sourceType || left.source);
    const rightSource = normalizeReviewSource(right.sourceType || right.source);
    return (
      (reviewSourceOrder[leftSource] ?? 99) - (reviewSourceOrder[rightSource] ?? 99) ||
      (left.sourceAttemptId ?? 0) - (right.sourceAttemptId ?? 0) ||
      getReviewOrder(left) - getReviewOrder(right) ||
      (left.id ?? 0) - (right.id ?? 0)
    );
  });
}

function dedupeReviewItems(items: ReviewQueueQuestion[]) {
  const unique = new Map<string, ReviewQueueQuestion>();
  for (const item of items) {
    const key = reviewUniqueKey(item);
    if (!unique.has(key)) unique.set(key, item);
  }
  return sortReviewItems(Array.from(unique.values()));
}

function buildSkillLabel(part: number) {
  if (!part) return "TOEIC review";
  if (part <= 4) return "Listening";
  if (part === 5) return "Grammar & Vocabulary";
  return "Reading";
}

function normalizeReviewSource(value?: string | null): ReviewSourceFilter {
  const normalized = (value || "all").trim().toLowerCase().replace(/-/g, "_");
  if (normalized === "practice") return "practice";
  if (["full", "full_test", "fulltest", "mock", "mock_test"].includes(normalized)) return "fulltest";
  if (["mini", "mini_test", "minitest"].includes(normalized)) return "minitest";
  if (["weekly", "weekly_check", "weeklycheck"].includes(normalized)) return "weeklycheck";
  if (["diagnostic", "placement", "placement_test"].includes(normalized)) return "diagnostic";
  return "all";
}

export function getReviewSourceLabel(source?: string | null) {
  const normalized = normalizeReviewSource(source);
  return {
    all: "Tất cả",
    practice: "Bài tập",
    fulltest: "Full Test",
    minitest: "Mini Test",
    weeklycheck: "Weekly Check",
    diagnostic: "Diagnostic",
  }[normalized];
}

const missingOptionWarningKeys = new Set<string>();

function mapReviewItem(item: ReviewItemResponse): ReviewQueueQuestion {
  const questionId = Number(item.question_id ?? item.questionId ?? 0);
  const part = Number(item.part_number ?? item.partNumber ?? item.part ?? 0);
  const questionNumber = item.question_number ?? item.questionNumber ?? null;
  const options = (item.options || []).map(mapOption).sort((a, b) => a.sortOrder - b.sortOrder);
  const correctLabel = item.correct_option_key ?? item.correctOptionKey ?? item.correct_option_label ?? item.correctOptionLabel ?? null;
  const userLabel = item.selected_option_key ?? item.selectedOptionKey ?? item.user_selected_option_label ?? item.userSelectedOptionLabel ?? null;
  const rawCorrectAnswerText = item.correct_answer_text ?? item.correctAnswerText ?? "";
  const correctAnswerText =
    rawCorrectAnswerText &&
    rawCorrectAnswerText.trim() &&
    rawCorrectAnswerText.trim().toUpperCase() !== (correctLabel || "").trim().toUpperCase()
      ? rawCorrectAnswerText
      : answerTextFromLabel(options, correctLabel);
  const fallbackPassageText = item.passage_text ?? item.passageText ?? null;
  const passage = mapPassage(item.passage, fallbackPassageText);
  const audio = mapAsset(item.audio ?? null) || passage?.audio || null;
  const image = mapAsset(item.image ?? null) || passage?.image || null;
  const questionText = item.question_text_en ?? item.questionTextEn ?? item.question_text ?? item.questionText ?? "";
  const sourceType = normalizeReviewSource(
    item.source_type ?? item.sourceType ?? item.attempt_type ?? item.attemptType ?? item.source,
  );
  const sourceLabel = item.source_label ?? item.sourceLabel ?? getReviewSourceLabel(sourceType);
  const explanation =
    item.explanation_detail ||
    item.explanationDetail ||
    item.raw_explanation ||
    item.rawExplanation ||
    item.option_analysis ||
    item.optionAnalysis ||
    item.vocabulary_notes ||
    item.vocabularyNotes ||
    "";
  const missingOptionLabels = options
    .filter((option) => option.optionTextEn === "[Missing option text]")
    .map((option) => option.optionLabel || "?");

  const warningKey = `${sourceType}:${item.runtime_question_id ?? item.runtimeQuestionId ?? questionId}`;
  if (import.meta.env.DEV && missingOptionLabels.length > 0 && !missingOptionWarningKeys.has(warningKey)) {
    missingOptionWarningKeys.add(warningKey);
    console.warn("Review question is missing option text", {
      questionId,
      runtimeQuestionId: item.runtime_question_id ?? item.runtimeQuestionId ?? null,
      part,
      missingOptions: missingOptionLabels,
      missingReason: item.missing_reason ?? item.missingReason ?? null,
    });
  }

  return {
    id: Number(item.id ?? questionId),
    missingReason: item.missing_reason ?? item.missingReason ?? null,
    queueId: Number(item.source_queue_id ?? item.sourceQueueId ?? questionId),
    questionId,
    runtimeQuestionId: item.runtime_question_id ?? item.runtimeQuestionId ?? null,
    diagnosticQuestionId: item.diagnostic_question_id ?? item.diagnosticQuestionId ?? null,
    docxQuestionId: item.docx_question_id ?? item.docxQuestionId ?? null,
    sourceQuestionId: item.source_question_id ?? item.sourceQuestionId ?? null,
    questionNumber,
    section: item.section ?? null,
    partLabel: item.part_label ?? item.partLabel ?? (part ? `Part ${part}` : null),
    questionType: item.question_type ?? item.questionType ?? null,
    question: questionText,
    questionText,
    skillCode: item.skill_code ?? item.skillCode ?? null,
    subskillCode: item.subskill_code ?? item.subskillCode ?? null,
    topic: item.topic ?? null,
    passageText: passage?.text ?? fallbackPassageText,
    passage,
    audio,
    image,
    options: options.map((option) => option.optionTextEn),
    optionRows: options,
    userAnswer: answerTextFromLabel(options, userLabel),
    userAnswerLabel: userLabel,
    selectedOptionKey: userLabel,
    correctAnswer: correctAnswerText,
    correctAnswerLabel: correctLabel,
    correctOptionKey: correctLabel,
    userAnswerIndex: optionIndexFromLabel(userLabel),
    correctAnswerIndex: optionIndexFromLabel(correctLabel),
    isCorrect: item.is_correct ?? item.isCorrect ?? null,
    isSkipped: Boolean(item.is_skipped ?? item.isSkipped),
    reviewReason: item.review_reason ?? item.reviewReason ?? null,
    reviewReasons: item.review_reasons ?? item.reviewReasons ?? [],
    hasNote: Boolean(item.has_note ?? item.hasNote ?? (item.notes || []).length > 0),
    hasHighlight: Boolean(item.has_highlight ?? item.hasHighlight ?? (item.highlights || []).length > 0),
    isBookmarked: Boolean(item.is_bookmarked ?? item.isBookmarked ?? item.bookmarked),
    explanation,
    optionAnalysis: item.option_analysis ?? item.optionAnalysis ?? null,
    vocabularyNotes: item.vocabulary_notes ?? item.vocabularyNotes ?? null,
    rawExplanation: item.raw_explanation ?? item.rawExplanation ?? null,
    rawBlock: item.raw_block ?? item.rawBlock ?? null,
    translationVi: item.translation_vi ?? item.translationVi ?? null,
    finalTranslationVi: item.final_translation_vi ?? item.finalTranslationVi ?? null,
    skill: item.skill_code ?? item.skillCode ?? buildSkillLabel(part),
    subskill: item.subskill_code ?? item.subskillCode ?? item.source_type ?? item.sourceType ?? "review",
    part,
    difficulty: (item.difficulty as ReviewQueueQuestion["difficulty"]) || normalizeDifficulty(),
    status: item.status || "active",
    sourceAttemptType: item.source_type ?? item.sourceType ?? null,
    sourceType,
    sourceLabel,
    attemptType: item.attempt_type ?? item.attemptType ?? sourceType,
    source: item.source ?? item.source_type ?? item.sourceType ?? sourceType,
    sourceAttemptId: item.source_attempt_id ?? item.sourceAttemptId ?? null,
    notes: (item.notes || []).map(mapNote),
    highlights: (item.highlights || []).map(mapHighlight),
    bookmarked: Boolean(item.bookmarked),
    audioUrl: audio?.path ?? null,
    imageUrl: image?.path ?? null,
    graphicUrl: image?.path ?? null,
  };
}

function buildSkillBreakdown(questions: ReviewQueueQuestion[]) {
  const grouped = new Map<string, ReviewQueueQuestion[]>();
  questions.forEach((question) => {
    grouped.set(question.skill, [...(grouped.get(question.skill) || []), question]);
  });
  return Array.from(grouped.entries()).map(([name, items]) => ({
    name,
    correct: items.filter((item) => item.isCorrect).length,
    total: items.length,
  }));
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
      correct: items.filter((item) => item.isCorrect).length,
      total: items.length,
    }));
}

function mapReviewSummaryStats(summary: ReviewSummaryStatsResponse): ReviewSummaryStats {
  const wrongCount = Number(summary.wrongCount ?? summary.wrong_count ?? 0);
  const skippedCount = Number(summary.skippedCount ?? summary.skipped_count ?? 0);
  const wrongCardCount = Number(
    summary.wrongCardCount ?? summary.wrong_card_count ?? summary.wrongReviewCount ?? summary.wrong_review_count ?? wrongCount + skippedCount,
  );
  return {
    wrongCount,
    skippedCount,
    wrongCardCount,
    notedCount: Number(summary.noteCount ?? summary.note_count ?? summary.notedCount ?? summary.noted_count ?? 0),
    highlightedCount: Number(summary.highlightCount ?? summary.highlight_count ?? summary.highlightedCount ?? summary.highlighted_count ?? 0),
    bookmarkedCount: Number(summary.bookmarkCount ?? summary.bookmark_count ?? summary.bookmarkedCount ?? summary.bookmarked_count ?? 0),
    totalReviewQuestions: Number(summary.totalReviewQuestions ?? summary.total_review_questions ?? 0),
    stabilityPercent: Math.max(0, Math.min(100, Number(summary.stabilityPercent ?? summary.stability_percent ?? 100))),
  };
}

export const reviewService = {
  async getReviewItems(
    filter: ReviewFilter = "all",
    limit = 500,
    options: { source?: ReviewSourceFilter | string; attemptId?: number | null } = {},
  ): Promise<ReviewQueueQuestion[]> {
    try {
      const params = new URLSearchParams({ filter, limit: String(limit) });
      const source = normalizeReviewSource(options.source);
      if (source !== "all") {
        params.set("source", source);
      }
      if (source !== "all" && options.attemptId && options.attemptId > 0) {
        params.set("attemptId", String(options.attemptId));
      }
      const items = await apiRequest<ReviewItemResponse[]>(`/api/review/items?${params.toString()}`, {
        auth: true,
      });
      return dedupeReviewItems(items.map(mapReviewItem));
    } catch (error) {
      if (error instanceof ApiError && [401, 403].includes(error.status)) return [];
      throw error;
    }
  },

  async getSummary(): Promise<ReviewSummaryView> {
    const questions = await this.getReviewItems("all", 500);
    return {
      pendingCount: questions.filter((item) => !item.isCorrect).length,
      reviewedCount: questions.filter((item) => item.isCorrect).length,
      topWeakSkills: buildSkillBreakdown(questions).map((item) => ({
        skill: item.name,
        accuracy: item.total > 0 ? Math.round((item.correct * 100) / item.total) : 0,
        attemptCount: item.total,
      })),
      questions,
      skillBreakdown: buildSkillBreakdown(questions),
      partBreakdown: buildPartBreakdown(questions),
    };
  },

  async getItem(itemId: number): Promise<ReviewQueueQuestion> {
    const items = await this.getReviewItems("all", 100);
    return items.find((item) => item.queueId === itemId || item.questionId === itemId) || items[0];
  },

  async markReviewed(itemId: number): Promise<ReviewQueueQuestion> {
    await apiRequest(`/api/review/item/${itemId}/mark-reviewed`, {
      method: "POST",
      auth: true,
    });
    return this.getItem(itemId);
  },

  async getNotes(questionId: number, options: ReviewIdentityOptions = {}): Promise<ReviewNote[]> {
    const params = new URLSearchParams({ question_id: String(questionId) });
    appendIdentityParams(params, questionId, options);
    const notes = await apiRequest<NoteResponse[]>(`/api/review/notes?${params.toString()}`, {
      auth: true,
    });
    return notes.map(mapNote);
  },

  async getReviewSummaryStats(
    filter: ReviewFilter = "all",
    options: { source?: ReviewSourceFilter | string; attemptId?: number | null } = {},
  ): Promise<ReviewSummaryStats> {
    const params = new URLSearchParams({ filter });
    const source = normalizeReviewSource(options.source);
    if (source !== "all") {
      params.set("source", source);
    }
    if (source !== "all" && options.attemptId && options.attemptId > 0) {
      params.set("attemptId", String(options.attemptId));
    }
    const summary = await apiRequest<ReviewSummaryStatsResponse>(`/api/review/summary?${params.toString()}`, {
      auth: true,
    });
    return mapReviewSummaryStats(summary);
  },

  async saveNote(
    questionId: number,
    noteText: string,
    attemptId?: number | null,
    options: ReviewIdentityOptions = {},
  ): Promise<ReviewNote> {
    const note = await apiRequest<NoteResponse>("/api/review/notes", {
      method: "POST",
      auth: true,
      body: JSON.stringify({
        question_id: questionId,
        source: options.source ?? "practice",
        attempt_id: attemptId ?? null,
        runtime_question_id: runtimeIdForPayload(options.source, options.runtimeQuestionId, questionId),
        diagnostic_question_id: diagnosticIdForPayload(options.source, options.diagnosticQuestionId, questionId),
        note_text: noteText,
      }),
    });
    return mapNote(note);
  },

  async updateNote(noteId: number, noteText: string): Promise<ReviewNote> {
    const note = await apiRequest<NoteResponse>(`/api/review/notes/${noteId}`, {
      method: "PUT",
      auth: true,
      body: JSON.stringify({ note_text: noteText }),
    });
    return mapNote(note);
  },

  async deleteNote(noteId: number) {
    return apiRequest(`/api/review/notes/${noteId}`, {
      method: "DELETE",
      auth: true,
    });
  },

  async getHighlights(questionId: number, options: ReviewIdentityOptions = {}): Promise<ReviewHighlight[]> {
    const params = new URLSearchParams({ question_id: String(questionId) });
    appendIdentityParams(params, questionId, options);
    const highlights = await apiRequest<HighlightResponse[]>(`/api/review/highlights?${params.toString()}`, {
      auth: true,
    });
    return highlights.map(mapHighlight);
  },

  async createHighlight(payload: HighlightCreatePayload): Promise<ReviewHighlight> {
    const requestPayload = {
      question_id: payload.question_id ?? payload.questionId,
      source: payload.source ?? "practice",
      attempt_id: payload.attempt_id ?? payload.attemptId ?? null,
      runtime_question_id: runtimeIdForPayload(
        payload.source,
        payload.runtime_question_id ?? payload.runtimeQuestionId,
        Number(payload.question_id ?? payload.questionId ?? 0),
      ),
      diagnostic_question_id: diagnosticIdForPayload(
        payload.source,
        payload.diagnostic_question_id ?? payload.diagnosticQuestionId,
        Number(payload.question_id ?? payload.questionId ?? 0),
      ),
      target_type: payload.target_type ?? payload.targetType ?? "question",
      target_key: payload.target_key ?? payload.targetKey ?? null,
      selected_text: payload.selected_text ?? payload.selectedText ?? "",
      start_offset: payload.start_offset ?? payload.startOffset ?? null,
      end_offset: payload.end_offset ?? payload.endOffset ?? null,
      color: payload.color ?? "yellow",
      note_text: payload.note_text ?? payload.noteText ?? null,
    };
    const highlight = await apiRequest<HighlightResponse>("/api/review/highlights", {
      method: "POST",
      auth: true,
      body: JSON.stringify(requestPayload),
    });
    return mapHighlight(highlight);
  },

  async deleteHighlight(highlightId: number) {
    return apiRequest(`/api/review/highlights/${highlightId}`, {
      method: "DELETE",
      auth: true,
    });
  },

  async getBookmark(questionId: number, options: ReviewIdentityOptions = {}): Promise<boolean> {
    const params = new URLSearchParams({ question_id: String(questionId) });
    appendIdentityParams(params, questionId, options);
    const response = await apiRequest<{ bookmarked?: boolean }>(`/api/review/bookmarks?${params.toString()}`, {
      auth: true,
    });
    return Boolean(response.bookmarked);
  },

  async toggleBookmark(
    questionId: number,
    attemptId?: number | null,
    options: ReviewIdentityOptions = {},
  ): Promise<boolean> {
    const response = await apiRequest<{ bookmarked?: boolean }>("/api/review/bookmarks/toggle", {
      method: "POST",
      auth: true,
      body: JSON.stringify({
        question_id: questionId,
        source: options.source ?? "practice",
        attempt_id: attemptId ?? null,
        runtime_question_id: runtimeIdForPayload(options.source, options.runtimeQuestionId, questionId),
        diagnostic_question_id: diagnosticIdForPayload(options.source, options.diagnosticQuestionId, questionId),
      }),
    });
    return Boolean(response.bookmarked);
  },
};
