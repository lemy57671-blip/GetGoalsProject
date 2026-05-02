import { ApiError, apiRequest } from "@src/services/apiClient";

export type ReviewFilter =
  | "all"
  | "wrong"
  | "correct"
  | "bookmarked"
  | "notes"
  | "highlights"
  | "notebook";

export type ReviewOption = {
  optionLabel: string;
  optionTextEn: string;
  isCorrect: boolean;
  sortOrder: number;
};

export type ReviewNote = {
  id: number;
  questionId: number;
  attemptId?: number | null;
  noteText: string;
  createdAt: string;
  updatedAt: string;
};

export type ReviewHighlight = {
  id: number;
  questionId: number;
  attemptId?: number | null;
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
  queueId: number;
  questionId: number;
  questionNumber?: number | null;
  question: string;
  passageText?: string | null;
  options: string[];
  optionRows: ReviewOption[];
  userAnswer: string;
  userAnswerLabel?: string | null;
  correctAnswer: string;
  correctAnswerLabel?: string | null;
  isCorrect: boolean;
  explanation: string;
  optionAnalysis?: string | null;
  vocabularyNotes?: string | null;
  translationVi?: string | null;
  finalTranslationVi?: string | null;
  skill: string;
  subskill: string;
  part: number;
  difficulty: "easy" | "medium" | "hard" | "mixed";
  status: string;
  sourceAttemptType?: string | null;
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

type ReviewOptionResponse = {
  option_label?: string;
  optionLabel?: string;
  option_text_en?: string;
  optionTextEn?: string;
  is_correct?: boolean;
  isCorrect?: boolean;
  sort_order?: number;
  sortOrder?: number;
};

type NoteResponse = {
  id: number;
  question_id?: number;
  questionId?: number;
  attempt_id?: number | null;
  attemptId?: number | null;
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
  attempt_id?: number | null;
  attemptId?: number | null;
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
  question_id?: number;
  questionId?: number;
  question_number?: number | null;
  questionNumber?: number | null;
  part_number?: number | null;
  partNumber?: number | null;
  question_text_en?: string;
  questionTextEn?: string;
  passage_text?: string | null;
  passageText?: string | null;
  options?: ReviewOptionResponse[];
  correct_option_label?: string | null;
  correctOptionLabel?: string | null;
  correct_answer_text?: string | null;
  correctAnswerText?: string | null;
  explanation_detail?: string | null;
  explanationDetail?: string | null;
  option_analysis?: string | null;
  optionAnalysis?: string | null;
  vocabulary_notes?: string | null;
  vocabularyNotes?: string | null;
  translation_vi?: string | null;
  translationVi?: string | null;
  final_translation_vi?: string | null;
  finalTranslationVi?: string | null;
  user_selected_option_label?: string | null;
  userSelectedOptionLabel?: string | null;
  is_correct?: boolean | null;
  isCorrect?: boolean | null;
  bookmarked?: boolean;
  notes?: NoteResponse[];
  highlights?: HighlightResponse[];
  source_attempt_id?: number | null;
  sourceAttemptId?: number | null;
  source_type?: string | null;
  sourceType?: string | null;
  source_queue_id?: number | null;
  sourceQueueId?: number | null;
  status?: string;
};

export type HighlightCreatePayload = {
  question_id?: number;
  questionId?: number;
  attempt_id?: number | null;
  attemptId?: number | null;
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

function normalizeDifficulty(): ReviewQueueQuestion["difficulty"] {
  return "mixed";
}

function mapOption(option: ReviewOptionResponse): ReviewOption {
  return {
    optionLabel: option.option_label || option.optionLabel || "",
    optionTextEn: option.option_text_en || option.optionTextEn || "",
    isCorrect: Boolean(option.is_correct ?? option.isCorrect),
    sortOrder: Number(option.sort_order ?? option.sortOrder ?? 0),
  };
}

function mapNote(note: NoteResponse): ReviewNote {
  return {
    id: note.id,
    questionId: Number(note.question_id ?? note.questionId ?? 0),
    attemptId: note.attempt_id ?? note.attemptId ?? null,
    noteText: note.note_text ?? note.noteText ?? "",
    createdAt: note.created_at ?? note.createdAt ?? "",
    updatedAt: note.updated_at ?? note.updatedAt ?? "",
  };
}

function mapHighlight(highlight: HighlightResponse): ReviewHighlight {
  return {
    id: highlight.id,
    questionId: Number(highlight.question_id ?? highlight.questionId ?? 0),
    attemptId: highlight.attempt_id ?? highlight.attemptId ?? null,
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
  return option ? `${option.optionLabel}. ${option.optionTextEn}` : label;
}

function buildSkillLabel(part: number) {
  if (!part) return "TOEIC review";
  if (part <= 4) return "Listening";
  if (part === 5) return "Grammar & Vocabulary";
  return "Reading";
}

function mapReviewItem(item: ReviewItemResponse): ReviewQueueQuestion {
  const questionId = Number(item.question_id ?? item.questionId ?? 0);
  const part = Number(item.part_number ?? item.partNumber ?? 0);
  const questionNumber = item.question_number ?? item.questionNumber ?? null;
  const options = (item.options || []).map(mapOption).sort((a, b) => a.sortOrder - b.sortOrder);
  const correctLabel = item.correct_option_label ?? item.correctOptionLabel ?? null;
  const userLabel = item.user_selected_option_label ?? item.userSelectedOptionLabel ?? null;
  const explanation =
    item.explanation_detail ||
    item.explanationDetail ||
    item.option_analysis ||
    item.optionAnalysis ||
    item.vocabulary_notes ||
    item.vocabularyNotes ||
    "";

  return {
    id: questionId,
    queueId: Number(item.source_queue_id ?? item.sourceQueueId ?? questionId),
    questionId,
    questionNumber,
    question: item.question_text_en ?? item.questionTextEn ?? "",
    passageText: item.passage_text ?? item.passageText ?? null,
    options: options.map((option) => option.optionTextEn),
    optionRows: options,
    userAnswer: answerTextFromLabel(options, userLabel),
    userAnswerLabel: userLabel,
    correctAnswer: item.correct_answer_text ?? item.correctAnswerText ?? answerTextFromLabel(options, correctLabel),
    correctAnswerLabel: correctLabel,
    userAnswerIndex: optionIndexFromLabel(userLabel),
    correctAnswerIndex: optionIndexFromLabel(correctLabel),
    isCorrect: Boolean(item.is_correct ?? item.isCorrect),
    explanation,
    optionAnalysis: item.option_analysis ?? item.optionAnalysis ?? null,
    vocabularyNotes: item.vocabulary_notes ?? item.vocabularyNotes ?? null,
    translationVi: item.translation_vi ?? item.translationVi ?? null,
    finalTranslationVi: item.final_translation_vi ?? item.finalTranslationVi ?? null,
    skill: buildSkillLabel(part),
    subskill: item.source_type ?? item.sourceType ?? "review",
    part,
    difficulty: normalizeDifficulty(),
    status: item.status || "active",
    sourceAttemptType: item.source_type ?? item.sourceType ?? null,
    sourceAttemptId: item.source_attempt_id ?? item.sourceAttemptId ?? null,
    notes: (item.notes || []).map(mapNote),
    highlights: (item.highlights || []).map(mapHighlight),
    bookmarked: Boolean(item.bookmarked),
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

export const reviewService = {
  async getReviewItems(filter: ReviewFilter = "all", limit = 50): Promise<ReviewQueueQuestion[]> {
    try {
      const params = new URLSearchParams({ filter, limit: String(limit) });
      const items = await apiRequest<ReviewItemResponse[]>(`/api/review/items?${params.toString()}`, {
        auth: true,
      });
      return items.map(mapReviewItem);
    } catch (error) {
      if (error instanceof ApiError && [401, 403].includes(error.status)) return [];
      throw error;
    }
  },

  async getSummary(): Promise<ReviewSummaryView> {
    const questions = await this.getReviewItems("all", 50);
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

  async getNotes(questionId: number): Promise<ReviewNote[]> {
    const params = new URLSearchParams({ question_id: String(questionId) });
    const notes = await apiRequest<NoteResponse[]>(`/api/review/notes?${params.toString()}`, {
      auth: true,
    });
    return notes.map(mapNote);
  },

  async saveNote(questionId: number, noteText: string, attemptId?: number | null): Promise<ReviewNote> {
    const note = await apiRequest<NoteResponse>("/api/review/notes", {
      method: "POST",
      auth: true,
      body: JSON.stringify({
        question_id: questionId,
        attempt_id: attemptId ?? null,
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

  async getHighlights(questionId: number): Promise<ReviewHighlight[]> {
    const params = new URLSearchParams({ question_id: String(questionId) });
    const highlights = await apiRequest<HighlightResponse[]>(`/api/review/highlights?${params.toString()}`, {
      auth: true,
    });
    return highlights.map(mapHighlight);
  },

  async createHighlight(payload: HighlightCreatePayload): Promise<ReviewHighlight> {
    const requestPayload = {
      question_id: payload.question_id ?? payload.questionId,
      attempt_id: payload.attempt_id ?? payload.attemptId ?? null,
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

  async getBookmark(questionId: number): Promise<boolean> {
    const params = new URLSearchParams({ question_id: String(questionId) });
    const response = await apiRequest<{ bookmarked?: boolean }>(`/api/review/bookmarks?${params.toString()}`, {
      auth: true,
    });
    return Boolean(response.bookmarked);
  },

  async toggleBookmark(questionId: number, attemptId?: number | null): Promise<boolean> {
    const response = await apiRequest<{ bookmarked?: boolean }>("/api/review/bookmarks/toggle", {
      method: "POST",
      auth: true,
      body: JSON.stringify({
        question_id: questionId,
        attempt_id: attemptId ?? null,
      }),
    });
    return Boolean(response.bookmarked);
  },
};
