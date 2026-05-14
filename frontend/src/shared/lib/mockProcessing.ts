import type { MockProcessResult, RouteSheet } from "../types/routeSheet";
import {
  createGeneration,
  createRun,
  getRun,
  loadRouteSheetFromUrl,
  startProcessing,
  uploadSourceFile,
} from "../api/runsApi";
import type { ArtifactResponse, RunResponse, RunStatus } from "../api/types";
import { getApiErrorMessage } from "../api/client";

let currentResult: MockProcessResult | null = null;

function clearCurrentModelUrl() {
  if (currentResult?.modelUrl?.startsWith("blob:")) {
    URL.revokeObjectURL(currentResult.modelUrl);
  }
}

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function getArtifact(run: RunResponse, type: ArtifactResponse["type"]) {
  return run.artifacts.find((artifact) => artifact.type === type && artifact.download_url);
}

function getRouteSheetFromMeta(run: RunResponse) {
  const generatedArtifact = run.artifacts.find((artifact) => artifact.type === "generated_json");
  const metaJson = generatedArtifact?.meta_json;

  if (
    metaJson &&
    typeof metaJson === "object" &&
    "Steps" in metaJson &&
    Array.isArray((metaJson as Partial<RouteSheet>).Steps)
  ) {
    return metaJson as RouteSheet;
  }

  return null;
}

function isPendingStatus(status: RunStatus) {
  return status !== "completed" && status !== "failed";
}

async function waitForRunCompletion(runId: number) {
  let run = await getRun(runId);

  for (let attempt = 0; attempt < 90 && isPendingStatus(run.status); attempt += 1) {
    await wait(1500);
    run = await getRun(runId);
  }

  if (run.status === "failed") {
    throw new Error("Обработка модели завершилась с ошибкой");
  }

  if (run.status !== "completed") {
    throw new Error("Не удалось дождаться завершения обработки модели");
  }

  return run;
}

async function resolveRouteSheet(run: RunResponse) {
  const generatedArtifact = getArtifact(run, "generated_json");

  if (generatedArtifact?.download_url) {
    return loadRouteSheetFromUrl(generatedArtifact.download_url);
  }

  const metaRouteSheet = getRouteSheetFromMeta(run);

  if (metaRouteSheet) {
    return metaRouteSheet;
  }

  const generationRun = await createGeneration(run.id);
  const completedRun = await waitForRunCompletion(generationRun.id);
  const generatedAfterRetry = getArtifact(completedRun, "generated_json");

  if (generatedAfterRetry?.download_url) {
    return loadRouteSheetFromUrl(generatedAfterRetry.download_url);
  }

  const metaAfterRetry = getRouteSheetFromMeta(completedRun);

  if (metaAfterRetry) {
    return metaAfterRetry;
  }

  throw new Error("Сервер не вернул JSON маршрутного листа");
}

export async function createProcessResultFromRun(run: RunResponse) {
  const routeSheet = await resolveRouteSheet(run);
  const sourceArtifact = getArtifact(run, "source_obj");
  const uploadedFileName = sourceArtifact?.file_name || routeSheet["File name"] || run.name || `run-${run.id}`;

  return {
    jobId: String(run.id),
    uploadedFileName,
    modelUrl: sourceArtifact?.download_url || "",
    routeSheet: {
      ...routeSheet,
      "File name": routeSheet["File name"] || uploadedFileName,
    },
  };
}

export async function simulateSuccessfulProcessing(file: File) {
  clearCurrentModelUrl();

  try {
    const createdRun = await createRun({ name: file.name });
    await uploadSourceFile(createdRun.id, file);
    const processingRun = await startProcessing(createdRun.id);
    const completedRun = await waitForRunCompletion(processingRun.id);
    currentResult = await createProcessResultFromRun(completedRun);

    if (!currentResult.modelUrl) {
      currentResult.modelUrl = URL.createObjectURL(file);
    }
  } catch (error) {
    throw new Error(getApiErrorMessage(error));
  }

  return currentResult;
}

export function getCurrentMockResult() {
  return currentResult;
}

export function setCurrentMockResult(result: MockProcessResult) {
  clearCurrentModelUrl();
  currentResult = result;
}
