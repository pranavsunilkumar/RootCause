import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Profile({ userId, account, onLogout }) {
  const [gami, setGami] = useState(null);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getGamification(userId).then(setGami).catch((e) => setError(e.message));
    api.getProgress(userId).then(setProgress).catch((e) => setError(e.message));
  }, [userId]);

  return (
    <>
      {error && <div className="error-banner">{error}</div>}
      <div className="card">
        <div className="label">Profile</div>
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 4 }}>
          <span
            style={{
              width: 56,
              height: 56,
              borderRadius: "50%",
              background: "var(--gold)",
              color: "#0e0b08",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              fontSize: 24,
              textTransform: "uppercase",
              flexShrink: 0,
            }}
          >
            {userId.charAt(0)}
          </span>
          <div>
            <h2 style={{ margin: 0, textTransform: "capitalize" }}>{userId}</h2>
            {account ? (
              <p className="small" style={{ margin: "2px 0 0" }}>
                Logged in{account.email ? ` · ${account.email}` : ""} — a real account, progress follows you anywhere.
              </p>
            ) : (
              <p className="small" style={{ margin: "2px 0 0" }}>
                Anonymous / browser-local learner. Log in to keep this progress on other devices.
              </p>
            )}
          </div>
        </div>
      </div>

      {gami && (
        <>
          <div className="stat-row">
            <div className="stat"><div className="n">{gami.points}</div><div className="l">Points</div></div>
            <div className="stat"><div className="n">{gami.mastered_count}</div><div className="l">Mastered</div></div>
            <div className="stat"><div className="n">{gami.current_streak}</div><div className="l">Streak</div></div>
          </div>
          <div className="card">
            <div className="label">Badges</div>
            {gami.badges.length === 0 && <p className="small">None yet — master your first concept to earn one.</p>}
            {gami.badges.map((b) => (
              <span className="badge" key={b.code} title={b.description}>{b.name}</span>
            ))}
          </div>
        </>
      )}

      {progress && (
        <div className="card">
          <div className="label">Breakdown</div>
          <div className="bar-row"><span style={{ width: 90, fontSize: 13 }}>Mastered</span>
            <div className="bar-track"><div className="bar-fill" style={{ width: `${(progress.mastered/progress.entries.length*100)||0}%` }} /></div>
            <span className="small">{progress.mastered}/{progress.entries.length}</span></div>
        </div>
      )}

      {onLogout && (
        <div className="card">
          <button className="ghost" onClick={onLogout} style={{ width: "100%", color: "var(--danger)" }}>
            Log out
          </button>
        </div>
      )}
    </>
  );
}
