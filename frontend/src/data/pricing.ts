export type PricingFeature = {
  text: string;
  included: boolean;
};

export type PricingFaq = {
  q: string;
  a: string;
};

export const freeFeatures: PricingFeature[] = [
  { text: "Bài chẩn đoán cơ bản", included: true },
  { text: "Practice giới hạn (20 câu/ngày)", included: true },
  { text: "Overview tiến độ cơ bản", included: true },
  { text: "Roadmap theo mục tiêu và deadline", included: false },
  { text: "Practice không giới hạn", included: false },
  { text: "Mock test kèm phân tích lỗi", included: false },
  { text: "AI chat box hỗ trợ", included: false },
  { text: "Báo cáo tiến độ theo tuần", included: false },
  { text: "Review nâng cao và notebook", included: false },
];

export const proFeatures: PricingFeature[] = [
  { text: "Bài chẩn đoán nâng cao", included: true },
  { text: "Practice không giới hạn", included: true },
  { text: "Roadmap cá nhân hóa theo mục tiêu", included: true },
  { text: "Mock test như thi thật", included: true },
  { text: "AI Coach hỗ trợ 24/7", included: true },
  { text: "Phân tích lỗi sai chi tiết", included: true },
  { text: "Báo cáo tiến độ theo tuần", included: true },
  { text: "Notebook lưu từ vựng", included: true },
  { text: "Review nâng cao với AI", included: true },
];

export const pricingFaqs: PricingFaq[] = [
  {
    q: "Tôi có thể dùng thử Pro miễn phí không?",
    a: "Hiện tại GetGoals chưa có gói dùng thử riêng. Bạn vẫn có thể trải nghiệm gói Free trước khi nâng cấp.",
  },
  {
    q: "Tôi có thể hủy đăng ký bất cứ lúc nào không?",
    a: "Có. Tài khoản sẽ quay về Free khi hết hạn gói hiện tại.",
  },
  {
    q: "Thanh toán như thế nào?",
    a: "GetGoals tạo mã QR và link PayOS để bạn thanh toán nhanh. Sau khi giao dịch được xác nhận, tài khoản sẽ được kích hoạt Pro.",
  },
  {
    q: "Có khuyến mãi cho sinh viên không?",
    a: "Thỉnh thoảng sẽ có ưu đãi theo chương trình. Bạn hãy theo dõi thông báo mới nhất trên ứng dụng.",
  },
  {
    q: "Dữ liệu học tập có được bảo mật không?",
    a: "Có. Dữ liệu học tập được lưu trong hệ thống và không tự động chia sẻ cho bên thứ ba.",
  },
];
