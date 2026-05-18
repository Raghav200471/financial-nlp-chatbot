/**
 * api/client.js
 * Central API client — all calls to FastAPI go through here.
 * JWT token is automatically attached from localStorage.
 */

const BASE = '';  // Vite proxy handles /api, /auth, /users → localhost:8000

function getToken() {
  return localStorage.getItem('finchat_token');
}

async function request(method, path, body = null) {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (networkErr) {
    throw new Error('Cannot connect to server. Is the backend running?');
  }

  if (res.status === 401) {
    localStorage.removeItem('finchat_token');
    localStorage.removeItem('finchat_user');
    window.location.href = '/login';
    return;
  }

  // Try to parse JSON — if server returns HTML error page, handle gracefully
  let data;
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    data = await res.json();
  } else {
    // Server returned non-JSON (e.g. 500 HTML page)
    const text = await res.text();
    throw new Error(`Server error (${res.status}). Check backend logs.`);
  }

  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

// ── Auth ──────────────────────────────────────────────────
export const api = {
  register: (name, email, password) =>
    request('POST', '/auth/register', { name, email, password }),

  login: (email, password) =>
    request('POST', '/auth/login', { email, password }),

  // ── User / Chats ────────────────────────────────────────
  getMe: () => request('GET', '/users/me'),

  getChats: () => request('GET', '/users/me/chats'),

  saveChat: (session) => request('POST', '/users/me/chats', session),

  deleteChat: (chatId) => request('DELETE', `/users/me/chats/${chatId}`),

  // ── RAG Profile ─────────────────────────────────────────
  getProfile: () => request('GET', '/users/me/profile'),

  saveProfile: (profile) => request('PUT', '/users/me/profile', profile),

  // ── Chat (NLP pipeline) ─────────────────────────────────
  sendMessage: ({ message, sessionId, useBert, useGemini, userContext }) =>
    request('POST', '/api/chat', {
      message,
      session_id: sessionId,
      use_bert: useBert,
      use_gemini: useGemini,
      user_context: userContext,
    }),
};
