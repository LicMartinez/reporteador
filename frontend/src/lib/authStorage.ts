const TOKEN_KEY = 'swisstools_token';
const USER_KEY = 'swisstools_user';
const LEGACY_TOKEN = 'restbar_token';
const LEGACY_USER = 'restbar_user';

/** Migra restbar_* → swisstools_* si faltan las claves nuevas. Idempotente. */
export function migrateLegacyAuthStorage(): void {
  try {
    if (!localStorage.getItem(TOKEN_KEY) && localStorage.getItem(LEGACY_TOKEN)) {
      localStorage.setItem(TOKEN_KEY, localStorage.getItem(LEGACY_TOKEN)!);
      localStorage.removeItem(LEGACY_TOKEN);
    }
    if (!localStorage.getItem(USER_KEY) && localStorage.getItem(LEGACY_USER)) {
      localStorage.setItem(USER_KEY, localStorage.getItem(LEGACY_USER)!);
      localStorage.removeItem(LEGACY_USER);
    }
  } catch {
    /* ignore */
  }
}

export function getStoredToken(): string | null {
  migrateLegacyAuthStorage();
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUserJson(): string | null {
  migrateLegacyAuthStorage();
  return localStorage.getItem(USER_KEY);
}

export function setStoredAuth(token: string, userJson: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, userJson);
}

export function clearStoredAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(LEGACY_TOKEN);
  localStorage.removeItem(LEGACY_USER);
}
