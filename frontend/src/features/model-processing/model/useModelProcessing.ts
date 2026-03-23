import { useCallback, useMemo, useState } from "react";
import { API_BASE, toApiUrl } from "../../../shared";
import type { ProcessResponse, Stage } from "../../../shared";

export function useModelProcessing() {
  const [file, setFile] = useState<File | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [images, setImages] = useState<string[]>([]);
  const [jsons, setJsons] = useState<string[]>([]);
  const [engine, setEngine] = useState<"type1" | "type2">("type1");
  const [llm, setLlm] = useState<"qwen-vl-max" | "qwen2.5-vl-72b" | "pixtral-12b">("qwen-vl-max");

  const onSelect = useCallback((nextFile: File | null) => {
    setFile(nextFile);
    setError(null);
    setImages([]);
    setJsons([]);
    setJobId(null);
  }, []);

  const canSubmit = useMemo(
    () => !!file && stage !== "uploading" && stage !== "rendering" && stage !== "postprocess",
    [file, stage]
  );

  const submit = async () => {
    if (!file) {
      return;
    }

    setStage("uploading");
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("engine", engine);
      formData.append("llm", llm);

      const response = await fetch(`${API_BASE}/process`, { method: "POST", body: formData });
      if (!response.ok) {
        const msg = await response.text();
        throw new Error(msg || "Request failed");
      }

      setStage("postprocess");
      const data = (await response.json()) as ProcessResponse;
      setJobId(data.job_id);
      setImages(data.images.map(toApiUrl));
      setJsons(data.json_files.map(toApiUrl));
      setStage("done");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      setStage("error");
    }
  };

  return {
    file,
    stage,
    error,
    jobId,
    images,
    jsons,
    engine,
    llm,
    canSubmit,
    onSelect,
    submit,
    setEngine,
    setLlm,
  };
}
