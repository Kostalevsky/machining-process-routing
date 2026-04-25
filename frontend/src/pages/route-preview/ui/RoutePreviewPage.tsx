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
  showBackButton?: boolean;
  onNavigate: (path: string, state?: Record<string, unknown>) => void;
  onLogout: () => void;
};

export function RoutePreviewPage({
  currentPath,
  profile,
  result,
  showBackButton = false,
  onNavigate,
  onLogout,
}: RoutePreviewPageProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isInfoModalOpen, setIsInfoModalOpen] = useState(false);
  const [dimensionErrors, setDimensionErrors] = useState({
    height: "",
    width: "",
    depth: "",
  });
  const [dimensions, setDimensions] = useState({
    height: "",
    width: "",
    depth: "",
  });
  const [dimensionDraft, setDimensionDraft] = useState({
    height: "",
    width: "",
    depth: "",
  });

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

  function handleOpenInfoModal() {
    setDimensionDraft(dimensions);
    setDimensionErrors({
      height: "",
      width: "",
      depth: "",
    });
    setIsInfoModalOpen(true);
  }

  function validateDimensionField(value: string) {
    const normalized = value.trim().replace(",", ".");

    if (!normalized) {
      return "Поле обязательно";
    }

    if (!/^\d+([.]\d+)?$/.test(normalized)) {
      return "Введите число";
    }

    if (Number(normalized) <= 0) {
      return "Значение должно быть больше 0";
    }

    return "";
  }

  function handleAddDimensions() {
    const nextErrors = {
      height: validateDimensionField(dimensionDraft.height),
      width: validateDimensionField(dimensionDraft.width),
      depth: validateDimensionField(dimensionDraft.depth),
    };

    setDimensionErrors(nextErrors);

    if (Object.values(nextErrors).some(Boolean)) {
      return;
    }

    setDimensions({
      height: dimensionDraft.height.trim().replace(",", "."),
      width: dimensionDraft.width.trim().replace(",", "."),
      depth: dimensionDraft.depth.trim().replace(",", "."),
    });
    setIsInfoModalOpen(false);
  }

  const hasDimensions = Object.values(dimensions).some((value) => value.trim().length > 0);

  return (
    <div className={styles.page}>
      <AppHeader currentPath={currentPath} profile={profile} onNavigate={onNavigate} onLogout={onLogout} />

      <main className={styles.main}>
        <section className={styles.toolbar}>
          <div className={styles.toolbarActions}>
            {showBackButton ? (
              <button type="button" className={styles.secondaryButton} onClick={() => onNavigate("/history")}>
                Назад
              </button>
            ) : null}
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
                          <span>Масштаб</span>
                        </div>
                        <div className={styles.topStampCenter}>
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
                        <div className={styles.documentTitle}>Маршрутный лист</div>
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
        <div
          className={styles.modalOverlay}
          role="dialog"
          aria-modal="true"
          onClick={() => {
            setIsModalOpen(false);
            setIsInfoModalOpen(false);
          }}
        >
          <div className={styles.modal} onClick={(event) => event.stopPropagation()}>
            <div className={styles.modalHeader}>
              <div className={styles.modalHeaderInfo}>
                <strong>3D-сцена модели</strong>
                <span title={result.uploadedFileName}>{truncateFileName(result.uploadedFileName, 52)}</span>
              </div>
              <button type="button" className={styles.closeButton} onClick={() => setIsModalOpen(false)}>
                Закрыть
              </button>
            </div>

            <MockModelViewer
              fileName={result.uploadedFileName}
              modelUrl={result.modelUrl}
              mode="modal"
              modalOverlay={
                <>
                  <div className={styles.sceneInfoPanel}>
                    <button
                      type="button"
                      className={styles.sceneInfoButton}
                      onClick={(event) => {
                        event.stopPropagation();
                        handleOpenInfoModal();
                      }}
                    >
                      Добавить доп. информацию
                      </button>

                    {hasDimensions ? (
                      <div className={styles.dimensionSummary}>
                        <span>Высота: {dimensions.height || "—"} мм</span>
                        <span>Ширина: {dimensions.width || "—"} мм</span>
                        <span>Глубина: {dimensions.depth || "—"} мм</span>
                      </div>
                    ) : null}
                  </div>

                  {isInfoModalOpen ? (
                    <div
                      className={styles.infoModal}
                      role="dialog"
                      aria-label="Дополнительная информация о детали"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <div className={styles.infoModalHeader}>
                        <strong>Параметры детали</strong>
                        <button
                          type="button"
                          className={styles.infoModalClose}
                          onClick={() => setIsInfoModalOpen(false)}
                          aria-label="Закрыть"
                        >
                          ×
                        </button>
                      </div>

                      <div className={styles.infoFields}>
                        <label className={styles.infoField}>
                          <span>Высота, мм</span>
                          <input
                            type="text"
                            value={dimensionDraft.height}
                            className={dimensionErrors.height ? styles.inputError : ""}
                            onChange={(event) =>
                              {
                                setDimensionDraft((current) => ({
                                  ...current,
                                  height: event.target.value,
                                }));
                                setDimensionErrors((current) => ({
                                  ...current,
                                  height: "",
                                }));
                              }
                            }
                          />
                          {dimensionErrors.height ? (
                            <span className={styles.fieldError}>{dimensionErrors.height}</span>
                          ) : null}
                        </label>

                        <label className={styles.infoField}>
                          <span>Ширина, мм</span>
                          <input
                            type="text"
                            value={dimensionDraft.width}
                            className={dimensionErrors.width ? styles.inputError : ""}
                            onChange={(event) =>
                              {
                                setDimensionDraft((current) => ({
                                  ...current,
                                  width: event.target.value,
                                }));
                                setDimensionErrors((current) => ({
                                  ...current,
                                  width: "",
                                }));
                              }
                            }
                          />
                          {dimensionErrors.width ? (
                            <span className={styles.fieldError}>{dimensionErrors.width}</span>
                          ) : null}
                        </label>

                        <label className={styles.infoField}>
                          <span>Глубина, мм</span>
                          <input
                            type="text"
                            value={dimensionDraft.depth}
                            className={dimensionErrors.depth ? styles.inputError : ""}
                            onChange={(event) =>
                              {
                                setDimensionDraft((current) => ({
                                  ...current,
                                  depth: event.target.value,
                                }));
                                setDimensionErrors((current) => ({
                                  ...current,
                                  depth: "",
                                }));
                              }
                            }
                          />
                          {dimensionErrors.depth ? (
                            <span className={styles.fieldError}>{dimensionErrors.depth}</span>
                          ) : null}
                        </label>
                      </div>

                      <button type="button" className={styles.primaryButton} onClick={handleAddDimensions}>
                        Добавить
                      </button>
                    </div>
                  ) : null}
                </>
              }
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
