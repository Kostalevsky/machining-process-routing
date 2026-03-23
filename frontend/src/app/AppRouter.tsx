import { HomePage } from "../pages/home";
import { TestPage } from "../pages/test";

export function AppRouter() {
  const pathname = window.location.pathname;
  return pathname === "/test" ? <TestPage /> : <HomePage />;
}
