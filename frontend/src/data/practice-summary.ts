export const practiceResults = {
  totalQuestions: 20,
  correct: 14,
  incorrect: 5,
  skipped: 1,
  timeSpent: "12:34",
  accuracy: 70,
  improvement: 8,
};

export const skillBreakdown = [
  { skill: "Verb tenses", correct: 4, total: 5, percentage: 80 },
  { skill: "Prepositions", correct: 3, total: 4, percentage: 75 },
  { skill: "Vocabulary", correct: 3, total: 4, percentage: 75 },
  { skill: "Question-Response", correct: 2, total: 4, percentage: 50 },
  { skill: "Photographs", correct: 2, total: 3, percentage: 67 },
];

export const weaknesses = [
  {
    skill: "Question-Response",
    description: "Cần cải thiện khả năng nhận diện câu hỏi WH",
  },
  {
    skill: "Prepositions",
    description: "Lưu ý phân biệt 'by', 'until', 'since'",
  },
];

export const reviewQuestions = [
  {
    id: 1,
    question: "Where is the meeting room?",
    userAnswer: "Yes, we're having a meeting.",
    correctAnswer: "It's on the third floor.",
    isCorrect: false,
    explanation:
      "This is a 'Where' question asking for a location. The correct answer provides a location ('on the third floor').",
    skill: "Question-Response",
    difficulty: "medium",
    part: "Part 2",
  },
  {
    id: 2,
    question:
      "The sales team _____ their quarterly targets ahead of schedule.",
    userAnswer: "achieved",
    correctAnswer: "achieved",
    isCorrect: true,
    explanation:
      "The past tense 'achieved' is correct because the context indicates a completed action.",
    skill: "Verb tenses",
    difficulty: "easy",
    part: "Part 5",
  },
  {
    id: 3,
    question:
      "All employees must submit their expense reports _____ the end of each month.",
    userAnswer: "until",
    correctAnswer: "by",
    isCorrect: false,
    explanation:
      "'By' is used to indicate a deadline. 'Until' means continuing to a point in time.",
    skill: "Prepositions",
    difficulty: "medium",
    part: "Part 5",
  },
];
