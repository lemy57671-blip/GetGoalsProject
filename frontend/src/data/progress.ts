import { BookOpen, Brain, FileText, Headphones } from "lucide-react";

export const scoreHistory = [
  { week: "W1", score: 520 },
  { week: "W2", score: 545 },
  { week: "W3", score: 575 },
  { week: "W4", score: 610 },
  { week: "W5", score: 640 },
  { week: "W6", score: 665 },
];

export const skillProgress = [
  {
    name: "Listening",
    value: 72,
    accuracy: 74,
    change: "+6%",
    trend: "up",
    icon: Headphones,
  },
  {
    name: "Reading",
    value: 61,
    accuracy: 63,
    change: "+4%",
    trend: "up",
    icon: FileText,
  },
  {
    name: "Grammar",
    value: 68,
    accuracy: 71,
    change: "+3%",
    trend: "up",
    icon: Brain,
  },
  {
    name: "Vocabulary",
    value: 57,
    accuracy: 59,
    change: "-1%",
    trend: "down",
    icon: BookOpen,
  },
] as const;

export const partProgress = [
  { part: "Part 1", accuracy: 84, speed: "Nhanh", status: "Vững" },
  { part: "Part 2", accuracy: 76, speed: "Ổn", status: "Đang tốt lên" },
  { part: "Part 3", accuracy: 64, speed: "TB", status: "Cần luyện thêm" },
  { part: "Part 4", accuracy: 59, speed: "TB", status: "Cần cải thiện" },
  { part: "Part 5", accuracy: 71, speed: "Nhanh", status: "Khá tốt" },
  { part: "Part 6", accuracy: 66, speed: "Ổn", status: "Đang cải thiện" },
  { part: "Part 7", accuracy: 48, speed: "Chậm", status: "Yếu nhất" },
];

export const weeklyActivity = [
  { day: "Mon", minutes: 55 },
  { day: "Tue", minutes: 40 },
  { day: "Wed", minutes: 75 },
  { day: "Thu", minutes: 30 },
  { day: "Fri", minutes: 65 },
  { day: "Sat", minutes: 85 },
  { day: "Sun", minutes: 50 },
];

export const heatmap = [
  [1, 0, 2, 1, 3, 2, 1],
  [2, 2, 1, 0, 3, 3, 1],
  [1, 1, 2, 2, 2, 0, 0],
  [3, 2, 2, 1, 1, 2, 3],
];

export const progressOverview = {
  currentScore: 665,
  targetScore: 750,
  roadmapCompletion: 64,
  daysLeft: 48,
  streak: 9,
  completedTests: 17,
  weeklyHours: 6.7,
};

export const roadmapSteps = [
  { title: "Nền tảng", done: true },
  { title: "Luyện tập trọng tâm", done: true },
  { title: "Mock test", done: false, current: true },
  { title: "AI Coach / Review", done: false },
] as const;
