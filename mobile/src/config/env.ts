const DEFAULT_DEV_API_URL = "http://127.0.0.1:8000/api/v1";

export const appEnvironment = process.env.EXPO_PUBLIC_ENV ?? "development";
export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? DEFAULT_DEV_API_URL).replace(/\/$/, "");
export const skipEmailVerification = appEnvironment !== "production" && (process.env.EXPO_PUBLIC_SKIP_EMAIL_VERIFICATION ?? process.env.SKIP_EMAIL_VERIFICATION ?? "false").toLowerCase() === "true";

if (appEnvironment === "production" && !API_URL.startsWith("https://")) {
  throw new Error("EXPO_PUBLIC_API_URL must use https:// in production builds.");
}

if (appEnvironment === "production" && skipEmailVerification) {
  throw new Error("Email verification cannot be skipped in production builds.");
}

export function websocketBaseUrl(apiUrl = API_URL): string {
  return apiUrl.replace(/^https:\/\//, "wss://").replace(/^http:\/\//, "ws://").replace(/\/api\/v1\/?$/, "");
}
