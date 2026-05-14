export type ProcessResponse = {
  status: "ok";
  job_id: string;
  images: string[];
  json_files: string[];
};

export type Stage = "idle" | "uploading" | "rendering" | "postprocess" | "done" | "error";
