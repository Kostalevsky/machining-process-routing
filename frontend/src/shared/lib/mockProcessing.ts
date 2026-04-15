import type { MockProcessResult, RouteSheet } from "../types/routeSheet";

const mockRouteSheet: RouteSheet = {
  "File name": "3D_model.jpg",
  "Name of operation": "Nuts Manufacturing",
  Steps: [
    {
      "Step number": 1,
      Action: "Analyze the drawing",
      Equipment: ["Computer"],
      ISO: ["ISO 2768"],
    },
    {
      "Step number": 2,
      Action: "Turning",
      Equipment: ["Universal lathe"],
      ISO: ["ISO 230-1", "ISO 7944"],
    },
    {
      "Step number": 3,
      Action: "Facing",
      Equipment: ["CNC lathe"],
      ISO: ["ISO 230-1", "ISO 7944"],
    },
    {
      "Step number": 4,
      Action: "Boring",
      Equipment: ["Boring machine"],
      ISO: ["ISO 230-1", "ISO 10794"],
    },
    {
      "Step number": 5,
      Action: "Threading",
      Equipment: ["CNC lathe"],
      ISO: ["ISO 230-1", "ISO 7944"],
    },
    {
      "Step number": 6,
      Action: "Drilling",
      Equipment: ["Drilling machine"],
      ISO: ["ISO 230-1", "ISO 10793"],
    },
    {
      "Step number": 7,
      Action: "Reaming",
      Equipment: ["Reaming machine"],
      ISO: ["ISO 230-1"],
    },
    {
      "Step number": 8,
      Action: "Milling",
      Equipment: ["CNC milling machine"],
      ISO: ["ISO 230-1", "ISO 10791"],
    },
    {
      "Step number": 9,
      Action: "Deburring",
      Equipment: ["Deburring tool"],
      ISO: ["ISO 15740"],
    },
    {
      "Step number": 10,
      Action: "Heat treatment",
      Equipment: ["Heat treatment furnace"],
      ISO: ["ISO 17226", "ISO 15614-1"],
    },
    {
      "Step number": 11,
      Action: "Grinding",
      Equipment: ["Grinding machine"],
      ISO: ["ISO 230-1", "ISO 10580"],
    },
    {
      "Step number": 12,
      Action: "Polishing",
      Equipment: ["Polishing machine"],
      ISO: ["ISO 15740", "ISO 4892"],
    },
    {
      "Step number": 13,
      Action: "Quality inspection",
      Equipment: ["Coordinate measuring machine (CMM)"],
      ISO: ["ISO 10360", "ISO 15530"],
    },
    {
      "Step number": 14,
      Action: "Surface coating",
      Equipment: ["Coating machine"],
      ISO: ["ISO 12100"],
    },
    {
      "Step number": 15,
      Action: "Packaging",
      Equipment: ["Packaging machine"],
      ISO: ["ISO 12100"],
    },
  ],
};

let currentResult: MockProcessResult | null = null;

function clearCurrentModelUrl() {
  if (currentResult?.modelUrl?.startsWith("blob:")) {
    URL.revokeObjectURL(currentResult.modelUrl);
  }
}

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export async function simulateSuccessfulProcessing(file: File) {
  await wait(450);
  await wait(700);
  await wait(450);

  clearCurrentModelUrl();

  currentResult = {
    jobId: `mock-${Date.now()}`,
    uploadedFileName: file.name,
    modelUrl: URL.createObjectURL(file),
    routeSheet: {
      ...mockRouteSheet,
      "File name": file.name,
    },
  };

  return currentResult;
}

export function getCurrentMockResult() {
  return currentResult;
}

export function setCurrentMockResult(result: MockProcessResult) {
  clearCurrentModelUrl();
  currentResult = result;
}
