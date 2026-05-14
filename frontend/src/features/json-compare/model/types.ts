export type OutputJson = {
  job_id: string;
  filename: string;
  url: string;
  modified: number;
};

export type CompareState = "idle" | "loading" | "done" | "error";
