import React, { useEffect, useState } from "react";
import { api, auth } from "./api.js";
import Diagnose from "./components/Diagnose.jsx";
import BugHunt from "./components/BugHunt.jsx";
import TeachBack from "./components/TeachBack.jsx";
import Progress from "./components/Progress.jsx";
import Path from "./components/Path.jsx";
import Home from "./components/Home.jsx";
import Login from "./components/Login.jsx";
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
  const [userId, setUserId] = useState(() => localStorage.getItem(USER_KEY) || "demo-learner");
  const [editingName, setEditingName] = useState(() => !localStorage.getItem(USER_KEY));
  const [apiDown, setApiDown] = useState(false);
  const [prefillTarget, setPrefillTarget] = useState(null);
  const [account, setAccount] = useState(null);

  function saveName(v) {
    const name = (v || "").trim() || "demo-learner";
    setUserId(name);
    setEditingName(false);
  }

  useEffect(() => {
    if (auth.isLoggedIn()) {
      api
        .me()
        .then((u) => {
          setAccount(u);
          setUserId(u.username); // logged-in identity always wins over the free-text id
        })
        .catch(() => auth.clearToken());
    }
  }, []);

  function handleAuthed(user) {
    setAccount(user);
    setUserId(user.username);
    setTab("home");
  }

  function logout() {
    auth.clearToken();
    setAccount(null);
  }

  function diagnoseConcept(conceptId) {
    setPrefillTarget(conceptId);
    setTab("diagnose");
  }

  useEffect(() => {
    localStorage.setItem(USER_KEY, userId);
  }, [userId]);

  useEffect(() => {
    api.health().catch(() => setApiDown(true));
  }, []);

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
      </header>

      {apiDown && (
        <div className="error-banner">
          Can't reach the RootCause API at the configured URL. Start the backend
          (<code>uvicorn app.main:app --reload --port 8000</code>) or check{" "}
          <code>VITE_API_BASE</code> in your <code>.env</code>.
        </div>
      )}

      <div className="card" style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        {account ? (
          <>
            <span className="small">Logged in as</span>
            <strong>{account.username}</strong>
            <button className="ghost" onClick={logout}>
              Log out
            </button>
          </>
        ) : editingName ? (
          <>
            <span className="small">What should we call you?</span>
            <input
              type="text"
              style={{ maxWidth: 220 }}
              placeholder="Your name"
              defaultValue={localStorage.getItem(USER_KEY) || ""}
              onKeyDown={(e) => e.key === "Enter" && saveName(e.currentTarget.value)}
              autoFocus
              id="nameInput"
            />
            <button className="ghost" onClick={() => saveName(document.getElementById("nameInput").value)}>
              Save
            </button>
          </>
        ) : (
          <>
            <span>
              👋 Hi, <strong>{userId}</strong>
            </span>
            <button className="ghost" onClick={() => setEditingName(true)}>
              Not you?
            </button>
            <span className="small">— progress is saved in this browser only, or</span>
            <button className="ghost" onClick={() => setTab("login")}>
              log in for a real account
            </button>
          </>
        )}
      </div>

      {tab === "home" && <Home onNavigate={setTab} userId={userId} />}
      {tab === "diagnose" && (
        <Diagnose userId={userId} initialTargetId={prefillTarget} onConsumedInitialTarget={() => setPrefillTarget(null)} />
      )}
      {tab === "bughunt" && <BugHunt userId={userId} />}
      {tab === "teachback" && <TeachBack userId={userId} />}
      {tab === "path" && <Path userId={userId} onDiagnoseConcept={diagnoseConcept} />}
      {tab === "progress" && <Progress userId={userId} onDiagnoseConcept={diagnoseConcept} />}
      {tab === "login" && <Login onAuthed={handleAuthed} />}
      {tab === "profile" && <Profile userId={userId} account={account} />}
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
