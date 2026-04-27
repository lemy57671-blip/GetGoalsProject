export const reviewQuestions = [
  {
    id: 1,
    question:
      "The company's new marketing strategy has been _______ successful in attracting younger customers.",
    options: ["remarkable", "remarkably", "remark", "remarking"],
    userAnswer: "A",
    correctAnswer: "B",
    isCorrect: false,
    explanation:
      "Trong câu này, chúng ta cần một trạng từ (adverb) để bổ nghĩa cho tính từ 'successful'. 'Remarkably' là trạng từ đúng. 'Remarkable' là tính từ nên không phù hợp.",
    skill: "Grammar",
    subskill: "Adverbs",
    part: 5,
    difficulty: "medium",
  },
  {
    id: 2,
    question: "All employees must submit their expense reports _______ the end of each month.",
    options: ["by", "until", "within", "through"],
    userAnswer: "A",
    correctAnswer: "A",
    isCorrect: true,
    explanation:
      "'By' được sử dụng để chỉ thời hạn cuối cùng (deadline). Câu này nói về việc nộp báo cáo trước cuối tháng.",
    skill: "Grammar",
    subskill: "Prepositions",
    part: 5,
    difficulty: "easy",
  },
  {
    id: 3,
    question: "The board of directors _______ to announce their decision next week.",
    options: ["expects", "expecting", "is expected", "are expected"],
    userAnswer: "D",
    correctAnswer: "C",
    isCorrect: false,
    explanation:
      "'The board of directors' được xem là một tập thể đơn lẻ, nên động từ phải ở dạng số ít. 'Is expected' là đáp án đúng.",
    skill: "Grammar",
    subskill: "Subject-Verb Agreement",
    part: 5,
    difficulty: "hard",
  },
] as const;

export type ReviewQuestion = (typeof reviewQuestions)[number];

export const notebookItems = [
  {
    id: 1,
    word: "remarkably",
    meaning: "một cách đáng chú ý, đáng kể",
    example: "The product was remarkably successful.",
    source: "Part 5 - Câu 1",
    note: "Trạng từ bổ nghĩa tính từ",
    tags: ["adverb", "grammar"],
  },
  {
    id: 2,
    word: "submit",
    meaning: "nộp, trình",
    example: "Please submit your report by Friday.",
    source: "Part 5 - Câu 2",
    note: "Động từ thường dùng trong văn phòng",
    tags: ["verb", "business"],
  },
] as const;

export const reviewSkillBreakdown = [
  { name: "Grammar", correct: 5, total: 8 },
  { name: "Vocabulary", correct: 3, total: 5 },
  { name: "Reading Comprehension", correct: 4, total: 7 },
] as const;

export const reviewPartBreakdown = [
  { name: "Part 5", correct: 7, total: 10 },
  { name: "Part 6", correct: 5, total: 6 },
  { name: "Part 7", correct: 4, total: 4 },
] as const;

export type ReviewChatMessage = {
  role: "assistant" | "user";
  content: string;
};

export const initialAiMessages: ReviewChatMessage[] = [
  {
    role: "assistant",
    content:
      "Chào bạn! Mình là AI Tutor. Bạn có thể hỏi vì sao đáp án đúng, phân tích lỗi sai, dịch câu hỏi hoặc xin mẹo làm dạng này.",
  },
];
