import { en } from "@src/i18n/en";
import { vi } from "@src/i18n/vi";

export type Language = "vi" | "en";
export type TranslationKey = keyof typeof vi;

export const translations = {
  vi,
  en,
} satisfies Record<Language, Record<TranslationKey, string>>;

export const DEFAULT_LANGUAGE: Language = "vi";
export const LANGUAGE_STORAGE_KEY = "getgoals_language";
