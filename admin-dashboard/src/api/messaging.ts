import axios from "axios";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/v1", headers: { "Content-Type": "application/json" } });
export type MessageReport = { id: number; kind: "message" | "conversation"; message_id?: string; conversation_id?: string; reporter: { username: string; full_name: string }; reason: string; details: string; status: string; context_snapshot: Record<string, unknown>; created_at: string };
export type ReportResponse = { success: boolean; message: string; data: { results: MessageReport[]; count: number; next_offset: number | null } };
export async function fetchMessageReports(token: string, kind: "messages" | "conversations", status?: string) { const { data } = await api.get<ReportResponse>("/admin/message-reports/", { params: { kind, status }, headers: { Authorization: `Bearer ${token}` } }); return data; }
export async function moderateMessageReport(token: string, kind: "messages" | "conversations", id: number, action: "pending" | "review" | "resolve" | "reject", reason: string) { const { data } = await api.post(`/admin/message-reports/${kind}/${id}/${action}/`, { reason }, { headers: { Authorization: `Bearer ${token}` } }); return data; }
