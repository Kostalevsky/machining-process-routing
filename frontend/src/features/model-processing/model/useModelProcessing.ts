import { useCallback, useMemo, useState } from "react";
import { simulateSuccessfulProcessing } from "../../../shared";
import { validateModelFile } from "../../../shared/lib/validation";
import type { Stage } from "../../../shared";

type UseModelProcessingOptions = {
  onComplete?: () => void;
};

export function useModelProcessing({ onComplete }: UseModelProcessingOptions = {}) {
  const [file, setFile] = useState<File | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [engine, setEngine] = useState<"type1" | "type2">("type1");
  const [llm, setLlm] = useState<"qwen-vl-max" | "qwen2.5-vl-72b" | "pixtral-12b">("qwen-vl-max");

  const onSelect = useCallback((nextFile: File | null) => {
    if (!nextFile) {
      setFile(null);
      setError(null);
      setJobId(null);
      setStage("idle");
      return;
    }

    const validationError = validateModelFile(nextFile);

    if (validationError) {
      setFile(null);
      setError(validationError);
      setJobId(null);
      setStage("idle");
      return;
    }

    setFile(nextFile);
    setError(null);
    setJobId(null);
  }, []);

  const canSubmit = useMemo(
    () => !!file && stage !== "uploading" && stage !== "rendering" && stage !== "postprocess",
    [file, stage]
  );

  const submit = async () => {
    const validationError = validateModelFile(file);

    if (validationError) {
      setError(validationError);
      return;
    }

    setStage("uploading");
    setError(null);

    try {
      await new Promise((resolve) => window.setTimeout(resolve, 350));
      setStage("rendering");
      await new Promise((resolve) => window.setTimeout(resolve, 500));
      setStage("postprocess");
      const data = await simulateSuccessfulProcessing(file);
      setJobId(data.jobId);
      setStage("done");
      onComplete?.();
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
    engine,
    llm,
    canSubmit,
    onSelect,
    submit,
    setEngine,
    setLlm,
  };
}
