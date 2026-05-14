import styles from "./JsonComparePanel.module.scss";
import { useJsonCompare } from "../model/useJsonCompare";

export function JsonComparePanel() {
  const {
    serverFiles,
    selectedUrl,
    uploadedFileName,
    result,
    state,
    error,
    selectedName,
    fileInputRef,
    setSelectedUrl,
    onUpload,
    compare,
  } = useJsonCompare();

  return (
    <div className={styles.panel}>
      <div className={styles.section}>
        <div className={styles.label}>Выберите один из ранее сгенерированных JSON-файлов</div>
        {serverFiles.length === 0 ? (
          <p className={styles.hint}>Нет доступных файлов или не удалось загрузить список.</p>
        ) : (
          <select value={selectedUrl} onChange={(event) => setSelectedUrl(event.target.value)} className={styles.select}>
            {serverFiles.map((file) => (
              <option key={`${file.job_id}-${file.filename}`} value={file.url}>
                {file.job_id} / {file.filename}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <div className={styles.label}>Загрузите JSON-файл</div>
          <button type="button" onClick={() => fileInputRef.current?.click()} className={styles.linkButton}>
            Выбрать файл
          </button>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".json,application/json"
          className={styles.hiddenInput}
          onChange={(event) => onUpload(event.target.files?.[0] ?? null)}
        />

        <div className={styles.fileState}>
          {uploadedFileName ? (
            <span>
              Загружен файл: <span className={styles.value}>{uploadedFileName}</span>
            </span>
          ) : (
            "Файл не выбран"
          )}
        </div>
      </div>

      <div className={styles.actionsRow}>
        <button type="button" onClick={compare} disabled={state === "loading"} className={styles.compareButton}>
          {state === "loading" ? "Сравнение..." : "Сравнить"}
        </button>

        <div className={styles.meta}>
          {selectedName ? (
            <div>
              Выбран из backend: <span className={styles.value}>{selectedName}</span>
            </div>
          ) : null}
          {uploadedFileName ? (
            <div>
              Загружен локально: <span className={styles.value}>{uploadedFileName}</span>
            </div>
          ) : null}
        </div>
      </div>

      {result ? (
        <div className={styles.resultCard}>
          <div className={styles.label}>Интегральная оценка</div>
          <div className={styles.score}>{result.distance.toFixed(6)}</div>
        </div>
      ) : null}

      {error ? <div className={styles.error}>{error}</div> : null}
    </div>
  );
}
