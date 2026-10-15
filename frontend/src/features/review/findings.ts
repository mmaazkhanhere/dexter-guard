import type { Finding, ReviewDecision } from "../../api/types";

export function isFindingUnresolved(finding: Finding, decisions: ReviewDecision[]): boolean {
  if (finding.state !== "OPEN" && finding.state !== "STALE") return false;
  const latestDecision = decisions.filter((decision) => decision.findingId === finding.reviewFindingId && decision.noteRevision === finding.noteRevision).at(-1);
  return latestDecision?.outcome !== "ADJUDICATED" && latestDecision?.outcome !== "RESOLVED";
}
