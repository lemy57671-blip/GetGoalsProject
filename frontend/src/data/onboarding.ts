export type OnboardingStep = {
  id: number;
  title: string;
};

export type LevelOption = {
  value: string;
  label: string;
  desc: string;
  score: string;
};

export type TargetScoreOption = {
  value: string;
  label: string;
  desc: string;
};

export type DeadlineOption = {
  value: string;
  label: string;
  intensity: string;
};

export type StudyTimeOption = {
  value: string;
  label: string;
};

export type WeakSkillOption = {
  value: string;
  label: string;
  desc: string;
};

export const onboardingSteps: OnboardingStep[] = [
  { id: 1, title: "Trình độ hiện tại" },
  { id: 2, title: "Mục tiêu điểm số" },
  { id: 3, title: "Thời gian deadline" },
  { id: 4, title: "Thói quen học" },
  { id: 5, title: "Điểm yếu cần cải thiện" },
];

export const onboardingLevels: LevelOption[] = [
  { value: "beginner", label: "Mới bắt đầu", desc: "Chưa từng thi TOEIC hoặc dưới 300 điểm", score: "< 300" },
  { value: "elementary", label: "Sơ cấp", desc: "Điểm TOEIC từ 300-450", score: "300-450" },
  { value: "intermediate", label: "Trung cấp", desc: "Điểm TOEIC từ 450-600", score: "450-600" },
  { value: "upper", label: "Trung cấp cao", desc: "Điểm TOEIC từ 600-750", score: "600-750" },
  { value: "advanced", label: "Cao cấp", desc: "Điểm TOEIC trên 750", score: "750+" },
];

export const onboardingTargetScores: TargetScoreOption[] = [
  { value: "500", label: "500 điểm", desc: "Đủ yêu cầu cơ bản" },
  { value: "600", label: "600 điểm", desc: "Chuẩn tốt nghiệp nhiều trường" },
  { value: "700", label: "700 điểm", desc: "Yêu cầu tuyển dụng phổ biến" },
  { value: "800", label: "800 điểm", desc: "Cơ hội thăng tiến cao" },
  { value: "900", label: "900+ điểm", desc: "Xuất sắc, mục tiêu cao nhất" },
];

export const onboardingDeadlines: DeadlineOption[] = [
  { value: "1month", label: "1 tháng", intensity: "Cao" },
  { value: "2months", label: "2 tháng", intensity: "Trung bình" },
  { value: "3months", label: "3 tháng", intensity: "Vừa phải" },
  { value: "6months", label: "6 tháng", intensity: "Thoải mái" },
  { value: "flexible", label: "Linh hoạt", intensity: "Tự do" },
];

export const onboardingStudyTimes: StudyTimeOption[] = [
  { value: "30min", label: "30 phút/ngày" },
  { value: "1hour", label: "1 giờ/ngày" },
  { value: "2hours", label: "2 giờ/ngày" },
  { value: "3hours", label: "3+ giờ/ngày" },
];

export const onboardingWeakSkills: WeakSkillOption[] = [
  { value: "listening-part1", label: "Listening Part 1", desc: "Mô tả hình ảnh" },
  { value: "listening-part2", label: "Listening Part 2", desc: "Hỏi - Đáp" },
  { value: "listening-part3", label: "Listening Part 3", desc: "Hội thoại ngắn" },
  { value: "listening-part4", label: "Listening Part 4", desc: "Bài nói ngắn" },
  { value: "reading-part5", label: "Reading Part 5", desc: "Điền từ vào câu" },
  { value: "reading-part6", label: "Reading Part 6", desc: "Điền từ vào đoạn văn" },
  { value: "reading-part7", label: "Reading Part 7", desc: "Đọc hiểu" },
  { value: "vocabulary", label: "Từ vựng", desc: "Vốn từ hạn chế" },
  { value: "grammar", label: "Ngữ pháp", desc: "Cấu trúc câu" },
];
