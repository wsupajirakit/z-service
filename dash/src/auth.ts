import axios from 'axios';
import { API_BASE } from './core';

// The JS-set session cookie travels over https only (plain http is local development).
const SECURE = location.protocol === 'https:' ? '; secure' : '';

/**
 * Single-user auth wiring. The login page (public/login.html) stores the JWT;
 * here we attach it to every API call and bounce back to /login when it is
 * missing or expired (tokens last 24h).
 */
export function setupAuth() {
  const token = localStorage.getItem('z_token');

  axios.interceptors.request.use((config) => {
    const t = localStorage.getItem('z_token');
    if (t) config.headers.Authorization = `Bearer ${t}`;
    return config;
  });

  axios.interceptors.response.use(
    (res) => res,
    (err) => {
      if (err?.response?.status === 401) logout();
      return Promise.reject(err);
    },
  );

  // Keep the cookie fresh so a hard page load passes the server-side gate.
  if (token) {
    document.cookie = `z_token=${token}; path=/; max-age=86400; samesite=lax${SECURE}`;
  } else {
    logout();
  }
}

export function logout() {
  localStorage.removeItem('z_token');
  document.cookie = `z_token=; path=/; max-age=0; samesite=lax${SECURE}`;
  if (!location.pathname.startsWith('/login')) location.href = '/login';
}

/** Keep a token the server issued (after a password change the old ones are revoked). */
export function storeToken(token: string) {
  localStorage.setItem('z_token', token);
  document.cookie = `z_token=${token}; path=/; max-age=86400; samesite=lax${SECURE}`;
}

export type Account = { username: string; expiresAt: number | null };

/** Who is signed in, read from the stored token (display only; the server checks it). */
export function currentAccount(): Account | null {
  const token = localStorage.getItem('z_token');
  if (!token) return null;
  try {
    const part = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const payload = JSON.parse(atob(part.padEnd(part.length + ((4 - (part.length % 4)) % 4), '=')));
    return { username: String(payload.sub ?? ''), expiresAt: typeof payload.exp === 'number' ? payload.exp * 1000 : null };
  } catch {
    return null;
  }
}

/** End the session on the server too (the token is revoked), then leave for /login. */
export async function signOut() {
  try {
    await axios.post(`${API_BASE}/api/auth/logout`);
  } catch { /* the local sign-out below still happens */ }
  logout();
}
