import axios from "axios";

import { API_URL } from "../config/env";

export const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});
