const extractNumbers = (value: unknown, acc: number[]): void => {
  if (typeof value === "number" && Number.isFinite(value)) {
    acc.push(value);
    return;
  }

  if (Array.isArray(value)) {
    value.forEach((item) => extractNumbers(item, acc));
    return;
  }

  if (value && typeof value === "object") {
    Object.values(value as Record<string, unknown>).forEach((item) => {
      if (typeof item !== "string") {
        extractNumbers(item, acc);
      }
    });
  }
};

export const cosineDistance = (a: unknown, b: unknown) => {
  const va: number[] = [];
  const vb: number[] = [];

  extractNumbers(a, va);
  extractNumbers(b, vb);

  if (va.length === 0 || vb.length === 0) {
    throw new Error("Не удалось найти числовые данные в одном из файлов");
  }

  const maxLength = Math.max(va.length, vb.length);
  const v1 = [...va];
  const v2 = [...vb];

  while (v1.length < maxLength) v1.push(0);
  while (v2.length < maxLength) v2.push(0);

  const dot = v1.reduce((sum, n, index) => sum + n * v2[index], 0);
  const norm1 = Math.sqrt(v1.reduce((sum, n) => sum + n * n, 0));
  const norm2 = Math.sqrt(v2.reduce((sum, n) => sum + n * n, 0));

  if (norm1 === 0 || norm2 === 0) {
    throw new Error("Норма одного из векторов равна 0");
  }

  return dot / (norm1 * norm2);
};

export const normalizeJsonName = (name: string) => {
  const lower = (name || "").toLowerCase();
  const withoutExt = lower.endsWith(".json") ? lower.slice(0, -5) : lower;
  return withoutExt.replace(/_bench$/, "");
};
