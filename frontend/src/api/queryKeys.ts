export const queryKeys = {
  examples: ["saved-examples"] as const,
  source: (id: string, version: number) => ["source", id, version] as const,
  note: (id: string, revision: number) => ["note", id, revision] as const,
  review: (id: string, revision?: number) => ["review", id, revision ?? "latest"] as const,
  audit: (id: string) => ["audit", id] as const,
  evaluations: ["evaluation-runs"] as const,
  evaluation: (id: string) => ["evaluation-run", id] as const,
};
