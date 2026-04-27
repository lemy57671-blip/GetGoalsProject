export const mockQuestion = {
  id: 1,
  part: 5,
  type: "sentence_completion",
  question:
    "The company's new marketing strategy has been _______ successful in attracting younger customers.",
  options: [
    { id: "A", text: "remarkable" },
    { id: "B", text: "remarkably" },
    { id: "C", text: "remark" },
    { id: "D", text: "remarking" },
  ],
  correctAnswer: "B",
  difficulty: "medium",
  skill: "Grammar",
  subskill: "Adverbs",
};

export const mockQuestions = Array.from({ length: 200 }, (_, i) => ({
  ...mockQuestion,
  id: i + 1,
  part: i < 100 ? Math.ceil((i + 1) / 25) : 4 + Math.ceil((i - 99) / 33),
}));
