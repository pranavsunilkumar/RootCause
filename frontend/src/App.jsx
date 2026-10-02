import React, { useEffect, useState } from "react";
import { api, auth } from "./api.js";
import Auth from "./components/Auth.jsx"; // Imported new Auth gate
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

export default function App() {
  const [tab, setTab] = useState("home");
  const [account, setAccount] = useState(null);
  const [apiDown, setApiDown] = useState(false);
  const [prefillTarget, setPrefillTarget] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.health().catch(() => setApiDown(true));
    
    // Check session on load
    if (auth.isLoggedIn()) {
      api.me()
        .then((u) => setAccount(u))
        .catch(() => auth.clearToken())
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  function handleAuthSuccess(token, username) {
    auth.setToken(token);
    setAccount({ username }); // Briefly set username until api.me() syncs it
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

  if (apiDown) {
    return (
      <div className="error-banner" style={{ margin: 20 }}>
        Can't reach the RootCause API at the configured URL. Start the backend
        (<code>uvicorn app.main:app --reload --port 8000</code>) or check{" "}
        <code>VITE_API_BASE</code> in your <code>.env</code>.
      </div>
    );
  }

  if (isLoading) {
    return <div style={{ padding: 40, color: "var(--gold)" }}>Verifying session...</div>;
  }

  // --- STRICT AUTHENTICATION GATE ---
  if (!account) {
    return (
      <div id="root">
        <Auth onAuthSuccess={handleAuthSuccess} />
      </div>
    );
  }

  const userId = account.username;

  // --- SECURE MAIN APPLICATION ---
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
        
        {/* Username display -- logout lives in the Profile tab now */}
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
      {tab === "profile" && <Profile userId={userId} account={account} onLogout={logout} />}
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