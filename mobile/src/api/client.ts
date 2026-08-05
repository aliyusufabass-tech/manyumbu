import axios from "axios";

export const api = axios.create({
  baseURL: process.env.EXPO_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1",
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});
