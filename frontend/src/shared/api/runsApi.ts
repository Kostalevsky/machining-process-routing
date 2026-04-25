import axios from "axios";
import { apiClient } from "./client";
import type {
  ArtifactResponse,
  CollageGenerateRequest,
  CollageSelectRequest,
  GenerationCreateRequest,
  RunCreateRequest,
  RunResponse,
} from "./types";
import type { RouteSheet } from "../types/routeSheet";

export async function healthcheck() {
  const response = await apiClient.get<Record<string, string>>("/health");
  return response.data;
}

export async function listRuns() {
  const response = await apiClient.get<RunResponse[]>("/runs");
  return response.data;
}

export async function createRun(request: RunCreateRequest) {
  const response = await apiClient.post<RunResponse>("/runs", request);
  return response.data;
}

export async function getRun(runId: number) {
  const response = await apiClient.get<RunResponse>(`/runs/${runId}`);
  return response.data;
}

export async function getSelectedCollage(runId: number) {
  const response = await apiClient.get<ArtifactResponse>(`/runs/${runId}/selected-collage`);
  return response.data;
}

export async function uploadSourceFile(runId: number, file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post<RunResponse>(`/runs/${runId}/source-file`, formData);

  return response.data;
}

export async function uploadRenders(runId: number, files: File[]) {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  const response = await apiClient.post<RunResponse>(`/runs/${runId}/renders`, formData);

  return response.data;
}

export async function generateCollages(runId: number, request: CollageGenerateRequest = {}) {
  const response = await apiClient.post<RunResponse>(`/runs/${runId}/collages/generate`, request);
  return response.data;
}

export async function selectCollage(runId: number, request: CollageSelectRequest) {
  const response = await apiClient.post<RunResponse>(`/runs/${runId}/collages/select`, request);
  return response.data;
}

export async function startProcessing(runId: number) {
  const response = await apiClient.post<RunResponse>(`/runs/${runId}/process`);
  return response.data;
}

export async function createGeneration(runId: number, request: GenerationCreateRequest = {}) {
  const response = await apiClient.post<RunResponse>(`/runs/${runId}/generations`, request);
  return response.data;
}

export async function loadRouteSheetFromUrl(downloadUrl: string) {
  const response = await axios.get<RouteSheet>(downloadUrl);
  return response.data;
}
