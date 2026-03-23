import type { Stage } from "../../../shared";
import styles from "./Pipeline.module.scss";

type PipelineProps = {
  stage: Stage;
};

export function Pipeline({ stage }: PipelineProps) {
  const steps = [
    { key: "idle", label: "Ожидание" },
    { key: "uploading", label: "Загрузка" },
    { key: "rendering", label: "Рендер" },
    { key: "postprocess", label: "Маршрут" },
    { key: "done", label: "Готово" },
  ] as const;

  const currentIndex = Math.max(steps.findIndex((step) => step.key === stage), 0);

  return (
    <div className={styles.pipeline}>
      <ol className={styles.list}>
        {steps.map((step, index) => {
          const completed = index <= currentIndex;
          return (
            <li key={step.key} className={styles.item}>
              <span className={[styles.dot, completed ? styles.dotActive : ""].join(" ")} />
              <span className={[styles.label, completed ? styles.labelActive : ""].join(" ")}>{step.label}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
