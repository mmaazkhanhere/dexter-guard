import { ApiError, apiErrorFromPayload } from "./errors";

const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api/v1";
export function idempotencyKey(operation: string): string { return `${operation}-${crypto.randomUUID()}`; }

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try { response = await fetch(`${baseUrl}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init.headers } }); }
  catch { throw new ApiError("Der Backend-Dienst ist nicht erreichbar.", { kind: "network", code: "NETWORK_UNAVAILABLE", retryable: true }); }
  const raw = await response.text();
  let body: unknown = undefined;
  try { body = raw ? JSON.parse(raw) : undefined; } catch { throw new ApiError("Das Backend hat eine ungültige Antwort geliefert.", { kind: "malformed", code: "MALFORMED_RESPONSE", status: response.status }); }
  if (!response.ok) throw apiErrorFromPayload(body, response.status);
  return body as T;
}
