import React, { useState } from "react";
import { api, auth } from "../api.js";

export default function Login({ onAuthed }) {
  const [mode, setMode] = useState("login"); // login | register | forgot | reset
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [devToken, setDevToken] = useState("");
  const [info, setInfo] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setError("");
    setInfo("");
    setBusy(true);
    try {
      if (mode === "login" || mode === "register") {
        const res = mode === "login" ? await api.login(username, password) : await api.register(username, email, password);
        auth.setToken(res.access_token);
        onAuthed(res.user);
      } else if (mode === "forgot") {
        const res = await api.forgotPassword(username);
        setInfo(res.message);
        if (res.dev_reset_token) {
          setDevToken(res.dev_reset_token);
          setResetToken(res.dev_reset_token);
        }
        setMode("reset");
      } else if (mode === "reset") {
        const res = await api.resetPassword(resetToken, password);
        auth.setToken(res.access_token);
        onAuthed(res.user);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const titles = { login: "Log in", register: "Create an account", forgot: "Forgot password", reset: "Set a new password" };

  return (
    <div className="card">
      <div className="label">{titles[mode]}</div>
      <h2>
        {mode === "login" && "Welcome back"}
        {mode === "register" && "Track your progress with a real account"}
        {mode === "forgot" && "We'll get you a reset token"}
        {mode === "reset" && "Paste the token, pick a new password"}
      </h2>
      {mode !== "forgot" && mode !== "reset" && (
        <p className="small">
          Optional — RootCause works fine with just a name. Logging in gets
          you a leaderboard entry that can't be spoofed, and progress that
          follows you across devices.
        </p>
      )}

      {error && <div className="error-banner">{error}</div>}
      {info && <div className="feedback pass">{info}</div>}
      {devToken && (
        <div className="feedback fail">
          <strong>Dev mode:</strong> no email provider is configured, so here's
          your reset token directly (never do this in production):
          <pre style={{ marginTop: 6, fontSize: 11 }}>{devToken}</pre>
        </div>
      )}

      {(mode === "login" || mode === "register" || mode === "forgot") && (
        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          style={{ marginBottom: 8 }}
        />
      )}
      {mode === "register" && (
        <input
          type="text"
          placeholder="Email (optional)"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{ marginBottom: 8 }}
        />
      )}
      {mode === "reset" && (
        <input
          type="text"
          placeholder="Reset token"
          value={resetToken}
          onChange={(e) => setResetToken(e.target.value)}
          style={{ marginBottom: 8 }}
        />
      )}
      {(mode === "login" || mode === "register" || mode === "reset") && (
        <input
          type="password"
          placeholder="Password (min 8 characters)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      )}

      <div className="row">
        <button
          className="primary"
          disabled={busy || (mode === "forgot" ? !username : mode === "reset" ? !resetToken || !password : !username || !password)}
          onClick={submit}
        >
          {busy ? "Working…" : mode === "login" ? "Log in" : mode === "register" ? "Create account" : mode === "forgot" ? "Send reset token" : "Set new password"}
        </button>
        {mode === "login" && (
          <>
            <button className="ghost" onClick={() => setMode("register")}>Need an account? Register</button>
            <button className="ghost" onClick={() => setMode("forgot")}>Forgot password?</button>
          </>
        )}
        {mode !== "login" && (
          <button className="ghost" onClick={() => setMode("login")}>Back to log in</button>
        )}
      </div>
    </div>
  );
}
