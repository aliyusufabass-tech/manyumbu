import axios from "axios";

export type AdminPost = { id: string; author: { username: string; full_name: string }; caption: string; post_type: string; status: string; media: Array<{ media_type: string; url: string }>; like_count: number; comment_count: number; created_at: string; };
export type AdminPostsResponse = { success: boolean; message: string; data: { results: AdminPost[]; count: number; next_offset: number | null } };

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/v1", headers: { "Content-Type": "application/json" } });

export async function fetchAdminPosts(token: string, filters: { q?: string; status?: string; author?: string; media_type?: string }) {
  const { data } = await api.get<AdminPostsResponse>("/admin/posts/", { params: filters, headers: { Authorization: `Bearer ${token}` } });
  return data;
}

export async function moderatePost(token: string, postId: string, action: "remove" | "restore", reason: string) {
  const { data } = await api.post(`/admin/posts/${postId}/${action}/`, { reason }, { headers: { Authorization: `Bearer ${token}` } });
  return data;
}
