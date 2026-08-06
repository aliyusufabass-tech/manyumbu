import { api } from "./client";
import { getTokenItem } from "../store/tokenStorage";
import type { ApiResponse } from "../types/auth";
import type { CompactUser, Paginated, PrivacySettings, Profile } from "../types/profile";

async function authHeader() {
  const token = await getTokenItem("manyumbu_access");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function getMyProfile() {
  const { data } = await api.get<ApiResponse<{ profile: Profile }>>("/profiles/me/", { headers: await authHeader() });
  return data;
}

export async function getProfile(username: string) {
  const { data } = await api.get<ApiResponse<{ profile: Profile }>>(`/profiles/${username}/`, { headers: await authHeader() });
  return data;
}

export async function updateProfile(payload: Partial<Profile>) {
  const { data } = await api.patch<ApiResponse<{ profile: Profile }>>("/profiles/me/", payload, { headers: await authHeader() });
  return data;
}

export async function searchProfiles(q: string, offset = 0) {
  const { data } = await api.get<ApiResponse<Paginated<CompactUser>>>("/profiles/search/", { params: { q, offset }, headers: await authHeader() });
  return data;
}

export async function follow(username: string) {
  const { data } = await api.post<ApiResponse<{ state: string; request_id: number | null }>>(`/profiles/${username}/follow/`, {}, { headers: await authHeader() });
  return data;
}

export async function unfollow(username: string) {
  const { data } = await api.delete<ApiResponse<{ removed: boolean }>>(`/profiles/${username}/follow/`, { headers: await authHeader() });
  return data;
}

export async function relationshipList(name: "followers" | "following" | "requests-received" | "requests-sent" | "suggested", offset = 0) {
  const { data } = await api.get<ApiResponse<Paginated<CompactUser>>>(`/relationships/${name}/`, { params: { offset }, headers: await authHeader() });
  return data;
}

export async function block(username: string) {
  const { data } = await api.post<ApiResponse<Record<string, never>>>(`/relationships/blocked/${username}/`, {}, { headers: await authHeader() });
  return data;
}

export async function unblock(username: string) {
  const { data } = await api.delete<ApiResponse<{ removed: boolean }>>(`/relationships/blocked/${username}/`, { headers: await authHeader() });
  return data;
}

export async function simpleRelationship(kind: "restricted" | "muted" | "close-friends", username: string, method: "post" | "delete", payload = {}) {
  const url = `/relationships/${kind}/${username}/`;
  const headers = await authHeader();
  const { data } = method === "post"
    ? await api.post<ApiResponse<{ user: CompactUser }>>(url, payload, { headers })
    : await api.delete<ApiResponse<{ removed: boolean }>>(url, { headers });
  return data;
}

export async function getPrivacy() {
  const { data } = await api.get<ApiResponse<{ privacy: PrivacySettings }>>("/profiles/privacy/", { headers: await authHeader() });
  return data;
}

export async function updatePrivacy(payload: Partial<PrivacySettings>) {
  const { data } = await api.patch<ApiResponse<{ privacy: PrivacySettings }>>("/profiles/privacy/", payload, { headers: await authHeader() });
  return data;
}

export async function simpleRelationshipList(kind: "blocked" | "restricted" | "muted" | "close-friends", offset = 0) {
  const { data } = await api.get<ApiResponse<Paginated<CompactUser>>>(`/relationships/${kind}/`, { params: { offset }, headers: await authHeader() });
  return data;
}

export async function uploadProfileMedia(kind: "profile_picture" | "cover_photo", file: { uri: string; name: string; type: string }, onProgress?: (progress: number) => void) {
  const form = new FormData();
  form.append("type", kind);
  form.append("image", file as unknown as Blob);
  const { data } = await api.post<ApiResponse<{ profile: Profile }>>("/profiles/me/media/", form, {
    headers: { ...(await authHeader()), "Content-Type": "multipart/form-data" },
    onUploadProgress: (event) => {
      if (event.total && onProgress) onProgress(Math.round((event.loaded / event.total) * 100));
    },
  });
  return data;
}

export async function removeProfileMedia(kind: "profile_picture" | "cover_photo") {
  const { data } = await api.delete<ApiResponse<{ profile: Profile }>>("/profiles/me/media/", { data: { type: kind }, headers: await authHeader() });
  return data;
}
