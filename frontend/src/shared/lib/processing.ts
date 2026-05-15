import type { ProcessResult, RouteSheet } from "../types/routeSheet";
import {
    createGeneration,
    createRun,
    generateCollages,
    loadRouteSheetFromUrl,
    startProcessing,
    uploadSourceFile,
} from "../api/runsApi";
import type { ArtifactResponse, RunResponse } from "../api/types";
import { getApiErrorMessage } from "../api/client";

let currentResult: ProcessResult | null = null;

function clearCurrentModelUrl() {
    if (currentResult?.modelUrl?.startsWith("blob:")) {
        URL.revokeObjectURL(currentResult.modelUrl);
    }
}

function getArtifact(run: RunResponse, type: ArtifactResponse["type"]) {
    return run.artifacts.find(
        (artifact) => artifact.type === type && artifact.download_url,
    );
}

function getRouteSheetFromMeta(run: RunResponse) {
    const generatedArtifact = run.artifacts.find(
        (artifact) => artifact.type === "generated_json",
    );
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

function localizeRouteSheet(routeSheet: RouteSheet): RouteSheet {
    return {
        ...routeSheet,
        "Name of operation":
            routeSheet["Name of operation RU"] ||
            routeSheet["Name of operation"],
        Steps: routeSheet.Steps.map((step) => ({
            ...step,
            Stage: step["Stage RU"] || step.Stage,
            Action: step["Action RU"] || step.Action,
            Equipment: step["Equipment RU"]?.length
                ? step["Equipment RU"]
                : step.Equipment,
        })),
    };
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

    const generationRun = await createGeneration(run.id, {
        provider: "qwen",
        model_name: "qwen-vl-max",
        prompt_version: "v1",
    });
    const generatedAfterRetry = getArtifact(generationRun, "generated_json");

    if (generatedAfterRetry?.download_url) {
        return loadRouteSheetFromUrl(generatedAfterRetry.download_url);
    }

    const metaAfterRetry = getRouteSheetFromMeta(generationRun);

    if (metaAfterRetry) {
        return metaAfterRetry;
    }

    throw new Error("Сервер не вернул JSON маршрутного листа");
}

export async function createProcessResultFromRun(run: RunResponse) {
    const routeSheet = localizeRouteSheet(await resolveRouteSheet(run));
    const sourceArtifact = getArtifact(run, "source_obj");
    const uploadedFileName =
        sourceArtifact?.file_name ||
        routeSheet["File name"] ||
        run.name ||
        `run-${run.id}`;

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

export async function processModel(file: File) {
    clearCurrentModelUrl();

    try {
        const createdRun = await createRun({ name: file.name });
        await uploadSourceFile(createdRun.id, file);
        const processingRun = await startProcessing(createdRun.id);
        const collageRun = await generateCollages(processingRun.id, {
            counts: [3, 4, 6],
        });
        const generationRun = await createGeneration(collageRun.id, {
            provider: "qwen",
            model_name: "qwen-vl-max",
            prompt_version: "v1",
        });
        currentResult = await createProcessResultFromRun(generationRun);

        if (!currentResult.modelUrl) {
            currentResult.modelUrl = URL.createObjectURL(file);
        }
    } catch (error) {
        throw new Error(getApiErrorMessage(error));
    }

    return currentResult;
}

export function getCurrentProcessResult() {
    return currentResult;
}

export function setCurrentProcessResult(result: ProcessResult) {
    clearCurrentModelUrl();
    currentResult = result;
}
