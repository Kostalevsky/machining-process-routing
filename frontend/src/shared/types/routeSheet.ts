export type RouteSheetStep = {
  "Step number": number;
  Action: string;
  Equipment: string[];
  ISO: string[];
};

export type RouteSheet = {
  "File name": string;
  "Name of operation": string;
  Steps: RouteSheetStep[];
};

export type MockProcessResult = {
  jobId: string;
  uploadedFileName: string;
  modelUrl: string;
  routeSheet: RouteSheet;
};
