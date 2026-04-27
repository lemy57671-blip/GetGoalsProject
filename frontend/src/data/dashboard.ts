import {
  BarChart3,
  BookOpen,
  Crown,
  FileText,
  Headphones,
  LayoutDashboard,
  Map,
  Settings,
  Target,
  Zap,
  type LucideIcon,
} from "lucide-react";

export type DashboardNavItem = {
  name: string;
  href: string;
  icon: LucideIcon;
};

export type DashboardQuickAction = {
  label: string;
  href: string;
  icon: LucideIcon;
};

export type DashboardUserSummary = {
  initials: string;
  name: string;
  plan: string;
};

export type DiagnosticQuestion = {
  id: number;
  section: string;
  part: string;
  question: string;
  audio?: boolean;
  options: string[];
  correct: number;
};

export const dashboardNavigation: DashboardNavItem[] = [
  { name: "Tổng quan", href: "/dashboard", icon: LayoutDashboard },
  { name: "Placement Test", href: "/placement-test", icon: Target },
  { name: "Luyện tập", href: "/practice", icon: BookOpen },
  { name: "Mock Test", href: "/mock-test", icon: FileText },
  { name: "Roadmap", href: "/roadmap", icon: Map },
  { name: "Tiến độ", href: "/progress", icon: BarChart3 },
  { name: "Ôn tập", href: "/review", icon: BookOpen },
  { name: "Cài đặt", href: "/settings", icon: Settings },
];

export const dashboardQuickActions: DashboardQuickAction[] = [
  {
    label: "Listening",
    href: "/practice?type=listening",
    icon: Headphones,
  },
  {
    label: "Reading",
    href: "/practice?type=reading",
    icon: BookOpen,
  },
  {
    label: "Mini Test",
    href: "/mock-test",
    icon: Zap,
  },
];

export const dashboardUpgradeBanner = {
  href: "/pricing",
  title: "Nâng cấp Pro",
  description: "Mở khóa AI Coach & lộ trình cá nhân hóa",
  icon: Crown,
};

export const dashboardUserSummary: DashboardUserSummary = {
  initials: "NV",
  name: "Nguyễn Văn",
  plan: "Free Plan",
};

export const diagnosticSampleQuestions: DiagnosticQuestion[] = [
  {
    id: 1,
    section: "Listening",
    part: "Part 1",
    question:
      "Look at the picture and choose the statement that best describes what you see.",
    audio: true,
    options: [
      "A man is typing on a keyboard.",
      "A woman is reading a book.",
      "Two people are shaking hands.",
      "A group is having a meeting.",
    ],
    correct: 2,
  },
  {
    id: 2,
    section: "Listening",
    part: "Part 2",
    question: "Where is the nearest coffee shop?",
    audio: true,
    options: [
      "Yes, I like coffee.",
      "It's on the corner of Main Street.",
      "I prefer tea.",
      "About ten minutes.",
    ],
    correct: 1,
  },
  {
    id: 3,
    section: "Reading",
    part: "Part 5",
    question: "The manager _____ the report before the meeting started.",
    options: ["review", "reviews", "reviewed", "reviewing"],
    correct: 2,
  },
  {
    id: 4,
    section: "Reading",
    part: "Part 5",
    question:
      "Due to the bad weather, the outdoor event has been _____ until next week.",
    options: ["postponed", "canceled", "continued", "organized"],
    correct: 0,
  },
  {
    id: 5,
    section: "Reading",
    part: "Part 6",
    question:
      "All employees are required to submit their expense reports _____ the end of each month.",
    options: ["by", "until", "since", "from"],
    correct: 0,
  },
];
