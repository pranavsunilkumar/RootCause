import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function BugHunt({ userId }) {
  const [conceptIds, setConceptIds] = useState([]);
  const [conceptNames, setConceptNames] = useState({});
  const [conceptId, setConceptId] = useState("");
  const [snippet, setSnippet] = useState(null);
  const [guess, setGuess] = useState("");
  const [hintRequested, setHintRequested] = useState(false);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.listBugHuntConcepts(), api.listConcepts()])
      .then(([ids, all]) => {
        setConceptIds(ids);
        setConceptNames(Object.fromEntries(all.map((c) => [c.id, c.name])));
        if (ids.length) setConceptId(ids[0]);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function loadSnippet(id) {
    setError("");
    setBusy(true);
    setResult(null);
    setGuess("");
    setHintRequested(false);
    try {
      const s = await api.getBugSnippet(id);
      setSnippet(s);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (conceptId) loadSnippet(conceptId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conceptId]);

  async function submitGuess() {
    if (!guess) return;
    setError("");
    setBusy(true);
    try {
      const r = await api.submitBugGuess({
        user_id: userId,
        concept_id: conceptId,
        guessed_line: Number(guess),
        hint_requested: hintRequested,
      });
      setResult(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <div className="label">Bug Hunt</div>
        <h2>Find the misconception-bug</h2>
        <p className="small">
          Every snippet has exactly one deliberate bug that encodes a common
          misunderstanding. Which line is it?
        </p>
        <select value={conceptId} onChange={(e) => setConceptId(e.target.value)}>
          {conceptIds.map((id) => (
            <option key={id} value={id}>
              {conceptNames[id] || id}
            </option>
          ))}
        </select>
      </div>

      {snippet && (
        <div className="card">
          <pre className="code">
            {snippet.code.split("\n").map((line, i) => (
              <span className="line" key={i}>
                <span className="line-num">{i + 1}</span>
                {line}
              </span>
            ))}
          </pre>

          <div className="grid-2" style={{ marginTop: 14, alignItems: "end" }}>
            <div>
              <div className="small" style={{ marginBottom: 6 }}>
                Which line number is buggy? (1–{snippet.num_lines})
              </div>
              <input
                type="number"
                min={1}
                max={snippet.num_lines}
                value={guess}
                onChange={(e) => setGuess(e.target.value)}
              />
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button className="primary" disabled={busy || !guess} onClick={submitGuess}>
                Submit guess
              </button>
              <button
                className="ghost"
                onClick={() => setHintRequested(true)}
                disabled={hintRequested}
              >
                Use a hint next time
              </button>
            </div>
          </div>

          {result && (
            <div className={`feedback ${result.correct_line ? "pass" : "fail"}`}>
              <strong>{result.feedback}</strong>
              <p style={{ marginBottom: 6 }}>{result.misconception}</p>
              <div className="small" style={{ marginBottom: 4 }}>
                Fixed version:
              </div>
              <pre className="code" style={{ marginTop: 0 }}>
                {result.fixed_code}
              </pre>
              <button
                className="ghost"
                style={{ marginTop: 10 }}
                onClick={() => loadSnippet(conceptId)}
              >
                Try another snippet
              </button>
            </div>
          )}
        </div>
      )}
    </>
  );
}
