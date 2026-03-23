import styles from "./AppHeader.module.scss";

export function AppHeader() {
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <div className={styles.brand}>CAD2Tech</div>
        <button type="button" className={styles.profileButton} aria-label="Профиль пользователя">
          <span className={styles.profileIcon} />
        </button>
      </div>
    </header>
  );
}
