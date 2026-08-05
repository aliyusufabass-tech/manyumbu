import axios from "axios";

export type AdminStory = { id: string; author: { username: string }; caption: string; story_type: string; status: string; expires_at: string | null; view_count: number };
export type AdminReel = { id: string; author: { username: string }; caption: string; status: string; processing_status: string; view_count: number; like_count: number; comment_count: number };
const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/v1", headers: { "Content-Type": "application/json" } });
export async function fetchAdminStories(token: string) { const { data } = await api.get<{ success: boolean; data: { results: AdminStory[]; count: number } }>("/admin/stories/", { headers: { Authorization: `Bearer ${token}` } }); return data; }
export async function fetchAdminReels(token: string, status = "") { const { data } = await api.get<{ success: boolean; data: { results: AdminReel[]; count: number } }>("/admin/reels/", { params: { status }, headers: { Authorization: `Bearer ${token}` } }); return data; }
export async function moderateStoryReel(token: string, kind: "stories" | "reels", id: string, action: "remove" | "restore" | "retry-processing", reason: string) { const { data } = await api.post(`/admin/${kind}/${id}/${action}/`, { reason }, { headers: { Authorization: `Bearer ${token}` } }); return data; }
