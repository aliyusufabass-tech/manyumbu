import axios from "axios";

export type AdminLoginResult = {
  success: boolean;
  message: string;
  data: {
    user: {
      phone_number: string;
      email: string;
      username: string;
      full_name: string;
      is_active: boolean;
      is_email_verified: boolean;
    };
    tokens: { access: string; refresh: string };
  };
};

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/v1",
  headers: { "Content-Type": "application/json" },
});

export async function adminLogin(identifier: string, password: string) {
  const { data } = await api.post<AdminLoginResult>("/auth/login/", { identifier, password });
  return data;
}
