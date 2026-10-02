import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Leaderboard({ userId }) {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getLeaderboard().then(setRows).catch((e) => setError(e.message));
  }, []);

  return (
    <>
      {error && <div className="error-banner">{error}</div>}
      <div className="card">
        <div className="label">Leaderboard</div>
        <h2>Points from mastered concepts &amp; passed attempts</h2>
        <p className="small">
          +10 per concept mastered, +2 per passed attempt. Badges are earned
          automatically from your history.
        </p>
      </div>

      {rows && (
        <div className="card">
          {rows.length === 0 && <p className="small">No attempts yet — be the first on the board.</p>}
          {rows.map((r, i) => (
            <div className="leader-row" key={r.user_id}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span className="rank">{i + 1}</span>
                <div>
                  <div style={{ fontWeight: 600, color: r.user_id === userId ? "var(--gold)" : "var(--text)" }}>
                    {r.user_id}
                    {r.user_id === userId ? " (you)" : ""}
                  </div>
                  <div>
                    {r.badges.map((b) => (
                      <span className="badge" key={b.code} title={b.description}>
                        {b.name}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontFamily: "var(--serif)", fontSize: 20 }}>{r.points}</div>
                <div className="small">
                  {r.mastered_count} mastered · streak {r.current_streak}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
