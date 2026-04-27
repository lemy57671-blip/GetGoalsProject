import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  BookOpen,
  Brain,
  Headphones,
  Sparkles,
  Target,
  Award,
} from "lucide-react";

export type MarketingFeature = {
  icon: LucideIcon;
  title: string;
  description: string;
};

export type MarketingTestimonial = {
  name: string;
  role: string;
  content: string;
  score: string;
  avatar: string;
};

export type MarketingStat = {
  value: string;
  label: string;
};

export type MarketingFaq = {
  question: string;
  answer: string;
};

export type MarketingStep = {
  step: number;
  icon: LucideIcon;
  title: string;
  desc: string;
};

export const marketingFeatures: MarketingFeature[] = [
  {
    icon: Target,
    title: "Bai kiem tra chuan doan",
    description:
      "Danh gia trinh do hien tai va xac dinh diem yeu can cai thien chi trong 15 phut.",
  },
  {
    icon: Brain,
    title: "Lo trinh ca nhan hoa",
    description:
      "AI tao ke hoach hoc tap rieng dua tren muc tieu diem so va thoi gian ban co.",
  },
  {
    icon: BookOpen,
    title: "Luyen tap theo ky nang",
    description:
      "Hang nghin cau hoi duoc phan loai theo ky nang va Part TOEIC chi tiet.",
  },
  {
    icon: Headphones,
    title: "Mock Test chuan format",
    description:
      "De thi thu Full Test va Mini Test mo phong 100% ky thi thuc te.",
  },
  {
    icon: Sparkles,
    title: "AI Coach giai thich",
    description:
      "Tro ly AI phan tich loi sai, giai thich chi tiet va goi y cach cai thien.",
  },
  {
    icon: BarChart3,
    title: "Theo doi tien do",
    description:
      "Bieu do truc quan, bao cao tuan va phan tich xu huong diem so.",
  },
];

export const marketingTestimonials: MarketingTestimonial[] = [
  {
    name: "Nguyen Minh Anh",
    role: "Sinh vien Dai hoc Ngoai thuong",
    content:
      "Tu 550 len 850 TOEIC chi trong 3 thang! Lo trinh cua GetGoals giup minh tap trung dung diem yeu.",
    score: "850",
    avatar: "MA",
  },
  {
    name: "Tran Van Hung",
    role: "Nhan vien IT",
    content:
      "AI Coach giai thich rat chi tiet, giong nhu co gia su rieng 24/7. Tiet kiem rat nhieu thoi gian.",
    score: "920",
    avatar: "VH",
  },
  {
    name: "Le Thi Huong",
    role: "Ke toan tai Big4",
    content:
      "Mock test chuan format that, lam quen ap luc thi that. Diem thi thuc te dung nhu du doan.",
    score: "780",
    avatar: "TH",
  },
];

export const marketingStats: MarketingStat[] = [
  { value: "50,000+", label: "Hoc vien dang hoc" },
  { value: "150+", label: "Diem tang trung binh" },
  { value: "98%", label: "Hai long voi ket qua" },
  { value: "4.9/5", label: "Danh gia tu hoc vien" },
];

export const marketingFaqs: MarketingFaq[] = [
  {
    question: "GetGoals co phu hop voi nguoi moi bat dau khong?",
    answer:
      "Hoan toan phu hop! Bai kiem tra chuan doan se xac dinh trinh do cua ban va tao lo trinh hoc phu hop tu co ban den nang cao.",
  },
  {
    question: "Toi can hoc bao lau de tang 100 diem?",
    answer:
      "Tuy thuoc vao thoi gian hoc hang ngay, trung binh hoc vien tang 100 diem sau 6-8 tuan hoc deu dan 1-2 gio/ngay.",
  },
  {
    question: "AI Coach hoat dong nhu the nao?",
    answer:
      "AI Coach phan tich cau tra loi cua ban, giai thich loi sai chi tiet, va goi y phuong phap cai thien dua tren mau loi cua ban.",
  },
  {
    question: "Goi Pro co nhung gi khac goi Free?",
    answer:
      "Goi Pro bao gom: lo trinh ca nhan hoa theo deadline, practice khong gioi han, AI Chat ho tro tuc thi, mock test day du voi phan tich chi tiet.",
  },
  {
    question: "Toi co the huy goi Pro bat cu luc nao khong?",
    answer:
      "Co, ban co the huy bat cu luc nao. Goi se con hieu luc den het chu ky thanh toan hien tai.",
  },
];

export const marketingSteps: MarketingStep[] = [
  {
    step: 1,
    icon: Target,
    title: "Kiem tra trinh do",
    desc: "Lam bai chuan doan 15 phut",
  },
  {
    step: 2,
    icon: Brain,
    title: "Nhan lo trinh",
    desc: "AI tao ke hoach rieng cho ban",
  },
  {
    step: 3,
    icon: BookOpen,
    title: "Luyen tap hang ngay",
    desc: "Hoc theo lo trinh va AI Coach",
  },
  {
    step: 4,
    icon: Award,
    title: "Dat muc tieu",
    desc: "Thi thu va chinh phuc TOEIC",
  },
];
