import { BookOpen, Brain, FileText, Headphones } from "lucide-react";

export const partOptions = [
  { id: 1, name: "Part 1", desc: "Mô tả hình ảnh", type: "listening" },
  { id: 2, name: "Part 2", desc: "Hỏi - Đáp", type: "listening" },
  { id: 3, name: "Part 3", desc: "Hội thoại ngắn", type: "listening" },
  { id: 4, name: "Part 4", desc: "Bài nói ngắn", type: "listening" },
  { id: 5, name: "Part 5", desc: "Điền câu", type: "reading" },
  { id: 6, name: "Part 6", desc: "Hoàn thành đoạn văn", type: "reading" },
  { id: 7, name: "Part 7", desc: "Đọc hiểu", type: "reading" },
] as const;

export const skillOptions = [
  { id: "listening", name: "Listening", icon: Headphones },
  { id: "reading", name: "Reading", icon: BookOpen },
  { id: "grammar", name: "Grammar", icon: FileText },
  { id: "vocabulary", name: "Vocabulary", icon: Brain },
] as const;

export const difficultyOptions = [
  {
    id: "easy",
    name: "Dễ",
    color: "bg-green-100 text-green-700 border-green-200",
  },
  {
    id: "medium",
    name: "Trung bình",
    color: "bg-yellow-100 text-yellow-700 border-yellow-200",
  },
  {
    id: "hard",
    name: "Khó",
    color: "bg-red-100 text-red-700 border-red-200",
  },
  {
    id: "mixed",
    name: "Hỗn hợp",
    color: "bg-blue-100 text-blue-700 border-blue-200",
  },
] as const;

export const recentTests = [
  { id: 1, name: "Full Test #3", score: 685, date: "2 ngày trước", type: "full" },
  {
    id: 2,
    name: "Mini Test - Listening",
    score: 340,
    date: "4 ngày trước",
    type: "mini",
  },
  {
    id: 3,
    name: "Weekly Check #5",
    score: 720,
    date: "1 tuần trước",
    type: "weekly",
  },
] as const;

export type SkillOptionId = (typeof skillOptions)[number]["id"];
export type DifficultyOptionId = (typeof difficultyOptions)[number]["id"];
export type PartOptionId = (typeof partOptions)[number]["id"];
