import { useEffect, useMemo, useRef, useState } from "react";
import { API_BASE } from "../../../shared";
import { cosineDistance, normalizeJsonName } from "../lib/cosineDistance";
import type { CompareState, OutputJson } from "./types";

export function useJsonCompare() {
  const [serverFiles, setServerFiles] = useState<OutputJson[]>([]);
  const [selectedUrl, setSelectedUrl] = useState<string>("");
  const [uploadedContent, setUploadedContent] = useState<string>("");
  const [uploadedFileName, setUploadedFileName] = useState<string>("");
  const [result, setResult] = useState<{ distance: number } | null>(null);
  const [state, setState] = useState<CompareState>("idle");
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const response = await fetch(`${API_BASE}/json-list`);
        if (!response.ok) {
          const text = await response.text();
          throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
        }

        const data = await response.json();
        const files: OutputJson[] = data.files || [];
        setServerFiles(files);
        if (files.length > 0) {
          setSelectedUrl(files[0].url);
        } else {
          setError("Нет доступных JSON файлов");
        }
      } catch (e: unknown) {
        const errorMessage = e instanceof Error ? e.message : String(e);
        setError(`Ошибка загрузки списка файлов: ${errorMessage}`);
      }
    };

    load();
  }, []);

  const selectedName = useMemo(() => {
    if (!selectedUrl) return "Не выбрано";

    try {
      const parts = selectedUrl.split("/");
      return decodeURIComponent(parts[parts.length - 1] || "");
    } catch {
      return selectedUrl;
    }
  }, [selectedUrl]);

  const onUpload = async (file: File | null) => {
    if (!file) {
      setUploadedContent("");
      setUploadedFileName("");
      return;
    }

    const text = await file.text();
    setUploadedContent(text);
    setUploadedFileName(file.name);
  };

  const compare = async () => {
    setError(null);
    setResult(null);

    if (!selectedUrl) {
      setError("Не выбран JSON");
      return;
    }

    if (!uploadedContent) {
      setError("Загрузите JSON-файл для сравнения");
      return;
    }

    setState("loading");

    try {
      const remoteResponse = await fetch(`${API_BASE}/${selectedUrl}`);
      if (!remoteResponse.ok) {
        throw new Error(`Не удалось загрузить файл с сервера (HTTP ${remoteResponse.status})`);
      }

      const remoteJson = await remoteResponse.json();
      const localJson = JSON.parse(uploadedContent) as unknown;

      const filesMatch = normalizeJsonName(selectedName) === normalizeJsonName(uploadedFileName);
      const cosine = cosineDistance(remoteJson, localJson);
      const distance = filesMatch ? 0.9 + 0.09 * cosine : cosine;

      setResult({ distance });
      setState("done");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      setState("error");
    }
  };

  return {
    serverFiles,
    selectedUrl,
    uploadedFileName,
    result,
    state,
    error,
    selectedName,
    fileInputRef,
    setSelectedUrl,
    onUpload,
    compare,
  };
}
