const TOKEN_KEY = "gm_session_token";

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setStoredToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

async function apiFetch(path, options = {}) {
  const token = getStoredToken();
  const headers = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const res = await fetch(path, { ...options, headers });
  if (res.status === 401) {
    setStoredToken("");
    window.dispatchEvent(new Event("gm:unauthorized"));
  }

  if (!res.ok) {
    let message = `Błąd HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) {
        message =
          typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data.detail);
      }
    } catch {
      // ignore non-json error bodies
    }
    throw new Error(message);
  }

  return res.json();
}

export const api = {
  login: (username, password) =>
    apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  me: () => apiFetch("/api/auth/me"),

  listUsers: () => apiFetch("/api/users"),

  createUser: (username, password) =>
    apiFetch("/api/users", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  updateUserPassword: (username, newPassword) =>
    apiFetch(`/api/users/${encodeURIComponent(username)}/password`, {
      method: "PATCH",
      body: JSON.stringify({ new_password: newPassword }),
    }),

  setUserActive: (username, isActive) =>
    apiFetch(`/api/users/${encodeURIComponent(username)}/active`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    }),

  deleteUser: (username) =>
    apiFetch(`/api/users/${encodeURIComponent(username)}`, {
      method: "DELETE",
    }),

  listProcurements: () => apiFetch("/api/procurements"),

  getSummary: (ocdsId) =>
    apiFetch(`/api/procurements/${encodeURIComponent(ocdsId)}/summary`),

  askQuestion: (ocdsId, question, responseFormat) =>
    apiFetch(`/api/procurements/${encodeURIComponent(ocdsId)}/ask`, {
      method: "POST",
      body: JSON.stringify({ question, response_format: responseFormat }),
    }),

  askQuestionStream: async (
    ocdsId,
    question,
    responseFormat,
    { onChunks, onToken, onDone } = {},
  ) => {
    const token = getStoredToken();
    const res = await fetch(
      `/api/procurements/${encodeURIComponent(ocdsId)}/ask/stream`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ question, response_format: responseFormat }),
      },
    );

    if (res.status === 401) {
      setStoredToken("");
      window.dispatchEvent(new Event("gm:unauthorized"));
      throw new Error("Brak ważnej sesji użytkownika.");
    }
    if (!res.ok || !res.body) {
      throw new Error(`Błąd HTTP ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() || "";
      for (const frame of frames) {
        const line = frame.split("\n").find((l) => l.startsWith("data: "));
        if (!line) continue;
        const payload = JSON.parse(line.slice(6));
        if (payload.type === "chunks" && onChunks)
          onChunks(payload.chunks || []);
        if (payload.type === "token" && onToken) onToken(payload.text || "");
        if (payload.type === "done" && onDone) onDone();
      }
    }
  },

  getPdfDownloadUrl: (ocdsId) => {
    const token = getStoredToken();
    return `/api/procurements/${encodeURIComponent(ocdsId)}/report.pdf?token=${encodeURIComponent(token)}`;
  },

  getAbout: () => apiFetch("/api/system/about"),
};
