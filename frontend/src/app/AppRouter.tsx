import { useEffect, useState } from "react";
import { AuthPage } from "../pages/auth";
import { HomePage } from "../pages/home";
import { ProfilePage } from "../pages/profile";
import {
  getSessionState,
  loginWithMock,
  logoutMock,
  registerWithMock,
  updateMockProfile,
} from "../shared/lib/mockAuth";

export function AppRouter() {
  const [pathname, setPathname] = useState(window.location.pathname || "/");
  const [session, setSession] = useState(getSessionState);

  useEffect(() => {
    function handlePopState() {
      setPathname(window.location.pathname || "/");
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

  function navigate(path: string) {
    if (window.location.pathname !== path) {
      window.history.pushState({}, "", path);
    }
    setPathname(path);
  }

  function handleLogin(email: string) {
    loginWithMock(email);
    setSession(getSessionState());
    navigate("/");
  }

  function handleRegister(profile: Parameters<typeof registerWithMock>[0]) {
    registerWithMock(profile);
    setSession(getSessionState());
    navigate("/");
  }

  function handleLogout() {
    logoutMock();
    setSession(getSessionState());
    navigate("/login");
  }

  function handleProfileSave(profile: Parameters<typeof updateMockProfile>[0]) {
    updateMockProfile(profile);
    setSession(getSessionState());
  }

  const effectivePath = !session.isAuthenticated
    ? pathname === "/register"
      ? "/register"
      : "/login"
    : pathname === "/profile"
      ? "/profile"
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

  return (
    <HomePage
      currentPath={effectivePath}
      profile={session.profile}
      onNavigate={navigate}
      onLogout={handleLogout}
    />
  );
}
