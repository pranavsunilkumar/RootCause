const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";
const TOKEN_KEY = "rootcause_token";

export const auth = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  setToken: (t) => localStorage.setItem(TOKEN_KEY, t),
  clearToken: () => localStorage.removeItem(TOKEN_KEY),
  isLoggedIn: () => !!localStorage.getItem(TOKEN_KEY),
};

async function request(path, options = {}) {
  const token = auth.getToken();
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...options,
  });
  if (res.status === 401 && token) {
    // token expired/invalid -- drop it and fall back to anonymous mode
    // rather than getting the user stuck in a broken logged-in state
    auth.clearToken();
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status} ${detail}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

async function requestForm(path, formBody) {
  const res = await fetch(`${BASE}${path}`, { method: "POST", body: formBody });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json();
}

export const api = {
  health: () => request("/health"),
  listConcepts: () => request("/concepts"),
  getChain: (conceptId) => request(`/concepts/${encodeURIComponent(conceptId)}/chain`),

  checkNode: (body) =>
    request("/diagnose/check", { method: "POST", body: JSON.stringify(body) }),
  diagnose: (body) => request("/diagnose", { method: "POST", body: JSON.stringify(body) }),

  listBugHuntConcepts: () => request("/bughunt"),
  getBugSnippet: (conceptId) => request(`/bughunt/${encodeURIComponent(conceptId)}`),
  submitBugGuess: (body) =>
    request("/bughunt/guess", { method: "POST", body: JSON.stringify(body) }),

  submitTeachBack: (body) =>
    request("/teachback", { method: "POST", body: JSON.stringify(body) }),

  getProgress: (userId) => request(`/progress/${encodeURIComponent(userId)}`),
  getNextStep: (userId) => request(`/path/${encodeURIComponent(userId)}`),

  register: (username, email, password) =>
    request("/auth/register", { method: "POST", body: JSON.stringify({ username, email: email || null, password }) }),
  login: (username, password) => {
    const form = new URLSearchParams();
    form.set("username", username);
    form.set("password", password);
    return requestForm("/auth/login", form);
  },
  me: () => request("/auth/me"),
  forgotPassword: (username) => request("/auth/forgot-password", { method: "POST", body: JSON.stringify({ username }) }),
  resetPassword: (resetToken, newPassword) =>
    request("/auth/reset-password", { method: "POST", body: JSON.stringify({ reset_token: resetToken, new_password: newPassword }) }),

  getGamification: (userId) => request(`/gamification/${encodeURIComponent(userId)}`),
  getLeaderboard: (limit = 20) => request(`/leaderboard?limit=${limit}`),
  getAnalytics: () => request("/analytics/overview"),
  getRecommendations: (userId, limit = 5) =>
    request(`/recommendations/${encodeURIComponent(userId)}?limit=${limit}`),
  searchConcepts: (q, topK = 5) => request(`/search?q=${encodeURIComponent(q)}&top_k=${topK}`),
  ask: (query) => request("/ask", { method: "POST", body: JSON.stringify({ query }) }),
};
