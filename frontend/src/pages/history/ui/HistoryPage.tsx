import { useEffect, useState } from "react";
import { getApiErrorMessage } from "../../../shared/api/client";
import { getRun, listRuns } from "../../../shared/api/runsApi";
import type { RunResponse } from "../../../shared/api/types";
import { createProcessResultFromRun, setCurrentProcessResult } from "../../../shared";
import { UserProfile } from "../../../shared/lib/session";
import { AppHeader } from "../../../widgets/app-header";
import styles from "./HistoryPage.module.scss";

type HistoryPageProps = {
  currentPath: string;
  profile: UserProfile;
  onNavigate: (path: string, state?: Record<string, unknown>) => void;
  onLogout: () => void;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function truncate(value: string, max = 38) {
  if (value.length <= max) {
    return value;
  }

  const dot = value.lastIndexOf(".");
  const extension = dot > 0 ? value.slice(dot) : "";
  const base = extension ? value.slice(0, dot) : value;
  return `${base.slice(0, 16)}...${base.slice(-8)}${extension}`;
}

export function HistoryPage({ currentPath, profile, onNavigate, onLogout }: HistoryPageProps) {
  const [runs, setRuns] = useState<RunResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadRuns() {
      setIsLoading(true);
      setError(null);

      try {
        const data = await listRuns();

        if (!cancelled) {
          setRuns(data);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(getApiErrorMessage(loadError));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadRuns();

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleOpenRun(run: RunResponse) {
    if (run.status !== "completed") {
      setError("Открыть предпросмотр можно только для завершенной обработки");
      return;
    }

    try {
      const freshRun = await getRun(run.id);
      const result = await createProcessResultFromRun(freshRun);
      setCurrentProcessResult(result);
      onNavigate("/route-preview", { from: "history" });
    } catch (openError) {
      setError(getApiErrorMessage(openError));
    }
  }

  return (
    <div className={styles.page}>
      <AppHeader currentPath={currentPath} profile={profile} onNavigate={onNavigate} onLogout={onLogout} />

      <main className={styles.main}>
        <section className={styles.hero}>
          <h1>История просмотров</h1>
        </section>

        {error ? <div className={styles.error}>{error}</div> : null}

        {isLoading ? (
          <section className={styles.emptyState}>
            <div className={styles.emptyCard}>
              <h2>Загружаем историю</h2>
              <p>Получаем список обработок с сервера.</p>
            </div>
          </section>
        ) : runs.length > 0 ? (
          <section className={styles.grid}>
            {runs.map((run) => {
              const sourceArtifact = run.artifacts.find((artifact) => artifact.type === "source_obj");
              const fileName = sourceArtifact?.file_name || run.name || `run-${run.id}`;

              return (
                <article
                  key={run.id}
                  className={styles.card}
                  onClick={() => handleOpenRun(run)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      handleOpenRun(run);
                    }
                  }}
                >
                  <div className={styles.cardHeader}>
                    <div>
                      <h2>{run.name || `Обработка #${run.id}`}</h2>
                      <p title={fileName}>{truncate(fileName)}</p>
                    </div>
                    <span className={styles.status}>{run.status}</span>
                  </div>

                  <dl className={styles.meta}>
                    <div>
                      <dt>Дата обработки</dt>
                      <dd>{formatDate(run.updated_at)}</dd>
                    </div>
                    <div>
                      <dt>Артефактов</dt>
                      <dd>{run.artifacts.length}</dd>
                    </div>
                    <div>
                      <dt>Генераций</dt>
                      <dd>{run.generations.length}</dd>
                    </div>
                  </dl>
                </article>
              );
            })}
          </section>
        ) : (
          <section className={styles.emptyState}>
            <div className={styles.emptyCard}>
              <h2>Список пока пуст</h2>
              <p>История просмотров еще не содержит обработанных моделей.</p>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
