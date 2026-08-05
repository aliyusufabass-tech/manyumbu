import * as SecureStore from "expo-secure-store";
import { api } from "./client";
import type { ApiResponse } from "../types/auth";
import type { ActionPage, AppealPage, Call, CallConfig, CallPage, CallType, FeatureRestriction, ModerationAppeal, ProfessionalAccount, ProfessionalInsights, RestrictionPage, VerificationPage, VerificationRequest } from "../types/phase7";

async function authHeader() { const token = await SecureStore.getItemAsync("manyumbu_access"); return token ? { Authorization: `Bearer ${token}` } : {}; }
export async function getCallWsToken() { return SecureStore.getItemAsync("manyumbu_access"); }
export async function listCalls(params: { status?: string; type?: string } = {}) { const { data } = await api.get<ApiResponse<CallPage>>("/calls/", { params, headers: await authHeader() }); return data; }
export async function createCall(payload: { call_type: CallType; conversation_id?: string; group_id?: string }) { const { data } = await api.post<ApiResponse<{ call: Call }>>("/calls/", payload, { headers: await authHeader() }); return data; }
export async function getCall(id: string) { const { data } = await api.get<ApiResponse<{ call: Call }>>(`/calls/${id}/`, { headers: await authHeader() }); return data; }
export async function callAction(id: string, action: "accept" | "decline" | "cancel" | "end" | "join" | "leave" | "timeout", payload: Record<string, unknown> = {}) { const { data } = await api.post<ApiResponse<{ call: Call }>>(`/calls/${id}/${action}/`, payload, { headers: await authHeader() }); return data; }
export async function reportCall(id: string, reason: string, details = "") { const { data } = await api.post<ApiResponse<{ report_id: number }>>(`/calls/${id}/report/`, { reason, details }, { headers: await authHeader() }); return data; }
export async function deleteCallHistory(id: string) { const { data } = await api.delete<ApiResponse<Record<string, never>>>(`/calls/${id}/history/`, { headers: await authHeader() }); return data; }
export async function getCallConfig(id: string) { const { data } = await api.post<ApiResponse<{ config: CallConfig }>>(`/calls/${id}/config/`, {}, { headers: await authHeader() }); return data; }
export async function getCallPrivacy() { const { data } = await api.get<ApiResponse<{ privacy: Record<string, unknown> }>>("/calls/privacy/", { headers: await authHeader() }); return data; }
export async function updateCallPrivacy(payload: Record<string, unknown>) { const { data } = await api.patch<ApiResponse<{ privacy: Record<string, unknown> }>>("/calls/privacy/", payload, { headers: await authHeader() }); return data; }
export async function getProfessionalAccount() { const { data } = await api.get<ApiResponse<{ professional_account: ProfessionalAccount | null }>>("/professional-account/", { headers: await authHeader() }); return data; }
export async function createCreatorAccount(payload: Record<string, unknown>) { const { data } = await api.post<ApiResponse<{ professional_account: ProfessionalAccount }>>("/professional-account/creator/", payload, { headers: await authHeader() }); return data; }
export async function createBusinessAccount(payload: Record<string, unknown>) { const { data } = await api.post<ApiResponse<{ professional_account: ProfessionalAccount }>>("/professional-account/business/", payload, { headers: await authHeader() }); return data; }
export async function getProfessionalInsights() { const { data } = await api.get<ApiResponse<{ insights: ProfessionalInsights }>>("/professional-account/insights/", { headers: await authHeader() }); return data; }
export async function createVerificationRequest(payload: Record<string, unknown>) { const { data } = await api.post<ApiResponse<{ verification_request: VerificationRequest }>>("/verification-requests/", payload, { headers: await authHeader() }); return data; }
export async function listVerificationRequests() { const { data } = await api.get<ApiResponse<VerificationPage>>("/verification-requests/", { headers: await authHeader() }); return data; }
export async function listModerationActions() { const { data } = await api.get<ApiResponse<ActionPage>>("/moderation/actions/", { headers: await authHeader() }); return data; }
export async function listRestrictions() { const { data } = await api.get<ApiResponse<RestrictionPage>>("/moderation/restrictions/", { headers: await authHeader() }); return data; }
export async function submitAppeal(actionId: string, explanation: string) { const { data } = await api.post<ApiResponse<{ appeal: ModerationAppeal }>>(`/moderation/actions/${actionId}/appeal/`, { explanation }, { headers: await authHeader() }); return data; }
export async function listAppeals() { const { data } = await api.get<ApiResponse<AppealPage>>("/moderation/appeals/", { headers: await authHeader() }); return data; }
