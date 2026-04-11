export type UserProfile = {
  fullName: string;
  email: string;
  phone: string;
  company: string;
  role: string;
  about: string;
};

const STORAGE_KEY = "cad2tech.mock-auth";

const defaultProfile: UserProfile = {
  fullName: "Анна Смирнова",
  email: "anna.smirnova@cad2tech.ru",
  phone: "+7 (999) 123-45-67",
  company: "CAD2Tech",
  role: "Инженер-проектировщик",
  about: "Курирую загрузку моделей, проверяю результаты обработки и синхронизирую данные между командами.",
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

  if (!raw) {
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

export function getSessionState() {
  return readState();
}

export function loginWithMock(email: string) {
  const current = readState();

  writeState({
    isAuthenticated: true,
    profile: {
      ...current.profile,
      email,
    },
  });
}

export function registerWithMock(profile: Pick<UserProfile, "fullName" | "email" | "company" | "role">) {
  writeState({
    isAuthenticated: true,
    profile: {
      ...defaultProfile,
      ...profile,
      about: `Профиль ${profile.fullName} создан через временную мок-авторизацию.`,
    },
  });
}

export function updateMockProfile(profile: UserProfile) {
  writeState({
    isAuthenticated: true,
    profile,
  });
}

export function logoutMock() {
  const current = readState();

  writeState({
    isAuthenticated: false,
    profile: current.profile,
  });
}
