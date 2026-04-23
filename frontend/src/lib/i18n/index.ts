import ar from "./ar.json";
import en from "./en.json";

export type Locale = "en" | "ar";

const catalogs: Record<Locale, Record<string, string>> = {
  en: en as Record<string, string>,
  ar: ar as Record<string, string>,
};

let locale: Locale = "en";

/** Set active UI locale (English or Arabic). */
export function setLocale(next: Locale): void {
  locale = next;
  document.documentElement.lang = next;
  document.documentElement.dir = next === "ar" ? "rtl" : "ltr";
}

/** Resolve a message key for the active locale. */
export function t(key: string): string {
  const table = catalogs[locale];
  return table[key] ?? catalogs.en[key] ?? key;
}
