/*
 * Generated-contract boundary.
 *
 * The source of truth is specs/009-ui-implementation/contracts/openapi.yaml.
 * `npm run api:generate` refreshes this file with openapi-typescript when the
 * dependency cache is available. UI code imports transport models from
 * `types.ts`, which is a deliberately narrow projection of these contracts.
 */
export type ApiError = { code: string; message: string; field?: string | null; correlationId?: string | null; retryable?: boolean | null };
export type Health = { status: "ok" | "degraded"; database: "ready" | "unavailable" };
export type paths = Record<string, unknown>;
