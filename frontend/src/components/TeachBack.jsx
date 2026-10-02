import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const SpeechRecognitionAPI =
  typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);

export default function TeachBack({ userId }) {
  const [concepts, setConcepts] = useState([]);
  const [conceptId, setConceptId] = useState("");
  const [explanation, setExplanation] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [listening, setListening] = useState(false);
  const [related, setRelated] = useState([]);
  const recognitionRef = React.useRef(null);

  function toggleVoice() {
    if (!SpeechRecognitionAPI) {
      setError("Voice input isn't supported in this browser — try Chrome or Edge, or just type your explanation.");
      return;
    }
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const rec = new SpeechRecognitionAPI();
    rec.lang = "en-US";
    rec.interimResults = true;
    rec.continuous = true;
    let finalText = "";
    rec.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += transcript + " ";
        else interim += transcript;
      }
      setExplanation((finalText + interim).trim());
    };
    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    recognitionRef.current = rec;
    setListening(true);
    rec.start();
  }

  useEffect(() => {
    api
      .listConcepts()
      .then((list) => {
        setConcepts(list);
        if (list.length) setConceptId(list[0].id);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function submit() {
    if (!explanation.trim()) return;
    setError("");
    setBusy(true);
    setResult(null);
    try {
      const r = await api.submitTeachBack({
        user_id: userId,
        concept_id: conceptId,
        explanation,
      });
      setResult(r);

      // score >= 80%: surface related concepts to go deeper into.
      // failed: surface related concepts as "learn more" background reading.
      // Either way, ground the search in the concept's own name so results
      // are genuinely related rather than generic.
      const conceptName = concepts.find((c) => c.id === conceptId)?.name || conceptId;
      if (r.grade.score >= 0.8 || !r.grade.passed) {
        try {
          const hits = await api.searchConcepts(conceptName, 4);
          setRelated(hits.filter((h) => h.concept_id !== conceptId));
        } catch {
          setRelated([]);
        }
      } else {
        setRelated([]);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function tryAgain(clearText) {
    setResult(null);
    setRelated([]);
    if (clearText) setExplanation("");
  }

  return (
    <>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <div className="label">Teach-Back</div>
        <h2>Explain it like I'm the one who's confused</h2>
        <p className="small">
          Pick a concept and explain it in your own words. RootCause checks
          your explanation against the ideas that actually matter — not the
          exact wording.
        </p>
        <select value={conceptId} onChange={(e) => setConceptId(e.target.value)}>
          {concepts.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <div style={{ marginTop: 10 }}>
          <textarea
            value={explanation}
            onChange={(e) => setExplanation(e.target.value)}
            placeholder="Explain this concept as if teaching a beginner… or use the mic"
          />
        </div>
        <div className="row">
          <button className="primary" disabled={busy || !explanation.trim()} onClick={submit}>
            {busy ? "Grading…" : "Submit explanation"}
          </button>
          <button className="ghost" onClick={toggleVoice} aria-label={listening ? "Stop voice recording" : "Start voice recording"}>
            {listening ? "⏹ Stop recording" : "🎙 Speak your answer"}
          </button>
          {listening && <span className="small">Listening…</span>}
        </div>
      </div>

      {result && (
        <div className="card">
          <div className={`feedback ${result.grade.passed ? "pass" : "fail"}`}>
            <strong>
              {result.grade.passed ? "That covers it." : "Not quite there yet."}
            </strong>{" "}
            {result.grade.feedback}
            <div className="small" style={{ marginTop: 8 }}>
              Score: {(result.grade.score * 100).toFixed(0)}%
            </div>
          </div>

          {result.grade.matched.length > 0 && (
            <>
              <div className="label" style={{ marginTop: 14 }}>
                You covered
              </div>
              <ul className="key-points">
                {result.grade.matched.map((m, i) => (
                  <li key={i}>{m}</li>
                ))}
              </ul>
            </>
          )}

          {result.followup_question && (
            <div className="feedback fail" style={{ marginTop: 14 }}>
              <strong>Naive persona asks:</strong> {result.followup_question}
            </div>
          )}

          {related.length > 0 && (
            <div style={{ marginTop: 14 }}>
              <div className="label">
                {result.grade.score >= 0.8 ? "Go deeper" : "Learn more before revising"}
              </div>
              {related.map((h) => (
                <div key={h.concept_id} style={{ marginBottom: 8 }}>
                  <strong style={{ fontSize: 13 }}>{h.name}</strong>
                  <p className="small" style={{ margin: "2px 0" }}>
                    {h.summary}
                  </p>
                  <button className="ghost" onClick={() => { setConceptId(h.concept_id); setResult(null); setExplanation(""); }}>
                    Teach back this one
                  </button>
                </div>
              ))}
            </div>
          )}

          <div style={{ marginTop: 14 }}>
            <button className="primary" onClick={() => tryAgain(result.grade.passed)}>
              {result.grade.passed ? "Try another concept" : "Revise your answer"}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
