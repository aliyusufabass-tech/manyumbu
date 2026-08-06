import axios from "axios";

import { API_URL } from "../config/env";

export const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.message;
    if (typeof message === "string") {
      return Promise.reject(new Error(message));
    }
    if (Array.isArray(message)) {
      return Promise.reject(new Error(message.join(" ")));
    }
    return Promise.reject(error);
  },
);
