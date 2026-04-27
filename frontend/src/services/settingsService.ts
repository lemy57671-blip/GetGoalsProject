import { apiRequest } from "@src/services/apiClient";

export type ThemeMode = "system" | "light" | "dark";
export type LanguageCode = "vi" | "en";

export type ExperiencePreferences = {
  themeMode: ThemeMode;
  language: LanguageCode;
  notificationSoundEnabled: boolean;
  autoPlayAudio: boolean;
  autoAiExplanation: boolean;
  updatedAtUtc?: string | null;
};

export type NotificationPreferences = {
  dailyReminderEnabled: boolean;
  weeklyCheckReminderEnabled: boolean;
  emailNotificationsEnabled: boolean;
  reminderTimeLocal: string;
  timezone: string;
  updatedAtUtc?: string | null;
};

export type DangerousActionSummary = {
  deleted: Record<string, number>;
  updated: Record<string, number>;
  skipped: string[];
};

export type DangerousActionResult = {
  success: boolean;
  message: string;
  summary: DangerousActionSummary;
};

export const settingsService = {
  getPreferences(): Promise<ExperiencePreferences> {
    return apiRequest<ExperiencePreferences>("/api/settings/preferences", {
      auth: true,
    });
  },

  updatePreferences(
    payload: ExperiencePreferences,
  ): Promise<ExperiencePreferences> {
    return apiRequest<ExperiencePreferences>("/api/settings/preferences", {
      method: "PUT",
      auth: true,
      body: JSON.stringify(payload),
    });
  },

  getNotifications(): Promise<NotificationPreferences> {
    return apiRequest<NotificationPreferences>("/api/settings/notifications", {
      auth: true,
    });
  },

  updateNotifications(
    payload: NotificationPreferences,
  ): Promise<NotificationPreferences> {
    return apiRequest<NotificationPreferences>("/api/settings/notifications", {
      method: "PUT",
      auth: true,
      body: JSON.stringify(payload),
    });
  },

  resetProgress(): Promise<DangerousActionResult> {
    return apiRequest<DangerousActionResult>("/api/settings/reset-progress", {
      method: "POST",
      auth: true,
    });
  },

  deleteHistory(): Promise<DangerousActionResult> {
    return apiRequest<DangerousActionResult>("/api/settings/delete-history", {
      method: "POST",
      auth: true,
    });
  },

  deleteAccount(confirmText: string): Promise<DangerousActionResult> {
    return apiRequest<DangerousActionResult>("/api/settings/account", {
      method: "DELETE",
      auth: true,
      body: JSON.stringify({ confirmText }),
    });
  },
};
