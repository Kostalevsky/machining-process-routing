export type RouteSheetStep = {
  "Step number": number;
  Stage?: string;
  "Stage RU"?: string;
  Action: string;
  "Action RU"?: string;
  Equipment: string[];
  "Equipment RU"?: string[];
  ISO: string[];
};

export type RouteSheet = {
  "File name": string;
  "Name of operation": string;
  "Name of operation RU"?: string;
  Steps: RouteSheetStep[];
};

export type ProcessResult = {
  jobId: string;
  uploadedFileName: string;
  modelUrl: string;
  routeSheet: RouteSheet;
};
