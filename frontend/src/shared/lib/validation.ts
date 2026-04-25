const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const phonePattern = /^\+?[0-9\s()-]{7,20}$/;
const allowedModelExtensions = [".obj", ".stl", ".fbx", ".ply", ".glb", ".gltf"];
const maxModelFileSize = 100 * 1024 * 1024;

export function validateRequired(value: string, label: string) {
  return value.trim() ? "" : `${label} обязательно для заполнения`;
}

export function validateLength(value: string, label: string, min: number, max: number) {
  const trimmed = value.trim();

  if (trimmed.length < min) {
    return `${label} должно содержать не менее ${min} символов`;
  }

  if (trimmed.length > max) {
    return `${label} должно содержать не более ${max} символов`;
  }

  return "";
}

export function validateEmail(value: string) {
  const requiredError = validateRequired(value, "Email");

  if (requiredError) {
    return requiredError;
  }

  return emailPattern.test(value.trim()) ? "" : "Введите корректный email";
}

export function validatePassword(value: string) {
  const requiredError = validateRequired(value, "Пароль");

  if (requiredError) {
    return requiredError;
  }

  return value.trim().length >= 8 ? "" : "Пароль должен содержать не менее 8 символов";
}

export function validatePhone(value: string) {
  const requiredError = validateRequired(value, "Телефон");

  if (requiredError) {
    return requiredError;
  }

  return phonePattern.test(value.trim()) ? "" : "Введите корректный номер телефона";
}

export function validateModelFile(file: File | null) {
  if (!file) {
    return "Выберите 3D-модель для обработки";
  }

  const lowerName = file.name.toLowerCase();
  const hasAllowedExtension = allowedModelExtensions.some((extension) => lowerName.endsWith(extension));

  if (!hasAllowedExtension) {
    return `Поддерживаются только форматы ${allowedModelExtensions.join(", ")}`;
  }

  if (file.size <= 0) {
    return "Файл пустой, выберите другую модель";
  }

  if (file.size > maxModelFileSize) {
    return "Размер файла не должен превышать 100 MB";
  }

  return "";
}
