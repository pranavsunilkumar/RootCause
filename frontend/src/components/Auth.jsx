import React, { useState } from "react";
import { api } from "../api.js";

export default function Auth({ onAuthSuccess }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isLogin) {
        // Assuming api.login returns { access_token: "..." }
        const data = await api.login(username, password);
        onAuthSuccess(data.access_token, username);
      } else {
        // Assuming api.register creates the user, then we log them in
        await api.register(username, password);
        const data = await api.login(username, password);
        onAuthSuccess(data.access_token, username);
      }
    } catch (err) {
      setError(err.message || "Authentication failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "80vh" }}>
      <div className="card" style={{ width: "100%", maxWidth: "400px", padding: "32px" }}>
        <div className="brand" style={{ textAlign: "center", marginBottom: "8px" }}>
          Root<em>Cause</em>
        </div>
        <div className="small" style={{ textAlign: "center", marginBottom: "24px" }}>
          The AI tutor that finds what broke upstream.
        </div>

        <h2 style={{ fontSize: "20px", marginBottom: "16px", textAlign: "center" }}>
          {isLogin ? "Welcome back" : "Create your account"}
        </h2>

        {error && <div className="error-banner">{error}</div>}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "col", gap: "16px" }}>
          <div>
            <label className="small" style={{ display: "block", marginBottom: "4px", color: "var(--gold)" }}>USERNAME</label>
            <input 
              type="text" 
              value={username} 
              onChange={(e) => setUsername(e.target.value)} 
              required 
              placeholder="e.g., student_01"
            />
          </div>
          <div>
            <label className="small" style={{ display: "block", marginBottom: "4px", color: "var(--gold)" }}>PASSWORD</label>
            <input 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              required 
              placeholder="••••••••"
              style={{ width: "100%", background: "#0e0b08", border: "1px solid var(--panel-border)", color: "var(--text)", borderRadius: "10px", padding: "10px 12px", fontFamily: "var(--sans)" }}
            />
          </div>

          <button className="primary" type="submit" disabled={loading} style={{ width: "100%", marginTop: "8px" }}>
            {loading ? "Authenticating..." : (isLogin ? "Log In" : "Register")}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: "24px" }}>
          <button className="ghost" onClick={() => setIsLogin(!isLogin)} style={{ border: "none", fontSize: "12px" }}>
            {isLogin ? "Need an account? Register here." : "Already have an account? Log in."}
          </button>
        </div>
      </div>
    </div>
  );
}