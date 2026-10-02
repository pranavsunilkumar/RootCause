import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Analytics() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getAnalytics().then(setData).catch((e) => setError(e.message));
  }, []);

  return (
    <>
      {error && <div className="error-banner">{error}</div>}
      <div className="card">
        <div className="label">Analytics</div>
        <h2>Platform-wide learning data</h2>
        <p className="small">Live aggregates over every attempt, across every learner.</p>
      </div>

      {data && (
        <>
          <div className="stat-row">
            <Stat n={data.active_learners} l="Active learners" />
            <Stat n={data.total_attempts} l="Total attempts" />
            <Stat n={`${(data.overall_pass_rate * 100).toFixed(0)}%`} l="Pass rate" />
            <Stat n={data.total_mastered} l="Concepts mastered" />
          </div>

          <div className="card">
            <h2 style={{ fontSize: 18 }}>By mode</h2>
            {data.by_mode.map((m) => (
              <BarRow key={m.mode} label={m.mode} value={m.pass_rate} sub={`${m.passes}/${m.attempts} passed`} />
            ))}
          </div>

          <div className="grid-2">
            <div className="card">
              <h2 style={{ fontSize: 18 }}>Hardest concepts</h2>
              <p className="small">Lowest pass rate (min. 2 attempts) — candidates for a better lesson or probe.</p>
              {data.hardest_concepts.length === 0 && <p className="small">Not enough data yet.</p>}
              {data.hardest_concepts.map((c) => (
                <BarRow key={c.concept_id} label={c.name} value={c.pass_rate} sub={`${c.attempts} attempts`} />
              ))}
            </div>
            <div className="card">
              <h2 style={{ fontSize: 18 }}>Most practiced</h2>
              {data.most_practiced_concepts.length === 0 && <p className="small">Not enough data yet.</p>}
              {data.most_practiced_concepts.map((c) => (
                <BarRow key={c.concept_id} label={c.name} value={c.pass_rate} sub={`${c.attempts} attempts`} />
              ))}
            </div>
          </div>
        </>
      )}
    </>
  );
}

function Stat({ n, l }) {
  return (
    <div className="stat">
      <div className="n">{n}</div>
      <div className="l">{l}</div>
    </div>
  );
}

function BarRow({ label, value, sub }) {
  const pct = Math.round(value * 100);
  return (
    <div className="bar-row">
      <div style={{ width: 140, fontSize: 13 }}>{label}</div>
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="small" style={{ width: 110, textAlign: "right" }}>
        {pct}% · {sub}
      </div>
    </div>
  );
}
