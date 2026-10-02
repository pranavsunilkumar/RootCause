import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const IDLE = "idle";
const ASKING = "asking";
const DONE = "done";

export default function Diagnose({ userId, initialTargetId, onConsumedInitialTarget }) {
  const [concepts, setConcepts] = useState([]);
  const [targetId, setTargetId] = useState("");
  const [phase, setPhase] = useState(IDLE);
  const [chain, setChain] = useState([]);
  const [stepIndex, setStepIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [checks, setChecks] = useState([]);
  const [diagnosis, setDiagnosis] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .listConcepts()
      .then((list) => {
        setConcepts(list);
        if (initialTargetId && list.some((c) => c.id === initialTargetId)) {
          setTargetId(initialTargetId);
          onConsumedInitialTarget?.();
        } else if (list.length) {
          setTargetId(list[list.length - 1].id);
        }
      })
      .catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function start() {
    setError("");
    setBusy(true);
    try {
      const steps = await api.getChain(targetId);
      setChain(steps);
      setStepIndex(0);
      setChecks([]);
      setDiagnosis(null);
      setAnswer("");
      setPhase(ASKING);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitAnswer() {
    setError("");
    setBusy(true);
    const step = chain[stepIndex];
    try {
      const result = await api.checkNode({
        user_id: userId,
        target_concept: targetId,
        concept_id: step.concept_id,
        answer,
      });
      const nextChecks = [...checks, result];
      setChecks(nextChecks);

      if (!result.grade.passed) {
        await finish(nextChecks);
        return;
      }

      if (stepIndex + 1 >= chain.length) {
        await finish(nextChecks);
        return;
      }

      setStepIndex(stepIndex + 1);
      setAnswer("");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function finish(finalChecks) {
    try {
      const result = await api.diagnose({
        user_id: userId,
        target_concept: targetId,
        checks: finalChecks,
      });
      setDiagnosis(result);
      setPhase(DONE);
    } catch (e) {
      setError(e.message);
    }
  }

  function reset() {
    setPhase(IDLE);
    setChain([]);
    setDiagnosis(null);
    setLastGrade(null);
  }

  return (
    <>
      {error && <div className="error-banner">{error}</div>}

      {phase === IDLE && (
        <div className="card">
          <div className="label">Diagnose</div>
          <h2>What are you stuck on?</h2>
          <p className="small">
            Pick the concept you're trying to learn. RootCause will check its
            prerequisites one at a time, starting from the most foundational,
            until it finds the one that's actually broken.
          </p>
          <select value={targetId} onChange={(e) => setTargetId(e.target.value)}>
            {concepts.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <div style={{ marginTop: 14 }}>
            <button className="primary" disabled={!targetId || busy} onClick={start}>
              Start diagnosis
            </button>
          </div>
        </div>
      )}

      {phase === ASKING && chain[stepIndex] && (
        <div className="card">
          <div className="label">
            Checking {stepIndex + 1} of {chain.length}
          </div>
          <h2>{chain[stepIndex].name}</h2>
          <p className="small" style={{ fontSize: 14, color: "var(--text)" }}>
            {chain[stepIndex].question}
          </p>
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Answer in your own words…"
            autoFocus
          />
          <div style={{ marginTop: 14, display: "flex", gap: 10 }}>
            <button className="primary" disabled={busy} onClick={submitAnswer}>
              {busy ? "Checking…" : "Submit"}
            </button>
            <button className="ghost" onClick={reset}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {phase === DONE && diagnosis && (
        <div className="card">
          <div className="label">Diagnosis</div>
          <h2>
            {diagnosis.is_target_itself
              ? "Your prerequisites are solid — the gap is in this topic itself."
              : `Found it: ${checks.find((c) => c.concept_id === diagnosis.broken_concept)?.name || diagnosis.broken_concept}`}
          </h2>
          {!diagnosis.is_target_itself && (
            <p className="small">
              That's {diagnosis.steps_upstream} step{diagnosis.steps_upstream === 1 ? "" : "s"} upstream
              of {concepts.find((c) => c.id === diagnosis.target_concept)?.name || diagnosis.target_concept} —
              re-explaining the topic you asked about wouldn't have fixed this.
            </p>
          )}
          <p style={{ fontSize: 15 }}>{diagnosis.lesson_summary}</p>

          {diagnosis.ai_explanation && (
            <div className="feedback pass" style={{ marginTop: 10 }}>
              <strong>In plain terms:</strong> {diagnosis.ai_explanation}
            </div>
          )}

          <div className="label" style={{ marginTop: 16 }}>
            Quick tips to get better
          </div>
          <ul className="key-points">
            {diagnosis.lesson_key_points.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>

          <div className="label" style={{ marginTop: 16 }}>
            Full report — every concept checked
          </div>
          {checks.map((c) => (
            <div key={c.concept_id} className="bar-row" style={{ marginBottom: 6 }}>
              <span className={`pill ${c.grade.passed ? "mastered" : "weak"}`}>
                {c.grade.passed ? "✓" : "✗"}
              </span>
              <span style={{ flex: 1, fontSize: 13 }}>{c.name}</span>
              <span className="small">{Math.round(c.grade.score * 100)}%</span>
            </div>
          ))}

          <div style={{ marginTop: 16 }}>
            <button className="primary" onClick={reset}>
              Diagnose another concept
            </button>
          </div>
        </div>
      )}
    </>
  );
}
