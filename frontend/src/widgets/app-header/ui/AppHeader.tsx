import { useEffect, useRef, useState } from "react";
import { UserProfile } from "../../../shared/lib/mockAuth";
import styles from "./AppHeader.module.scss";

type AppHeaderProps = {
  currentPath: string;
  profile: UserProfile;
  onNavigate: (path: string) => void;
  onLogout: () => void;
};

export function AppHeader({ currentPath, profile, onNavigate, onLogout }: AppHeaderProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsMenuOpen(false);
      }
    }

    window.addEventListener("mousedown", handleClickOutside);
    window.addEventListener("keydown", handleEscape);

    return () => {
      window.removeEventListener("mousedown", handleClickOutside);
      window.removeEventListener("keydown", handleEscape);
    };
  }, []);

  function handleNavigate(path: string) {
    onNavigate(path);
    setIsMenuOpen(false);
  }

  function handleLogoutClick() {
    setIsMenuOpen(false);
    onLogout();
  }

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <button type="button" className={styles.brandButton} onClick={() => handleNavigate("/")}>
          CAD2Tech
        </button>

        <div className={styles.actions} ref={menuRef}>
          <div className={styles.userInfo}>
            <strong>{profile.fullName}</strong>
            <span>{profile.role}</span>
          </div>
          <button
            type="button"
            className={styles.profileButton}
            onClick={() => setIsMenuOpen((current) => !current)}
            aria-label="Меню пользователя"
            aria-expanded={isMenuOpen}
          >
            <span className={styles.profileLabel}>{profile.fullName.slice(0, 1)}</span>
          </button>

          {isMenuOpen ? (
            <div className={styles.menu}>
              <button
                type="button"
                className={currentPath === "/" ? styles.menuItemActive : styles.menuItem}
                onClick={() => handleNavigate("/")}
              >
                Главная
              </button>
              <button
                type="button"
                className={currentPath === "/profile" ? styles.menuItemActive : styles.menuItem}
                onClick={() => handleNavigate("/profile")}
              >
                Личный кабинет
              </button>
              <button type="button" className={styles.menuItem} onClick={handleLogoutClick}>
                Выйти
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
