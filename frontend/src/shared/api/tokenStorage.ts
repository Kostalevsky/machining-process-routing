const STORAGE_KEY = "cad2tech.auth-tokens";
const ACCESS_TOKEN_COOKIE = "cad2tech_access_token";
const REFRESH_TOKEN_COOKIE = "cad2tech_refresh_token";
const COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

export type AuthTokens = {
  accessToken: string;
  refreshToken: string;
};

function getCookie(name: string) {
  if (typeof document === "undefined") {
    return null;
  }

  const value = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`))
    ?.split("=")[1];

  return value ? decodeURIComponent(value) : null;
}

function setCookie(name: string, value: string) {
  if (typeof document === "undefined") {
    return;
  }

  document.cookie = `${name}=${encodeURIComponent(value)}; Max-Age=${COOKIE_MAX_AGE_SECONDS}; Path=/; SameSite=Lax`;
}

function clearCookie(name: string) {
  if (typeof document === "undefined") {
    return;
  }

  document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Lax`;
}

function readTokensFromLocalStorage() {
  const raw = window.localStorage.getItem(STORAGE_KEY);

  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as Partial<AuthTokens>;

    if (!parsed.accessToken || !parsed.refreshToken) {
      return null;
    }

    return {
      accessToken: parsed.accessToken,
      refreshToken: parsed.refreshToken,
    };
  } catch {
    return null;
  }
}

function readTokensFromCookies() {
  const accessToken = getCookie(ACCESS_TOKEN_COOKIE);
  const refreshToken = getCookie(REFRESH_TOKEN_COOKIE);

  if (!accessToken || !refreshToken) {
    return null;
  }

  return {
    accessToken,
    refreshToken,
  };
}

export function getStoredTokens(): AuthTokens | null {
  if (typeof window === "undefined") {
    return null;
  }

  const localTokens = readTokensFromLocalStorage();

  if (localTokens) {
    return localTokens;
  }

  const cookieTokens = readTokensFromCookies();

  if (cookieTokens) {
    setStoredTokens(cookieTokens);
  }

  return cookieTokens;
}

export function setStoredTokens(tokens: AuthTokens) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
  setCookie(ACCESS_TOKEN_COOKIE, tokens.accessToken);
  setCookie(REFRESH_TOKEN_COOKIE, tokens.refreshToken);
}

export function clearStoredTokens() {
  window.localStorage.removeItem(STORAGE_KEY);
  clearCookie(ACCESS_TOKEN_COOKIE);
  clearCookie(REFRESH_TOKEN_COOKIE);
}
