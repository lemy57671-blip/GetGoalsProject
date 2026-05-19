const DEFAULT_API_BASE_URL = "http://127.0.0.1:8001";

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/+$/, "");

export const AUTH_TOKEN_STORAGE_KEY = "getgoals.authToken";

type ApiRequestOptions = RequestInit & {
  auth?: boolean;
};

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(status: number, message: string, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

export function getAuthToken() {
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
}

export function setAuthToken(token: string) {
  window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
}

export function clearAuthToken() {
  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const headers = new Headers(options.headers);

  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  if (options.auth) {
    const token = getAuthToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    console.error("API network request failed", {
      endpoint: path,
      method: options.method || "GET",
      baseUrl: API_BASE_URL,
      detail,
    });
    throw new Error(`Network request failed for ${path}: ${detail}`);
  }

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const payloadObject =
      typeof payload === "object" && payload ? (payload as { message?: unknown; detail?: unknown }) : null;
    const messageValue = payloadObject && "message" in payloadObject ? String(payloadObject.message) : "";
    const detailValue = payloadObject && "detail" in payloadObject ? String(payloadObject.detail) : "";
    const message =
      messageValue && detailValue && detailValue !== messageValue
        ? `${messageValue}: ${detailValue}`
        : messageValue || detailValue || `Request failed with status ${response.status}`;

    throw new ApiError(response.status, message, payload);
  }

  return payload as T;
}
