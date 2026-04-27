export type PracticeRunnerQuestion = {
  id: number;
  section: "Listening" | "Reading";
  part: string;
  type: string;
  question: string;
  hasAudio: boolean;
  hasImage: boolean;
  options: string[];
  correct: number;
  explanation: string;
  skill: string;
};

export const practiceRunnerSampleQuestions: PracticeRunnerQuestion[] = [
  {
    id: 1,
    section: "Listening",
    part: "Part 1",
    type: "photograph",
    question:
      "Look at the picture and choose the statement that best describes what you see.",
    hasAudio: true,
    hasImage: true,
    options: [
      "The man is typing on a laptop.",
      "The woman is writing on a whiteboard.",
      "Two colleagues are reviewing documents together.",
      "The office is empty.",
    ],
    correct: 2,
    explanation:
      "The image shows two colleagues sitting at a desk, looking at papers and discussing them. This matches option C which describes 'Two colleagues are reviewing documents together.'",
    skill: "Identifying actions",
  },
  {
    id: 2,
    section: "Listening",
    part: "Part 2",
    type: "question-response",
    question: "Where is the meeting room?",
    hasAudio: true,
    hasImage: false,
    options: [
      "Yes, we're having a meeting.",
      "It's on the third floor.",
      "At 2 o'clock.",
      "About ten people.",
    ],
    correct: 1,
    explanation:
      "This is a 'Where' question asking for a location. Option B correctly provides a location ('on the third floor'). The other options don't answer the location question - A responds to 'Are you having a meeting?', C responds to 'When?', and D responds to 'How many?'",
    skill: "WH-questions",
  },
  {
    id: 3,
    section: "Reading",
    part: "Part 5",
    type: "incomplete-sentence",
    question: "The sales team _____ their quarterly targets ahead of schedule.",
    hasAudio: false,
    hasImage: false,
    options: ["achieve", "achieves", "achieved", "achieving"],
    correct: 2,
    explanation:
      "The past tense 'achieved' is correct because 'ahead of schedule' suggests a completed action. The subject 'sales team' is singular collective noun, and the sentence structure requires a finite verb form.",
    skill: "Verb tenses",
  },
  {
    id: 4,
    section: "Reading",
    part: "Part 5",
    type: "incomplete-sentence",
    question:
      "All employees must submit their expense reports _____ the end of each month.",
    hasAudio: false,
    hasImage: false,
    options: ["by", "until", "since", "from"],
    correct: 0,
    explanation:
      "'By' is used to indicate a deadline - the latest time something should happen. 'Until' means continuing to a point, 'since' indicates from a point in the past, and 'from' indicates a starting point.",
    skill: "Prepositions",
  },
  {
    id: 5,
    section: "Reading",
    part: "Part 5",
    type: "incomplete-sentence",
    question:
      "Due to the bad weather, the outdoor event has been _____ until next week.",
    hasAudio: false,
    hasImage: false,
    options: ["postponed", "canceled", "organized", "scheduled"],
    correct: 0,
    explanation:
      "'Postponed' means to delay to a later time, which matches 'until next week'. 'Canceled' means completely called off, not rescheduled. 'Organized' and 'scheduled' don't fit the context of bad weather causing a delay.",
    skill: "Vocabulary in context",
  },
];
