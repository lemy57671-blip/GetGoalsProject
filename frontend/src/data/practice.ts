export type ViewMode = "skill" | "part";
export type PracticeMode = "exam" | "smart";
export type Difficulty = "easy" | "medium" | "hard" | "mixed";
export type SkillFilter = "all" | "listening" | "reading";

export type PartItem = {
  id: string;
  name: string;
  tag: "listening" | "reading";
  description: string;
  count: number;
};

export type SkillPack = {
  id: string;
  name: string;
  tag: "listening" | "reading";
  description: string;
  parts: string[];
  estimatedCount: number;
  focus: string[];
};

export const TOEIC_PARTS: PartItem[] = [
  {
    id: "part1",
    name: "Part 1",
    tag: "listening",
    description: "Photographs",
    count: 6,
  },
  {
    id: "part2",
    name: "Part 2",
    tag: "listening",
    description: "Question-Response",
    count: 25,
  },
  {
    id: "part3",
    name: "Part 3",
    tag: "listening",
    description: "Conversations",
    count: 39,
  },
  {
    id: "part4",
    name: "Part 4",
    tag: "listening",
    description: "Talks",
    count: 30,
  },
  {
    id: "part5",
    name: "Part 5",
    tag: "reading",
    description: "Incomplete Sentences",
    count: 30,
  },
  {
    id: "part6",
    name: "Part 6",
    tag: "reading",
    description: "Text Completion",
    count: 16,
  },
  {
    id: "part7",
    name: "Part 7",
    tag: "reading",
    description: "Reading Comprehension",
    count: 54,
  },
];

export const SKILL_PACKS: SkillPack[] = [
  {
    id: "listening-basic",
    name: "Listening co ban",
    tag: "listening",
    description: "Lam quen nghe ngan, phan xa nhanh va bat y chinh.",
    parts: ["part1", "part2"],
    estimatedCount: 31,
    focus: ["Photographs", "Question-Response", "Listening reflex"],
  },
  {
    id: "listening-conversations",
    name: "Listening hoi thoai",
    tag: "listening",
    description: "Nghe hoi thoai nhieu nguoi noi va nhan dien thong tin.",
    parts: ["part3"],
    estimatedCount: 39,
    focus: ["Conversations", "Details", "Inference"],
  },
  {
    id: "listening-talks",
    name: "Listening bai noi",
    tag: "listening",
    description: "Nghe thong bao, bai noi ngan va dinh vi thong tin quan trong.",
    parts: ["part4"],
    estimatedCount: 30,
    focus: ["Talks", "Main idea", "Details"],
  },
  {
    id: "reading-grammar",
    name: "Reading grammar",
    tag: "reading",
    description: "Ngu phap nen tang, tu loai, cau truc cau va hoan chinh cau.",
    parts: ["part5"],
    estimatedCount: 30,
    focus: ["Grammar", "Sentence structure", "Word form"],
  },
  {
    id: "reading-vocabulary",
    name: "Reading vocabulary + text",
    tag: "reading",
    description: "Tu vung theo ngu canh va hoan chinh doan van.",
    parts: ["part5", "part6"],
    estimatedCount: 46,
    focus: ["Vocabulary", "Context", "Text completion"],
  },
  {
    id: "reading-comprehension",
    name: "Reading comprehension",
    tag: "reading",
    description: "Doc hieu email, thong bao, bieu mau va cau hoi suy luan.",
    parts: ["part7"],
    estimatedCount: 54,
    focus: ["Reading", "Inference", "Detail"],
  },
];
