import { useNavigate } from "react-router-dom";
import { safeMutationError, useStartFounderDemo } from "../../api/hooks";
import { useWorkspace } from "../../state/workspace";

export function FounderDemoPage() {
  const navigate = useNavigate();
  const { setDemo, setSource, applyNoteRevision, setDraftContent } = useWorkspace();
  const start = useStartFounderDemo();

  async function startDemo() {
    try {
      const demo = await start.mutateAsync();
      setDemo(demo);
      setSource(demo.source);
      applyNoteRevision(demo.note);
      setDraftContent(demo.note.content);
      navigate("/documentation");
    } catch {
      // The visible error below preserves the current workspace state.
    }
  }

  return <section className="demo-landing" aria-labelledby="demo-title">
    <span className="eyebrow">SYNTHETIC FOUNDER WALKTHROUGH</span>
    <h2 id="demo-title">See how Dexter Guard catches unsupported nursing documentation.</h2>
    <p>Start with one realistic synthetic transcript and an intentionally altered note. Inspect the evidence, correct the note, re-verify the saved revision, and make the final human approval.</p>
    <ol className="demo-steps-preview" aria-label="Guided demo stages">
      <li><strong>1. Inspect</strong><span>Compare transcript and note.</span></li>
      <li><strong>2. Verify</strong><span>See evidence-linked issues.</span></li>
      <li><strong>3. Correct</strong><span>Save a successor revision.</span></li>
      <li><strong>4. Approve</strong><span>Record the human decision.</span></li>
    </ol>
    {start.error && <p className="error-banner" role="alert">{safeMutationError(start.error).message}</p>}
    <div className="button-row"><button onClick={startDemo} disabled={start.isPending}>{start.isPending ? "Preparing demo …" : "Start guided demo"}</button><button className="secondary-button" onClick={() => navigate("/documentation")}>Explore workspace</button></div>
    <p className="muted">Synthetic data only. The demonstration does not make a clinical decision or approve a note automatically.</p>
  </section>;
}
