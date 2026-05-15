import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { API_BASE } from "../config/api";
import { clearStoredTokens, getStoredTokens, setStoredTokens } from "./tokenStorage";
import type { RefreshTokenRequest, TokenPairResponse } from "./types";

type RetriableRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean;
};

export const apiClient = axios.create({
  baseURL: API_BASE,
});

apiClient.interceptors.request.use((config) => {
  const tokens = getStoredTokens();

  if (tokens?.accessToken) {
    config.headers.Authorization = `Bearer ${tokens.accessToken}`;
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetriableRequestConfig | undefined;
    const tokens = getStoredTokens();

    if (
      error.response?.status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
      !tokens?.refreshToken ||
      originalRequest.url?.includes("/auth/refresh")
    ) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      const request: RefreshTokenRequest = { refresh_token: tokens.refreshToken };
      const response = await axios.post<TokenPairResponse>(
        `${API_BASE}/auth/refresh`,
        request,
      );

      setStoredTokens({
        accessToken: response.data.access_token,
        refreshToken: response.data.refresh_token,
      });

      originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`;
      return apiClient(originalRequest);
    } catch (refreshError) {
      clearStoredTokens();
      return Promise.reject(refreshError);
    }
  },
);

export function getApiErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (Array.isArray(detail) && detail[0]?.msg) {
      return String(detail[0].msg);
    }

    if (typeof detail === "string") {
      return detail;
    }

    if (error.response?.status === 401) {
      return "Не удалось авторизоваться. Проверьте учетные данные.";
    }

    if (error.response?.status) {
      return `Сервер вернул ошибку ${error.response.status}`;
    }

    if (error.message) {
      return error.message;
    }
  }

  return error instanceof Error ? error.message : "Произошла неизвестная ошибка";
}
