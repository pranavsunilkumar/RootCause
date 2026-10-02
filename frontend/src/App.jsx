import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import Diagnose from "./components/Diagnose.jsx";
import BugHunt from "./components/BugHunt.jsx";
import TeachBack from "./components/TeachBack.jsx";
import Progress from "./components/Progress.jsx";
import Path from "./components/Path.jsx";
import Home from "./components/Home.jsx";
import Profile from "./components/Profile.jsx";
import Leaderboard from "./components/Leaderboard.jsx";
import Analytics from "./components/Analytics.jsx";

const TABS = [
  { id: "home", label: "Home" },
  { id: "diagnose", label: "Diagnose" },
  { id: "bughunt", label: "Bug Hunt" },
  { id: "teachback", label: "Teach-Back" },
  { id: "path", label: "Path" },
  { id: "progress", label: "Progress" },
  { id: "profile", label: "Profile" },
  { id: "leaderboard", label: "Leaderboard" },
  { id: "analytics", label: "Analytics" },
];

const USER_KEY = "rootcause_user_id";

export default function App() {
  const [tab, setTab] = useState("home");
  const [userId, setUserId] = useState(() => localStorage.getItem(USER_KEY) || "");
  const [nameInput, setNameInput] = useState("");
  const [apiDown, setApiDown] = useState(false);
  const [prefillTarget, setPrefillTarget] = useState(null);

  useEffect(() => {
    api.health().catch(() => setApiDown(true));
  }, []);

  function saveName(v) {
    const name = (v || "").trim();
    if (!name) return;
    localStorage.setItem(USER_KEY, name);
    setUserId(name);
  }

  function changeName() {
    localStorage.removeItem(USER_KEY);
    setNameInput("");
    setUserId("");
  }

  function diagnoseConcept(conceptId) {
    setPrefillTarget(conceptId);
    setTab("diagnose");
  }

  if (apiDown) {
    return (
      <div className="error-banner" style={{ margin: 20 }}>
        Can't reach the RootCause API at the configured URL. Start the backend
        (<code>uvicorn app.main:app --reload --port 8000</code>) or check{" "}
        <code>VITE_API_BASE</code> in your <code>.env</code>.
      </div>
    );
  }

  // --- NAME GATE: no accounts, just a display name saved locally ---
  if (!userId) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "80vh" }}>
        <div className="card" style={{ width: "100%", maxWidth: 400, padding: 32, textAlign: "center" }}>
          <div className="brand" style={{ marginBottom: 8 }}>
            Root<em>Cause</em>
          </div>
          <p className="small" style={{ marginBottom: 24 }}>
            Diagnoses which upstream AI/ML concept actually broke.
          </p>
          <h2 style={{ fontSize: 20, marginBottom: 16 }}>What should we call you?</h2>
          <input
            type="text"
            placeholder="e.g., student_01"
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && saveName(nameInput)}
            autoFocus
            style={{ marginBottom: 14 }}
          />
          <button className="primary" style={{ width: "100%" }} onClick={() => saveName(nameInput)}>
            Continue
          </button>
          <p className="small" style={{ marginTop: 14 }}>
            No account needed — progress is saved in this browser.
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <header className="app-header">
        <div>
          <div className="brand">
            Root<em>Cause</em>
          </div>
          <div className="small" style={{ marginTop: 4 }}>
            Diagnoses which upstream AI/ML concept actually broke.
          </div>
        </div>
        <nav className="tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={tab === t.id ? "active" : ""}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>

        {/* Username display -- "change name" lives in the Profile tab now */}
        <div
          style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", paddingRight: 48 }}
          onClick={() => setTab("profile")}
          title="Go to profile"
        >
          <span
            style={{
              width: 28,
              height: 28,
              borderRadius: "50%",
              background: "var(--gold)",
              color: "#0e0b08",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              fontSize: 13,
              textTransform: "uppercase",
              flexShrink: 0,
            }}
          >
            {userId.charAt(0)}
          </span>
          <strong style={{ color: "var(--gold)", fontSize: 13 }}>{userId}</strong>
        </div>
      </header>

      {tab === "home" && <Home onNavigate={setTab} userId={userId} />}
      {tab === "diagnose" && (
        <Diagnose userId={userId} initialTargetId={prefillTarget} onConsumedInitialTarget={() => setPrefillTarget(null)} />
      )}
      {tab === "bughunt" && <BugHunt userId={userId} />}
      {tab === "teachback" && <TeachBack userId={userId} />}
      {tab === "path" && <Path userId={userId} onDiagnoseConcept={diagnoseConcept} />}
      {tab === "progress" && <Progress userId={userId} onDiagnoseConcept={diagnoseConcept} />}
      {tab === "profile" && <Profile userId={userId} onChangeName={changeName} />}
      {tab === "leaderboard" && <Leaderboard userId={userId} />}
      {tab === "analytics" && <Analytics />}

      <footer className="app-footer">
        <span>RootCause · Team Kuch bhi · AI Build Challenge 2026 (PS-03)</span>
        <span>
          <a href="https://buildfastwithai.com/hackathon" target="_blank" rel="noreferrer">
            buildfastwithai.com/hackathon
          </a>
        </span>
      </footer>
    </>
  );
}