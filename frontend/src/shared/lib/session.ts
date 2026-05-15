import { getApiErrorMessage } from "../api/client";
import { getCurrentUser, login, logout, register, updateCurrentUser } from "../api/authApi";
import { getStoredTokens } from "../api/tokenStorage";
import type { UserResponse } from "../api/types";

export type UserProfile = {
  fullName: string;
  email: string;
  phone: string;
  company: string;
  role: string;
  about: string;
};

const STORAGE_KEY = "cad2tech.session";

const defaultProfile: UserProfile = {
  fullName: "",
  email: "",
  phone: "",
  company: "",
  role: "",
  about: "",
};

type SessionState = {
  isAuthenticated: boolean;
  profile: UserProfile;
};

function readState(): SessionState {
  if (typeof window === "undefined") {
    return { isAuthenticated: false, profile: defaultProfile };
  }

  const raw = window.localStorage.getItem(STORAGE_KEY);
  const tokens = getStoredTokens();

  if (!raw || !tokens) {
    return { isAuthenticated: false, profile: defaultProfile };
  }

  try {
    const parsed = JSON.parse(raw) as Partial<SessionState>;

    return {
      isAuthenticated: Boolean(parsed.isAuthenticated),
      profile: {
        ...defaultProfile,
        ...parsed.profile,
      },
    };
  } catch {
    return { isAuthenticated: false, profile: defaultProfile };
  }
}

function writeState(state: SessionState) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function mergeUserProfile(current: UserProfile, user: UserResponse): UserProfile {
  return {
    ...current,
    email: user.email,
    fullName: user.full_name || current.fullName,
    company: user.company || current.company,
    role: user.role || current.role,
    about: user.description || current.about,
  };
}

function toUserUpdateRequest(profile: UserProfile) {
  return {
    full_name: profile.fullName,
    company: profile.company,
    role: profile.role,
    description: profile.about,
  };
}

export function getSessionState() {
  return readState();
}

export async function restoreSession() {
  if (!getStoredTokens()) {
    return {
      success: false as const,
    };
  }

  try {
    const user = await getCurrentUser();
    const current = readState();

    writeState({
      isAuthenticated: true,
      profile: mergeUserProfile(current.profile, user),
    });

    return {
      success: true as const,
    };
  } catch (error) {
    logout();
    return {
      success: false as const,
      error: getApiErrorMessage(error),
    };
  }
}

export async function loginWithApi(email: string, password: string) {
  try {
    const user = await login({ email: email.trim(), password });
    const current = readState();

    writeState({
      isAuthenticated: true,
      profile: mergeUserProfile(current.profile, user),
    });

    return {
      success: true as const,
    };
  } catch (error) {
    return {
      success: false as const,
      error: getApiErrorMessage(error),
    };
  }
}

export async function registerWithApi(profile: Pick<UserProfile, "fullName" | "email" | "company" | "role"> & { password: string }) {
  try {
    const user = await register({ email: profile.email.trim(), password: profile.password });
    const nextProfile = mergeUserProfile(
      {
        ...defaultProfile,
        fullName: profile.fullName,
        company: profile.company,
        role: profile.role,
      },
      user,
    );

    writeState({
      isAuthenticated: true,
      profile: nextProfile,
    });

    await updateCurrentUser(toUserUpdateRequest(nextProfile));

    return {
      success: true as const,
    };
  } catch (error) {
    return {
      success: false as const,
      error: getApiErrorMessage(error),
    };
  }
}

export async function updateProfile(profile: UserProfile) {
  writeState({
    isAuthenticated: true,
    profile,
  });

  try {
    const user = await updateCurrentUser(toUserUpdateRequest(profile));
    writeState({
      isAuthenticated: true,
      profile: mergeUserProfile(profile, user),
    });
  } catch (error) {
    return {
      success: false as const,
      error: getApiErrorMessage(error),
    };
  }

  return {
    success: true as const,
  };
}

export function logoutSession() {
  const current = readState();

  logout();

  writeState({
    isAuthenticated: false,
    profile: current.profile,
  });
}
