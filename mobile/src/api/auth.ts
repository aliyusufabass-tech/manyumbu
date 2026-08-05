import { api } from "./client";
import type { ApiResponse, AuthTokens, ManyumbuUser } from "../types/auth";

export type RegisterPayload = {
  full_name: string;
  username: string;
  phone_number: string;
  email: string;
  date_of_birth: string;
  password: string;
  confirm_password: string;
  accepted_terms: boolean;
  accepted_privacy: boolean;
};

export async function register(payload: RegisterPayload) {
  const { data } = await api.post<ApiResponse<{ user: ManyumbuUser }>>("/auth/register/", payload);
  return data;
}

export async function verifyEmail(phone_number: string, code: string) {
  const { data } = await api.post<ApiResponse<{ user: ManyumbuUser; tokens: AuthTokens }>>("/auth/verify-email/", { phone_number, code });
  return data;
}

export async function resendCode(phone_number: string) {
  const { data } = await api.post<ApiResponse<Record<string, never>>>("/auth/resend-code/", { phone_number });
  return data;
}

export async function login(identifier: string, password: string) {
  const { data } = await api.post<ApiResponse<{ user: ManyumbuUser; tokens: AuthTokens }>>("/auth/login/", { identifier, password });
  return data;
}

export async function forgotPassword(identifier: string) {
  const { data } = await api.post<ApiResponse<Record<string, never>>>("/auth/forgot-password/", { identifier });
  return data;
}
