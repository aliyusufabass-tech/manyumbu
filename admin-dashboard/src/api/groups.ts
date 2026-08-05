import axios from "axios";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/v1", headers: { "Content-Type": "application/json" } });
export type AdminGroup = { id: string; name: string; description: string; owner: { username: string; full_name: string }; privacy: string; member_count: number; status: string; created_at: string; updated_at: string };
export type GroupReport = { id: number; group_id: string; group_name?: string; message_id?: string; reporter: { username: string; full_name: string }; reason: string; status: string; context_snapshot: Record<string, unknown> };
export type GroupResponse<T> = { success: boolean; message: string; data: { results: T[]; count: number; next_offset: number | null } };
export async function fetchAdminGroups(token: string, params: { q?: string; status?: string; privacy?: string } = {}) { const { data } = await api.get<GroupResponse<AdminGroup>>("/admin/groups/", { params, headers: { Authorization: `Bearer ${token}` } }); return data; }
export async function moderateGroup(token: string, id: string, action: "suspend" | "restore" | "remove" | "warn-owner", reason: string) { const { data } = await api.post(`/admin/groups/${id}/${action}/`, { reason, message: reason }, { headers: { Authorization: `Bearer ${token}` } }); return data; }
export async function fetchGroupReports(token: string, kind: "group-reports" | "group-message-reports", status?: string) { const { data } = await api.get<GroupResponse<GroupReport>>("/admin/groups/", { params: { kind, status }, headers: { Authorization: `Bearer ${token}` } }); return data; }
export async function sendAnnouncement(token: string, title: string, body: string, target = "all") { const { data } = await api.post("/admin/announcements/announcement/", { title, body, target }, { headers: { Authorization: `Bearer ${token}` } }); return data; }
