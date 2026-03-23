import { JsonComparePanel } from "../../../features/json-compare";
import styles from "./TestPage.module.scss";

export function TestPage() {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.inner}>
          <div className={styles.title}>Тест сравнения JSON</div>
          <a className={styles.backLink} href="/">
            ← Назад
          </a>
        </div>
      </header>

      <main className={styles.main}>
        <JsonComparePanel />
      </main>
    </div>
  );
}
