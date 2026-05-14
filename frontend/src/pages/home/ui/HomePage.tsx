import { ModelUploadCard, useModelProcessing } from "../../../features/model-processing";
import { UserProfile } from "../../../shared/lib/mockAuth";
import { AppHeader } from "../../../widgets/app-header";
import { ResultsSection } from "../../../widgets/render-results";
import styles from "./HomePage.module.scss";

type HomePageProps = {
  currentPath: string;
  profile: UserProfile;
  onNavigate: (path: string) => void;
  onLogout: () => void;
};

export function HomePage({ currentPath, profile, onNavigate, onLogout }: HomePageProps) {
  const { file, stage, error, engine, canSubmit, onSelect, submit, setEngine } = useModelProcessing({
    onComplete: () => onNavigate("/route-preview"),
  });

  return (
    <div className={styles.page}>
      <AppHeader currentPath={currentPath} profile={profile} onNavigate={onNavigate} onLogout={onLogout} />

      <main className={styles.main}>
        <div className={styles.layout}>
          <section className={styles.uploadColumn}>
            <ModelUploadCard
              file={file}
              stage={stage}
              error={error}
              engine={engine}
              canSubmit={canSubmit}
              onSelect={onSelect}
              onSubmit={submit}
              onEngineChange={setEngine}
            />
          </section>

          <aside className={styles.resultsColumn}>
            <ResultsSection images={[]} jsons={[]} />
          </aside>
        </div>
      </main>
    </div>
  );
}
