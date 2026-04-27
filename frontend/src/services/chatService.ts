import { apiRequest } from "@src/services/apiClient";

type ChatResponse = {
  reply?: string;
};

export const chatService = {
  async send(message: string) {
    const response = await apiRequest<ChatResponse>("/api/chat", {
      method: "POST",
      auth: true,
      body: JSON.stringify({ message }),
    });

    return response.reply || "AI Tutor chua tao duoc phan hoi.";
  },
};
