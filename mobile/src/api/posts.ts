import { api } from "./client";
import { getTokenItem } from "../store/tokenStorage";
import type { ApiResponse } from "../types/auth";
import type { Comment, FeedPage, Post } from "../types/post";
import type { Paginated } from "../types/profile";

async function authHeader() {
  const token = await getTokenItem("manyumbu_access");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export type CreatePostPayload = { caption: string; audience: string; comments_enabled: boolean; location_name?: string; hashtags?: string[]; mentions?: string[]; tagged_users?: string[]; selected_users?: string[]; status?: "draft" | "published"; media?: Array<{ uri: string; name: string; type: string }> };

export async function createPost(payload: CreatePostPayload, onProgress?: (progress: number) => void) {
  const form = new FormData();
  Object.entries(payload).forEach(([key, value]) => {
    if (key === "media" || value === undefined) return;
    form.append(key, Array.isArray(value) ? JSON.stringify(value) : String(value));
  });
  payload.media?.forEach((file) => form.append("media", file as unknown as Blob));
  const { data } = await api.post<ApiResponse<{ post: Post }>>("/posts/", form, { headers: { ...(await authHeader()), "Content-Type": "multipart/form-data" }, onUploadProgress: (event) => event.total && onProgress?.(Math.round((event.loaded / event.total) * 100)) });
  return data;
}

export async function getFeed(cursor?: string | null) { const { data } = await api.get<ApiResponse<FeedPage>>("/feed/", { params: { cursor }, headers: await authHeader() }); return data; }
export async function getPost(id: string) { const { data } = await api.get<ApiResponse<{ post: Post }>>(`/posts/${id}/`, { headers: await authHeader() }); return data; }
export async function updatePost(id: string, payload: Partial<CreatePostPayload>) { const { data } = await api.patch<ApiResponse<{ post: Post }>>(`/posts/${id}/`, payload, { headers: await authHeader() }); return data; }
export async function deletePost(id: string) { const { data } = await api.delete<ApiResponse<Record<string, never>>>(`/posts/${id}/`, { headers: await authHeader() }); return data; }
export async function archivePost(id: string) { const { data } = await api.post<ApiResponse<{ post: Post }>>(`/posts/${id}/archive/`, {}, { headers: await authHeader() }); return data; }
export async function restorePost(id: string) { const { data } = await api.post<ApiResponse<{ post: Post }>>(`/posts/${id}/restore/`, {}, { headers: await authHeader() }); return data; }
export async function likePost(id: string) { const { data } = await api.post<ApiResponse<{ liked: boolean; like_count: number }>>(`/posts/${id}/like/`, {}, { headers: await authHeader() }); return data; }
export async function unlikePost(id: string) { const { data } = await api.delete<ApiResponse<{ liked: boolean; like_count: number }>>(`/posts/${id}/like/`, { headers: await authHeader() }); return data; }
export async function savePost(id: string) { const { data } = await api.post<ApiResponse<{ saved: boolean }>>(`/posts/${id}/save/`, {}, { headers: await authHeader() }); return data; }
export async function unsavePost(id: string) { const { data } = await api.delete<ApiResponse<{ saved: boolean }>>(`/posts/${id}/save/`, { headers: await authHeader() }); return data; }
export async function getComments(id: string) { const { data } = await api.get<ApiResponse<Paginated<Comment>>>(`/posts/${id}/comments/`, { headers: await authHeader() }); return data; }
export async function addComment(id: string, text: string, parent_id?: string) { const { data } = await api.post<ApiResponse<{ comment: Comment }>>(`/posts/${id}/comments/`, { text, parent_id }, { headers: await authHeader() }); return data; }
export async function getUserPosts(username: string, offset = 0) { const { data } = await api.get<ApiResponse<Paginated<Post>>>(`/users/${username}/posts/`, { params: { offset }, headers: await authHeader() }); return data; }
export async function getSavedPosts(offset = 0) { const { data } = await api.get<ApiResponse<Paginated<Post>>>("/me/saved-posts/", { params: { offset }, headers: await authHeader() }); return data; }
export async function getArchivedPosts(offset = 0) { const { data } = await api.get<ApiResponse<Paginated<Post>>>("/me/archived-posts/", { params: { offset }, headers: await authHeader() }); return data; }
export async function getHashtagPosts(hashtag: string, offset = 0) { const { data } = await api.get<ApiResponse<Paginated<Post>>>(`/hashtags/${hashtag}/posts/`, { params: { offset }, headers: await authHeader() }); return data; }
export async function reportPost(id: string, reason: string, details = "") { const { data } = await api.post<ApiResponse<{ report_id: number }>>(`/posts/${id}/report/`, { reason, details }, { headers: await authHeader() }); return data; }
export async function hidePost(id: string) { const { data } = await api.post<ApiResponse<Record<string, never>>>(`/posts/${id}/hide/`, {}, { headers: await authHeader() }); return data; }
