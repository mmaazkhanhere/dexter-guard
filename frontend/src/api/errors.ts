export type ApiErrorKind = "validation" | "not-found" | "conflict" | "unavailable" | "timeout" | "malformed" | "network" | "unknown";
export class ApiError extends Error {
  readonly kind: ApiErrorKind; readonly code: string; readonly status: number; readonly field?: string; readonly retryable: boolean;
  constructor(message: string, options: { kind: ApiErrorKind; code: string; status?: number; field?: string; retryable?: boolean }) {
    super(message); this.name = "ApiError"; this.kind = options.kind; this.code = options.code; this.status = options.status ?? 0; this.field = options.field; this.retryable = options.retryable ?? false;
  }
}
export function normalizeApiError(error: unknown): ApiError { return error instanceof ApiError ? error : new ApiError("Der Backend-Dienst ist nicht erreichbar.", { kind: "network", code: "NETWORK_UNAVAILABLE", retryable: true }); }
export function apiErrorFromPayload(payload: unknown, status: number): ApiError {
  const body = typeof payload === "object" && payload !== null ? payload as Record<string, unknown> : {};
  const code = typeof body.code === "string" ? body.code : "HTTP_ERROR";
  const message = typeof body.message === "string" ? body.message : "Die Anfrage konnte nicht verarbeitet werden.";
  const kind: ApiErrorKind = status === 404 ? "not-found" : status === 409 ? "conflict" : status === 408 || status === 504 ? "timeout" : status === 422 || status === 400 ? "validation" : status >= 500 ? "unavailable" : "unknown";
  return new ApiError(message, { kind, code, status, field: typeof body.field === "string" ? body.field : undefined, retryable: kind === "timeout" || kind === "unavailable" });
}
