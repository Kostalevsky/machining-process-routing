import { createRouteSheetPdfBlob } from "./routeSheetPdf";
import { setCurrentMockResult } from "./mockProcessing";
import type { MockProcessResult, RouteSheet } from "../types/routeSheet";

export type HistoryItem = {
  id: string;
  title: string;
  fileName: string;
  processedAt: string;
  status: "Готово" | "В архиве" | "Проверено";
  routeSheet: RouteSheet;
  modelFileName: string;
  modelContent: string;
};

const historyItems: HistoryItem[] = [
  {
    id: "hist-1",
    title: "Кольцо опорное",
    fileName: "00000002_1ffb81a41_trimesh_001.obj",
    processedAt: "15 апреля 2026, 14:32",
    status: "Готово",
    modelFileName: "00000002_1ffb81a41_trimesh_001.obj",
    modelContent: "# mock obj\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n",
    routeSheet: {
      "File name": "00000002_1ffb81a41_trimesh_001.obj",
      "Name of operation": "Nuts Manufacturing",
      Steps: [
        { "Step number": 1, Action: "Analyze the drawing", Equipment: ["Computer"], ISO: ["ISO 2768"] },
        { "Step number": 2, Action: "Turning", Equipment: ["Universal lathe"], ISO: ["ISO 230-1", "ISO 7944"] },
        { "Step number": 3, Action: "Facing", Equipment: ["CNC lathe"], ISO: ["ISO 230-1", "ISO 7944"] },
        { "Step number": 4, Action: "Boring", Equipment: ["Boring machine"], ISO: ["ISO 230-1", "ISO 10794"] },
        { "Step number": 5, Action: "Threading", Equipment: ["CNC lathe"], ISO: ["ISO 230-1", "ISO 7944"] },
      ],
    },
  },
  {
    id: "hist-2",
    title: "Втулка переходная",
    fileName: "bushing_transition_rev_c.glb",
    processedAt: "14 апреля 2026, 18:05",
    status: "Проверено",
    modelFileName: "bushing_transition_rev_c.glb",
    modelContent: "{\"asset\":{\"version\":\"2.0\"}}",
    routeSheet: {
      "File name": "bushing_transition_rev_c.glb",
      "Name of operation": "Bushing Milling",
      Steps: [
        { "Step number": 1, Action: "Drawing review", Equipment: ["CAD workstation"], ISO: ["ISO 128"] },
        { "Step number": 2, Action: "Outer turning", Equipment: ["Turning center"], ISO: ["ISO 230-1"] },
        { "Step number": 3, Action: "Slot milling", Equipment: ["4-axis milling machine"], ISO: ["ISO 10791"] },
        { "Step number": 4, Action: "Surface finishing", Equipment: ["Finishing station"], ISO: ["ISO 1302"] },
      ],
    },
  },
  {
    id: "hist-3",
    title: "Фланец крепежный",
    fileName: "flange_mount_final_mesh.obj",
    processedAt: "12 апреля 2026, 10:47",
    status: "В архиве",
    modelFileName: "flange_mount_final_mesh.obj",
    modelContent: "# mock obj\nv 0 0 0\nv 0 2 0\nv 2 0 0\nf 1 2 3\n",
    routeSheet: {
      "File name": "flange_mount_final_mesh.obj",
      "Name of operation": "Flange Assembly Prep",
      Steps: [
        { "Step number": 1, Action: "Technical inspection", Equipment: ["Inspection desk"], ISO: ["ISO 9001"] },
        { "Step number": 2, Action: "CNC drilling", Equipment: ["Drilling center"], ISO: ["ISO 10793"] },
        { "Step number": 3, Action: "Chamfering", Equipment: ["Chamfer tool"], ISO: ["ISO 13715"] },
        { "Step number": 4, Action: "Final control", Equipment: ["CMM"], ISO: ["ISO 10360"] },
      ],
    },
  },
];

export function getMockHistoryItems() {
  return historyItems;
}

function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}

export function downloadHistoryPdf(item: HistoryItem) {
  downloadBlob(createRouteSheetPdfBlob(item.routeSheet), `${item.fileName.replace(/\.[^.]+$/, "")}.pdf`);
}

export function downloadHistoryJson(item: HistoryItem) {
  downloadBlob(new Blob([JSON.stringify(item.routeSheet, null, 2)], { type: "application/json" }), `${item.fileName.replace(/\.[^.]+$/, "")}.json`);
}

export function downloadHistoryModel(item: HistoryItem) {
  downloadBlob(new Blob([item.modelContent], { type: "text/plain" }), item.modelFileName);
}

export function openHistoryPreview(item: HistoryItem) {
  const modelBlob = new Blob([item.modelContent], { type: "text/plain" });
  const result: MockProcessResult = {
    jobId: item.id,
    uploadedFileName: item.fileName,
    modelUrl: URL.createObjectURL(modelBlob),
    routeSheet: item.routeSheet,
  };

  setCurrentMockResult(result);
}
