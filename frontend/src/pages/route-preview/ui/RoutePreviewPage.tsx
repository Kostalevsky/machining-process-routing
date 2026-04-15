import { useMemo, useState } from "react";
import { createRouteSheetPdfBlob } from "../../../shared";
import { UserProfile } from "../../../shared/lib/mockAuth";
import type { MockProcessResult } from "../../../shared/types/routeSheet";
import { MockModelViewer } from "../../../shared/ui/model-viewer/MockModelViewer";
import { AppHeader } from "../../../widgets/app-header";
import styles from "./RoutePreviewPage.module.scss";

type RoutePreviewPageProps = {
  currentPath: string;
  profile: UserProfile;
  result: MockProcessResult;
  onNavigate: (path: string) => void;
  onLogout: () => void;
};

export function RoutePreviewPage({ currentPath, profile, result, onNavigate, onLogout }: RoutePreviewPageProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const jsonString = useMemo(() => JSON.stringify(result.routeSheet, null, 2), [result.routeSheet]);
  const pdfBlob = useMemo(() => createRouteSheetPdfBlob(result.routeSheet), [result.routeSheet]);
  const productName = useMemo(() => {
    const base = result.uploadedFileName.replace(/\.[^.]+$/, "").trim();
    return base || result.routeSheet["Name of operation"];
  }, [result.routeSheet, result.uploadedFileName]);

  function truncateFileName(name: string, maxLength = 34) {
    if (name.length <= maxLength) {
      return name;
    }

    const dotIndex = name.lastIndexOf(".");
    const extension = dotIndex > 0 ? name.slice(dotIndex) : "";
    const base = extension ? name.slice(0, dotIndex) : name;
    return `${base.slice(0, 16)}...${base.slice(-8)}${extension}`;
  }

  function downloadJson() {
    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${result.uploadedFileName.replace(/\.[^.]+$/, "") || "route-sheet"}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function downloadPdf() {
    const url = URL.createObjectURL(pdfBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${result.uploadedFileName.replace(/\.[^.]+$/, "") || "route-sheet"}.pdf`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function handleOpenModelModal() {
    window.setTimeout(() => {
      setIsModalOpen(true);
    }, 0);
  }

  return (
    <div className={styles.page}>
      <AppHeader currentPath={currentPath} profile={profile} onNavigate={onNavigate} onLogout={onLogout} />

      <main className={styles.main}>
        <section className={styles.toolbar}>
          <div className={styles.toolbarActions}>
            <button type="button" className={styles.secondaryButton} onClick={() => onNavigate("/")}>
              Загрузить другую модель
            </button>
            <button type="button" className={styles.secondaryButton} onClick={downloadPdf}>
              Скачать PDF
            </button>
            <button type="button" className={styles.primaryButton} onClick={downloadJson}>
              Скачать JSON
            </button>
          </div>
        </section>

        <div className={styles.layout}>
          <section className={styles.pdfSection}>
            <div className={styles.paper}>
              <div className={styles.paperToolbar}>
                <span className={styles.pdfBadge}>PDF</span>
                <span className={styles.paperFileName} title={result.routeSheet["File name"]}>
                  {truncateFileName(result.routeSheet["File name"])}
                </span>
              </div>
              <div className={styles.paperFrame}>
                <div className={styles.paperPages}>
                  <article className={`${styles.paperPage} ${styles.coverPage}`}>
                    <div className={styles.pageInner}>
                      <div className={styles.topStamp}>
                        <div className={styles.topStampLeft}>
                          <span>Лит.</span>
                          <span>Масса</span>
                          <span>Масштаб</span>
                        </div>
                        <div className={styles.topStampCenter}>
                          <div className={styles.topStampCode}>ОКБ "ЭЙТЕП"</div>
                          <div className={styles.topStampName} title={productName}>
                            {truncateFileName(productName, 28)}
                          </div>
                        </div>
                        <div className={styles.topStampRight}>
                          <span>14</span>
                          <span>1</span>
                        </div>
                      </div>

                      <div className={styles.pageCenter}>
                        <div className={styles.approvedText}>СОГЛАСОВАНО</div>
                        <div className={styles.documentTitle}>КОМПЛЕКТ ДОКУМЕНТОВ</div>
                        <div className={styles.documentSubtitle}>технологического процесса изготовления изделия</div>
                        <div className={styles.documentOperation}>{result.routeSheet["Name of operation"]}</div>
                      </div>

                      <div className={styles.bottomStamp}>
                        <div className={styles.bottomStampType}>
                          <span>ТЛ</span>
                          <span>Титульный лист</span>
                        </div>
                        <div className={styles.bottomStampMeta}>
                          <span title={result.routeSheet["File name"]}>{truncateFileName(result.routeSheet["File name"], 22)}</span>
                          <span>Лист 1</span>
                        </div>
                      </div>
                    </div>
                  </article>

                  <article className={`${styles.paperPage} ${styles.stepsPage}`}>
                    <div className={styles.pageInner}>
                      <div className={styles.pageHeader}>
                        <div>
                          <span className={styles.paperLabel}>Документ</span>
                        </div>
                        <div>
                          <strong title={productName}>{truncateFileName(productName, 28)}</strong>
                        </div>
                      </div>

                      <div className={styles.tableHead}>
                        <span>Шаг</span>
                        <span>Действие</span>
                        <span>Оборудование</span>
                        <span>ISO</span>
                      </div>

                      <div className={styles.steps}>
                        {result.routeSheet.Steps.map((step) => (
                          <div key={step["Step number"]} className={styles.stepRow}>
                            <span>{step["Step number"]}</span>
                            <span>{step.Action}</span>
                            <span title={step.Equipment.join(", ")}>{step.Equipment.join(", ")}</span>
                            <span title={step.ISO.join(", ")}>{step.ISO.join(", ")}</span>
                          </div>
                        ))}
                      </div>

                      <div className={styles.bottomStamp}>
                        <div className={styles.bottomStampType}>
                          <span>МЛ</span>
                          <span>Лист операций</span>
                        </div>
                        <div className={styles.bottomStampMeta}>
                          <span>{result.routeSheet.Steps.length} шагов</span>
                          <span>Лист 2</span>
                        </div>
                      </div>
                    </div>
                  </article>
                </div>
              </div>
            </div>
          </section>

          <aside className={styles.modelSection}>
            <MockModelViewer fileName={result.uploadedFileName} modelUrl={result.modelUrl} onExpand={handleOpenModelModal} />
          </aside>
        </div>
      </main>

      {isModalOpen ? (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" onClick={() => setIsModalOpen(false)}>
          <div className={styles.modal} onClick={(event) => event.stopPropagation()}>
            <div className={styles.modalHeader}>
              <div>
                <strong>3D-сцена модели</strong>
                <span title={result.uploadedFileName}>{truncateFileName(result.uploadedFileName, 52)}</span>
              </div>
              <button type="button" className={styles.closeButton} onClick={() => setIsModalOpen(false)}>
                Закрыть
              </button>
            </div>

            <MockModelViewer fileName={result.uploadedFileName} modelUrl={result.modelUrl} mode="modal" />
          </div>
        </div>
      ) : null}
    </div>
  );
}
