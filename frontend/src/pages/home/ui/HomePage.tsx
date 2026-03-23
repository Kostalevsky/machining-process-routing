import { ModelUploadCard, useModelProcessing } from "../../../features/model-processing";
import { AppHeader } from "../../../widgets/app-header";
import { ResultsSection } from "../../../widgets/render-results";
import styles from "./HomePage.module.scss";

export function HomePage() {
  const { file, stage, error, images, jsons, engine, canSubmit, onSelect, submit, setEngine } = useModelProcessing();

  return (
    <div className={styles.page}>
      <AppHeader />

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
            <ResultsSection images={images} jsons={jsons} />
          </aside>
        </div>
      </main>
    </div>
  );
}
