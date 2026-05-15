import { useEffect, useState } from "react";
import { AuthPage } from "../pages/auth";
import { HistoryPage } from "../pages/history";
import { HomePage } from "../pages/home";
import { ProfilePage } from "../pages/profile";
import { RoutePreviewPage } from "../pages/route-preview";
import { getCurrentProcessResult } from "../shared";
import {
  getSessionState,
  loginWithApi,
  logoutSession,
  registerWithApi,
  restoreSession,
  updateProfile,
} from "../shared/lib/session";

export function AppRouter() {
  const [pathname, setPathname] = useState(window.location.pathname || "/");
  const [navigationState, setNavigationState] = useState<Record<string, unknown> | null>(
    (window.history.state as Record<string, unknown> | null) ?? null
  );
  const [session, setSession] = useState(getSessionState);
  const previewResult = pathname === "/route-preview" ? getCurrentProcessResult() : null;

  useEffect(() => {
    if (!session.isAuthenticated) {
      restoreSession().then((result) => {
        if (result.success) {
          setSession(getSessionState());
          window.history.replaceState({}, "", "/");
          setPathname("/");
          setNavigationState(null);
        }
      });
    }
  }, []);

  useEffect(() => {
    function handlePopState() {
      setPathname(window.location.pathname || "/");
      setNavigationState((window.history.state as Record<string, unknown> | null) ?? null);
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (!session.isAuthenticated && pathname !== "/login" && pathname !== "/register") {
      window.history.replaceState({}, "", "/login");
      setPathname("/login");
    }

    if (session.isAuthenticated && (pathname === "/login" || pathname === "/register")) {
      window.history.replaceState({}, "", "/");
      setPathname("/");
    }
  }, [pathname, session.isAuthenticated]);

  useEffect(() => {
    if (session.isAuthenticated && pathname === "/route-preview" && !previewResult) {
      window.history.replaceState({}, "", "/");
      setPathname("/");
    }
  }, [pathname, previewResult, session.isAuthenticated]);

  function navigate(path: string, state?: Record<string, unknown>) {
    if (window.location.pathname !== path) {
      window.history.pushState(state ?? {}, "", path);
    } else if (state) {
      window.history.replaceState(state, "", path);
    }
    setPathname(path);
    setNavigationState(state ?? null);
  }

  async function handleLogin(email: string, password: string) {
    const result = await loginWithApi(email, password);

    if (!result.success) {
      return result.error;
    }

    setSession(getSessionState());
    navigate("/");
    return null;
  }

  async function handleRegister(profile: Parameters<typeof registerWithApi>[0]) {
    const result = await registerWithApi(profile);

    if (!result.success) {
      return result.error;
    }

    setSession(getSessionState());
    navigate("/");
    return null;
  }

  function handleLogout() {
    logoutSession();
    setSession(getSessionState());
    navigate("/login");
  }

  function handleProfileSave(profile: Parameters<typeof updateProfile>[0]) {
    updateProfile(profile);
    setSession(getSessionState());
  }

  const effectivePath = !session.isAuthenticated
    ? pathname === "/register"
      ? "/register"
      : "/login"
    : pathname === "/profile"
      ? "/profile"
      : pathname === "/history"
        ? "/history"
      : pathname === "/route-preview"
        ? "/route-preview"
      : "/";

  if (!session.isAuthenticated) {
    return (
      <AuthPage
        mode={effectivePath === "/register" ? "register" : "login"}
        onLogin={handleLogin}
        onRegister={handleRegister}
        onNavigate={navigate}
      />
    );
  }

  if (effectivePath === "/profile") {
    return (
      <ProfilePage
        currentPath={effectivePath}
        profile={session.profile}
        onNavigate={navigate}
        onLogout={handleLogout}
        onSave={handleProfileSave}
      />
    );
  }

  if (effectivePath === "/history") {
    return (
      <HistoryPage
        currentPath={effectivePath}
        profile={session.profile}
        onNavigate={navigate}
        onLogout={handleLogout}
      />
    );
  }

  if (effectivePath === "/route-preview") {
    if (!previewResult) {
      return null;
    }

    return (
      <RoutePreviewPage
        currentPath={effectivePath}
        profile={session.profile}
        result={previewResult}
        showBackButton={navigationState?.from === "history"}
        onNavigate={navigate}
        onLogout={handleLogout}
      />
    );
  }

  return (
    <HomePage
      currentPath={effectivePath}
      profile={session.profile}
      onNavigate={navigate}
      onLogout={handleLogout}
    />
  );
}
