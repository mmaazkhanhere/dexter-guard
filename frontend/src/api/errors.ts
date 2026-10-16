export type ApiErrorKind = "validation" | "not-found" | "conflict" | "unavailable" | "timeout" | "malformed" | "network" | "unknown";
export class ApiError extends Error {
  readonly kind: ApiErrorKind; readonly code: string; readonly status: number; readonly field?: string; readonly details?: Record<string, unknown>; readonly retryable: boolean; readonly technicalMessage: string;
  constructor(message: string, options: { kind: ApiErrorKind; code: string; status?: number; field?: string; details?: Record<string, unknown>; retryable?: boolean; technicalMessage?: string }) {
    super(message); this.name = "ApiError"; this.kind = options.kind; this.code = options.code; this.status = options.status ?? 0; this.field = options.field; this.details = options.details; this.retryable = options.retryable ?? false; this.technicalMessage = options.technicalMessage ?? message;
  }
}
export function userFacingApiMessage(code: string, message: string, field?: string, kind?: ApiErrorKind): string {
  if (code === "GENERATION_REJECTED" && (field?.endsWith("temporalQualifier") || /temporal|time|qualifier/i.test(message))) return "The AI added a time detail that was not found in the transcript. Please check the transcript and try again.";
  if (["GENERATION_PROVIDER_UNAVAILABLE", "GENERATION_PROVIDER_FAILURE", "GENERATION_PROVIDER_TIMEOUT"].includes(code)) return "The nursing note could not be generated right now. Please try again.";
  if (code === "EMPTY_MODEL_OUTPUT") return "The AI did not produce a nursing note. Please try again.";
  if (code === "GENERATION_REJECTED") return "The AI could not create a note that is fully supported by the transcript. Please check the transcript and try again.";
  if (["NETWORK_UNAVAILABLE", "DEPENDENCY_UNAVAILABLE"].includes(code)) return "The service is temporarily unavailable. Please try again.";
  if (code === "PROVIDER_TIMEOUT") return "Evidence verification took too long. The note was not approved; try verification again.";
  if (code === "PROVIDER_UNAVAILABLE") return "Evidence verification is temporarily unavailable. The note was not approved; try verification again.";
  if (code === "MALFORMED_VERIFIER_OUTPUT") return "Evidence verification returned an invalid response. The note was not approved; try verification again.";
  if (code === "UPSTREAM_FAILURE") return "Evidence verification did not complete. The note was not approved; try verification again.";
  if (code === "MALFORMED_RESPONSE") return "The service returned an unexpected response. Please try again.";
  if (code === "NOTE_VERSION_CONFLICT" || code === "STALE_REVISION") return "This note changed before your action finished. Refresh the page and try again.";
  if (code === "REVISION_ALREADY_APPROVED") return "This revision is already approved. No duplicate approval was recorded.";
  if (code === "APPROVAL_PRECONDITION_FAILED") return "This revision is not eligible for approval. Resolve the remaining review requirements and verify it again.";
  if (kind === "timeout") return "The action took too long to finish. Please try again.";
  if (kind === "unavailable" || kind === "network") return "The service is temporarily unavailable. Please try again.";
  if (kind === "validation") return "Please check the information and try again.";
  return "We could not complete that action. Please try again.";
}

export function userFacingFailureMessage(code?: string | null, message?: string | null): string {
  return userFacingApiMessage(code ?? "UNKNOWN_ERROR", message ?? "", undefined, "unknown");
}

export function normalizeApiError(error: unknown): ApiError { return error instanceof ApiError ? error : new ApiError("The service is temporarily unavailable. Please try again.", { kind: "network", code: "NETWORK_UNAVAILABLE", technicalMessage: "An unknown client-side error occurred.", retryable: true }); }
export function apiErrorFromPayload(payload: unknown, status: number): ApiError {
  const body = typeof payload === "object" && payload !== null ? payload as Record<string, unknown> : {};
  const code = typeof body.code === "string" ? body.code : "HTTP_ERROR";
  const message = typeof body.message === "string" ? body.message : "Die Anfrage konnte nicht verarbeitet werden.";
  const kind: ApiErrorKind = status === 404 ? "not-found" : status === 409 ? "conflict" : status === 408 || status === 504 ? "timeout" : status === 422 || status === 400 ? "validation" : status >= 500 ? "unavailable" : "unknown";
  const field = typeof body.field === "string" ? body.field : undefined;
  const details = typeof body.details === "object" && body.details !== null ? body.details as Record<string, unknown> : undefined;
  return new ApiError(userFacingApiMessage(code, message, field, kind), { kind, code, status, field, details, technicalMessage: message, retryable: kind === "timeout" || kind === "unavailable" });
}
