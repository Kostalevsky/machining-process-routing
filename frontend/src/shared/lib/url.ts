import { API_BASE } from "../config/api";

export const toApiUrl = (url: string) => (url.startsWith("http") ? url : `${API_BASE}/${url}`);
