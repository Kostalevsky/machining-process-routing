import { apiClient } from "./client";
import { clearStoredTokens, setStoredTokens } from "./tokenStorage";
import type { LoginRequest, RegisterRequest, TokenPairResponse, UserResponse, UserUpdateRequest } from "./types";

function storeTokenPair(data: TokenPairResponse) {
  setStoredTokens({
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
  });

  return data.user;
}

export async function login(request: LoginRequest) {
  const response = await apiClient.post<TokenPairResponse>("/auth/login", request);
  return storeTokenPair(response.data);
}

export async function register(request: RegisterRequest) {
  const response = await apiClient.post<TokenPairResponse>("/auth/register", request);
  return storeTokenPair(response.data);
}

export async function getCurrentUser() {
  const response = await apiClient.get<UserResponse>("/users/me");
  return response.data;
}

export async function updateCurrentUser(request: UserUpdateRequest) {
  const response = await apiClient.patch<UserResponse>("/users/me", request);
  return response.data;
}

export function logout() {
  clearStoredTokens();
}
