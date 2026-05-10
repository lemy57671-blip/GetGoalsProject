import { API_BASE_URL, apiRequest, getAuthToken } from "@src/services/apiClient";

export type ChatIntent =
  | "word_meaning"
  | "collocation_preposition"
  | "gap_requirement"
  | "correct_answer"
  | "option_reason"
  | "full_option_analysis"
  | "translation"
  | "explanation"
  | "hint"
  | "grammar_structure"
  | "grammar_formula_request"
  | "target_completion_request"
  | "grammar_structure_definition"
  | "collocation_preposition_request"
  | "relative_pronoun_request"
  | "vocabulary_definition_only"
  | "vocabulary_lookup"
  | "answer_request"
  | "explanation_request"
  | "translation_request"
  | "vocabulary_request"
  | "option_analysis_request"
  | "grammar_request"
  | "question_goal_request"
  | "general_question"
  | "explain_question"
  | "grammar_help"
  | "vocabulary_help"
  | "translate"
  | "fix_sentence"
  | "generate_examples"
  | "study_plan"
  | "weak_skill_analysis"
  | "mock_test_review"
  | "weekly_check_advice"
  | "general_chat";

export type ChatQuestionOption =
  | string
  | {
      id?: number | string | null;
      label?: string | null;
      text?: string | null;
      content?: string | null;
      optionText?: string | null;
      value?: string | null;
      isCorrect?: boolean | null;
    };

export type ChatQuestionContext = {
  id?: number | string | null;
  questionId?: number | string | null;
  question_id?: number | string | null;
  runtimeQuestionId?: number | string | null;
  runtime_question_id?: number | string | null;
  runnerQuestionId?: number | string | null;
  runner_question_id?: number | string | null;
  diagnosticQuestionId?: number | string | null;
  diagnostic_question_id?: number | string | null;
  reviewItemId?: number | string | null;
  review_item_id?: number | string | null;
  docxQuestionId?: number | string | null;
  docx_question_id?: number | string | null;
  sourceQuestionId?: number | string | null;
  source_question_id?: number | string | null;
  sqlId?: number | string | null;
  source?: string | null;
  sourceType?: string | null;

  questionNumber?: number | string | null;
  question_number?: number | string | null;

  part?: number | string | null;
  Part?: number | string | null;
  partLabel?: string | null;
  part_label?: string | null;
  section?: string | null;

  questionText?: string | null;
  question_text?: string | null;
  text?: string | null;
  content?: string | null;
  prompt?: string | null;

  passageText?: string | null;
  passage_text?: string | null;
  passage?: string | Record<string, unknown> | null;
  passageTitle?: string | null;
  passage_title?: string | null;
  transcript?: string | null;

  options?: ChatQuestionOption[];
  choices?: ChatQuestionOption[];

  selectedAnswer?: unknown;
  selected_answer?: unknown;
  selectedOptionKey?: string | null;
  selected_option_key?: string | null;
  selectedOptionText?: string | null;
  selected_option_text?: string | null;
  selectedAnswerIndex?: number | null;
  selected_answer_index?: number | null;

  correctAnswer?: unknown;
  correct_answer?: unknown;
  correctOptionKey?: string | null;
  correct_option_key?: string | null;
  correctOptionText?: string | null;
  correct_option_text?: string | null;
  correctAnswerIndex?: number | null;
  correct_answer_index?: number | null;

  explanation?: string | null;
  explanationText?: string | null;
  explanation_text?: string | null;
  explanationDetail?: string | null;
  explanation_detail?: string | null;
  rawExplanation?: string | null;
  raw_explanation?: string | null;
  rawBlock?: string | null;
  raw_block?: string | null;
  translationVi?: string | null;
  translation_vi?: string | null;
  finalTranslationVi?: string | null;
  final_translation_vi?: string | null;
  optionAnalysis?: string | null;
  option_analysis?: string | null;
  vocabularyNotes?: string | null;
  vocabulary_notes?: string | null;
  selectedText?: string | null;
  selected_text?: string | null;
  currentHighlightedText?: string | null;
  current_highlighted_text?: string | null;
  audio?: Record<string, unknown> | null;
  image?: Record<string, unknown> | null;
  skill?: string | null;
  subskill?: string | null;
  topic?: string | null;
  difficulty?: string | null;
  type?: string | null;
  questionType?: string | null;
};

export type ChatRequest = {
  message: string;

  conversation_id?: number | null;
  conversationId?: number | null;

  question_id?: number | string | null;
  questionId?: number | string | null;
  currentQuestionId?: number | string | null;
  runtimeQuestionId?: number | string | null;
  runtime_question_id?: number | string | null;
  runnerQuestionId?: number | string | null;
  runner_question_id?: number | string | null;
  docxQuestionId?: number | string | null;
  docx_question_id?: number | string | null;
  sourceQuestionId?: number | string | null;
  source_question_id?: number | string | null;
  sqlId?: number | string | null;
  source?: string | null;

  attempt_id?: number | null;
  attemptId?: number | null;

  context_type?: string | null;
  contextType?: string | null;
  currentQuestionKey?: string | null;
  current_question_key?: string | null;

  selected_answer_index?: number | null;
  selectedAnswerIndex?: number | null;
  selected_option_label?: string | null;
  selectedOptionLabel?: string | null;

  questionNumber?: number | string | null;
  question_number?: number | string | null;
  part?: number | string | null;
  partLabel?: string | null;
  part_label?: string | null;
  section?: string | null;
  skill?: string | null;
  subskill?: string | null;
  questionText?: string | null;
  question_text?: string | null;
  passage?: string | Record<string, unknown> | null;
  passageText?: string | null;
  passage_text?: string | null;
  options?: ChatQuestionOption[];
  choices?: ChatQuestionOption[];
  selectedAnswer?: unknown;
  selected_answer?: unknown;
  selectedOptionKey?: string | null;
  selected_option_key?: string | null;
  selectedOptionText?: string | null;
  selected_option_text?: string | null;
  correctAnswer?: unknown;
  correct_answer?: unknown;
  correctOptionKey?: string | null;
  correct_option_key?: string | null;
  correctOptionText?: string | null;
  correct_option_text?: string | null;
  explanation?: string | null;
  explanationText?: string | null;
  explanation_text?: string | null;
  explanationDetail?: string | null;
  explanation_detail?: string | null;
  rawExplanation?: string | null;
  raw_explanation?: string | null;
  rawBlock?: string | null;
  raw_block?: string | null;
  translationVi?: string | null;
  translation_vi?: string | null;
  finalTranslationVi?: string | null;
  final_translation_vi?: string | null;
  optionAnalysis?: string | null;
  option_analysis?: string | null;
  vocabularyNotes?: string | null;
  vocabulary_notes?: string | null;
  selectedText?: string | null;
  selected_text?: string | null;
  currentHighlightedText?: string | null;
  current_highlighted_text?: string | null;
  audio?: Record<string, unknown> | null;
  image?: Record<string, unknown> | null;
  reviewReason?: string | null;
  reviewReasons?: string[] | null;
  answerMode?: "short" | "default" | string | null;
  answer_mode?: "short" | "default" | string | null;
  useSqlOnly?: boolean | null;
  use_sql_only?: boolean | null;
  includeCorrectAnswer?: boolean | null;
  include_correct_answer?: boolean | null;

  currentQuestion?: ChatQuestionContext | null;
  current_question?: ChatQuestionContext | null;
  question?: ChatQuestionContext | null;
  context?: Record<string, unknown> | null;
};

export type ChatMessage = {
  id?: number | null;
  conversation_id?: number | null;
  conversationId?: number | null;
  role: "user" | "assistant" | "system";
  content: string;
  intent?: ChatIntent | string | null;
  status?: "created" | "streaming" | "completed" | "failed";
  created_at?: string | null;
  createdAt?: string | null;
  metadata?: Record<string, unknown>;
};

export type ChatResponse = {
  content?: string;
  answer?: string;
  message?: string;
  reply?: string;

  conversation_id?: number | null;
  conversationId?: number | null;

  role?: "assistant";
  intent?: ChatIntent | string;

  suggestions?: string[];
  messages?: ChatMessage[];

  user_message?: ChatMessage | null;
  userMessage?: ChatMessage | null;

  assistant_message?: ChatMessage | null;
  assistantMessage?: ChatMessage | null;

  intent_confidence?: number;
  intentConfidence?: number;

  intent_reason?: string;
  intentReason?: string;

  context_missing?: string[];
  contextMissing?: string[];

  requiresPro?: boolean;
  requires_pro?: boolean;
};

export type ChatStreamEvent = {
  event: "created" | "status" | "chunk" | "completed" | "error";
  data: Record<string, unknown>;
};

function normalizeRequest(
  messageOrRequest: string | ChatRequest,
  context?: Omit<ChatRequest, "message">,
): ChatRequest {
  if (typeof messageOrRequest === "string") {
    return { message: messageOrRequest, ...context };
  }

  return messageOrRequest;
}

function fallbackReply(response: ChatResponse) {
  return (
    response.reply ||
    response.answer ||
    response.content ||
    response.message ||
    response.assistant_message?.content ||
    response.assistantMessage?.content ||
    response.messages?.find((item) => item.role === "assistant")?.content ||
    "AI Tutor chưa tạo được phản hồi."
  );
}

function parseSseEvent(rawEvent: string): ChatStreamEvent | null {
  const lines = rawEvent.split("\n");
  const eventLine = lines.find((line) => line.startsWith("event:"));
  const dataLines = lines.filter((line) => line.startsWith("data:"));

  if (!eventLine || dataLines.length === 0) return null;

  return {
    event: eventLine.replace("event:", "").trim() as ChatStreamEvent["event"],
    data: JSON.parse(dataLines.map((line) => line.replace("data:", "").trim()).join("\n")),
  };
}

export const chatService = {
  async send(message: string, context?: Omit<ChatRequest, "message">) {
    const response = await this.sendDetailed(message, context);
    return fallbackReply(response);
  },

  async sendDetailed(messageOrRequest: string | ChatRequest, context?: Omit<ChatRequest, "message">) {
    const request = normalizeRequest(messageOrRequest, context);

    let response: ChatResponse;
    try {
      response = await apiRequest<ChatResponse>("/api/chat", {
        method: "POST",
        auth: true,
        body: JSON.stringify(request),
      });
    } catch (error) {
      if (error instanceof TypeError) {
        throw new Error(`Không kết nối được AI Tutor tại ${API_BASE_URL}/api/chat. Kiểm tra backend FastAPI và VITE_API_BASE_URL.`);
      }
      throw error;
    }

    return {
      ...response,
      reply: fallbackReply(response),
    };
  },

  async stream(
    messageOrRequest: string | ChatRequest,
    onEvent: (event: ChatStreamEvent) => void,
    context?: Omit<ChatRequest, "message">,
  ) {
    const request = normalizeRequest(messageOrRequest, context);

    const headers = new Headers({
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    });

    const token = getAuthToken();

    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: "POST",
        headers,
        body: JSON.stringify(request),
      });
    } catch {
      const fallback = await this.sendDetailed(request);
      onEvent({ event: "completed", data: { reply: fallback.reply, response: fallback } });
      return;
    }

    if (response.status === 404 || response.status === 405) {
      const fallback = await this.sendDetailed(request);
      onEvent({ event: "completed", data: { reply: fallback.reply, response: fallback } });
      return;
    }

    if (!response.ok || !response.body) {
      const detail = await response.text();
      throw new Error(detail || `Chat stream failed with status ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();

      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";

      for (const rawEvent of events) {
        const parsed = parseSseEvent(rawEvent);
        if (parsed) onEvent(parsed);
      }
    }

    if (buffer.trim()) {
      const parsed = parseSseEvent(buffer);
      if (parsed) onEvent(parsed);
    }
  },
};
