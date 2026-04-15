import { UserProfile } from "../../../shared/lib/mockAuth";
import {
  downloadHistoryJson,
  downloadHistoryModel,
  downloadHistoryPdf,
  getMockHistoryItems,
  openHistoryPreview,
} from "../../../shared/lib/mockHistory";
import { AppHeader } from "../../../widgets/app-header";
import styles from "./HistoryPage.module.scss";

type HistoryPageProps = {
  currentPath: string;
  profile: UserProfile;
  onNavigate: (path: string) => void;
  onLogout: () => void;
};

function truncate(value: string, max = 32) {
  if (value.length <= max) {
    return value;
  }

  const dot = value.lastIndexOf(".");
  const ext = dot > 0 ? value.slice(dot) : "";
  const base = ext ? value.slice(0, dot) : value;
  return `${base.slice(0, 14)}...${base.slice(-8)}${ext}`;
}

export function HistoryPage({ currentPath, profile, onNavigate, onLogout }: HistoryPageProps) {
  const items = getMockHistoryItems();

  function handleOpenPreview(item: (typeof items)[number]) {
    openHistoryPreview(item);
    onNavigate("/route-preview");
  }

  return (
    <div className={styles.page}>
      <AppHeader currentPath={currentPath} profile={profile} onNavigate={onNavigate} onLogout={onLogout} />

      <main className={styles.main}>
        <section className={styles.hero}>
          <h1>История просмотров</h1>
        </section>

        <section className={styles.grid}>
          {items.map((item) => (
            <article
              key={item.id}
              className={styles.card}
              onClick={() => handleOpenPreview(item)}
              role="button"
              tabIndex={0}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  handleOpenPreview(item);
                }
              }}
            >
              <div className={styles.cardHeader}>
                <div>
                  <h2>{item.title}</h2>
                  <p title={item.fileName}>{truncate(item.fileName, 38)}</p>
                </div>
              </div>

              <dl className={styles.meta}>
                <div>
                  <dt>Дата обработки</dt>
                  <dd>{item.processedAt}</dd>
                </div>
                <div>
                  <dt>Операция</dt>
                  <dd>{item.routeSheet["Name of operation"]}</dd>
                </div>
                <div>
                  <dt>Шагов</dt>
                  <dd>{item.routeSheet.Steps.length}</dd>
                </div>
              </dl>

              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.actionButton}
                  onClick={(event) => {
                    event.stopPropagation();
                    downloadHistoryPdf(item);
                  }}
                >
                  Скачать PDF
                </button>
                <button
                  type="button"
                  className={styles.actionButton}
                  onClick={(event) => {
                    event.stopPropagation();
                    downloadHistoryJson(item);
                  }}
                >
                  Скачать JSON
                </button>
                <button
                  type="button"
                  className={styles.actionButton}
                  onClick={(event) => {
                    event.stopPropagation();
                    downloadHistoryModel(item);
                  }}
                >
                  Скачать 3D
                </button>
              </div>
            </article>
          ))}
        </section>
      </main>
    </div>
  );
}
