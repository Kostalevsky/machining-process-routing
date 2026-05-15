import { useCallback, useRef } from "react";
import type { DragEvent } from "react";
import { Spinner } from "../../../shared";
import type { Stage } from "../../../shared";
import { Pipeline } from "./Pipeline";
import styles from "./ModelUploadCard.module.scss";

type ModelUploadCardProps = {
  file: File | null;
  stage: Stage;
  error: string | null;
  engine: "type1" | "type2";
  canSubmit: boolean;
  onSelect: (file: File | null) => void;
  onSubmit: () => void;
  onEngineChange: (engine: "type1" | "type2") => void;
};

const formatFileSize = (size: number) => {
  const mb = size / (1024 * 1024);
  return `${mb.toFixed(1)} MB`;
};

export function ModelUploadCard({
  file,
  stage,
  error,
  engine,
  canSubmit,
  onSelect,
  onSubmit,
  onEngineChange,
}: ModelUploadCardProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const onDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault();
      const nextFile = event.dataTransfer.files?.[0];
      if (nextFile) {
        onSelect(nextFile);
      }
    },
    [onSelect]
  );

  const isLoading = stage === "uploading" || stage === "rendering" || stage === "postprocess";
  const actionLabel = isLoading ? <Spinner /> : "Обработать";

  return (
    <div onDragOver={(event) => event.preventDefault()} onDrop={onDrop} className={styles.card}>
      <div className={styles.body}>
        <h2 className={styles.title}>Загрузка 3D-модели</h2>
        <p className={styles.subtitle}>Поддерживаются форматы .obj, .stl, .fbx, .ply, .glb, .gltf</p>

        <input
          ref={inputRef}
          type="file"
          accept=".obj,.stl,.fbx,.ply,.glb,.gltf"
          className={styles.input}
          onChange={(event) => onSelect(event.target.files?.[0] ?? null)}
        />

        <button type="button" onClick={() => inputRef.current?.click()} className={styles.dropzone}>
          {file ? (
            <div className={styles.fileCard}>
              <div className={styles.filePreview} />
              <div className={styles.fileName}>{file.name}</div>
              <div className={styles.fileSize}>{formatFileSize(file.size)}</div>
            </div>
          ) : (
            <div className={styles.dropzoneContent}>
              <div className={styles.dropzoneIcon}>↑</div>
              <div className={styles.dropzoneText}>Перетащи сюда файл</div>
              <div className={styles.dropzoneHint}>или кликни, чтобы выбрать</div>
            </div>
          )}
        </button>

        <div className={styles.footer}>
          <Pipeline stage={stage} />

          <button type="button" disabled={!canSubmit} onClick={onSubmit} className={styles.submitButton}>
            {actionLabel}
          </button>
        </div>

        {error ? <div className={styles.error}>{error}</div> : null}
      </div>
    </div>
  );
}
