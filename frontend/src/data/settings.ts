export const initialSettingsFormState = {
  name: "",
  email: "",
  currentScore: "550",
  targetScore: "750",
  examDate: "",
  studyMinutesPerDay: "30",
  theme: "system",
  language: "vi",
  soundEnabled: true,
  autoPlayAudio: true,
  defaultTestMode: "smart",
  aiExplanation: true,
  dailyReminder: true,
  weeklyCheck: true,
  emailNotification: false,
  reminderTime: "20:00",
};

export const learningSkillTags = [
  { label: "Listening", value: "listening" },
  { label: "Reading", value: "reading" },
  { label: "Grammar", value: "grammar" },
  { label: "Vocabulary", value: "vocabulary" },
] as const;

export const subscriptionFeatures = [
  "Basic diagnostic",
  "Limited daily practice",
  "Basic progress overview",
] as const;
