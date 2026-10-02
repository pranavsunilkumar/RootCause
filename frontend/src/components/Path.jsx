import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const REASON_LABEL = {
  weakest_link: "Weakest link",
  next_unlocked: "Next unlocked",
  next_root: "Starting point",
  all_mastered: "All mastered",
};

export default function Path({ userId, onDiagnoseConcept }) {
  const [step, setStep] = useState(null);
  const [recs, setRecs] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  function load() {
    setError("");
    setLoading(true);
    Promise.all([api.getNextStep(userId), api.getRecommendations(userId)])
      .then(([s, r]) => {
        setStep(s);
        setRecs(r);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [userId]);

  return (
    <>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <div className="label">Personalized Path</div>
        <h2>What should {userId} study next?</h2>
        <p className="small">
          Auto-sequenced from the mastery map: the most foundational weak
          concept if there is one, otherwise the next concept whose
          prerequisites are already mastered.
        </p>
        <button className="ghost" onClick={load}>
          Refresh
        </button>
      </div>

      {!loading && step && (
        <div className="card">
          {step.concept_id ? (
            <>
              <span className="pill weak" style={{ marginBottom: 10, display: "inline-block" }}>
                {REASON_LABEL[step.reason_code] || step.reason_code}
              </span>
              <h2>{step.name}</h2>
              <p className="small" style={{ fontSize: 14, color: "var(--text)" }}>
                {step.reason}
              </p>
              <div style={{ marginTop: 14 }}>
                <button
                  className="primary"
                  onClick={() => onDiagnoseConcept(step.concept_id)}
                >
                  Diagnose this concept
                </button>
              </div>
            </>
          ) : (
            <>
              <span className="pill mastered" style={{ marginBottom: 10, display: "inline-block" }}>
                {REASON_LABEL[step.reason_code] || step.reason_code}
              </span>
              <h2>Nothing left to queue up</h2>
              <p className="small">{step.reason}</p>
            </>
          )}
        </div>
      )}

      {recs && recs.length > 0 && (
        <div className="card">
          <div className="label">More recommendations</div>
          <h2 style={{ fontSize: 18 }}>Also worth a look</h2>
          {recs.map((r) => (
            <div key={r.concept_id} style={{ marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong>{r.name}</strong>
                <span className={`pill ${r.status}`}>{r.status}</span>
              </div>
              <p className="small" style={{ margin: "4px 0" }}>
                {r.reason}
              </p>
              {r.related.length > 0 && (
                <p className="small">Related: {r.related.map((h) => h.name).join(", ")}</p>
              )}
              <button
                className="ghost"
                onClick={() => onDiagnoseConcept(r.concept_id)}
                style={{ marginTop: 4 }}
              >
                Diagnose this
              </button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
