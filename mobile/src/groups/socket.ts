import { getGroupWsToken } from "../api/groups";
import type { ChatEvent } from "../types/messaging";

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";
export function groupWebsocketBaseUrl() { return API_URL.replace(/^http/, "ws").replace(/\/api\/v1\/?$/, ""); }
export async function openGroupSocket(groupId: string, onEvent: (event: ChatEvent) => void) { const token = await getGroupWsToken(); const socket = new WebSocket(`${groupWebsocketBaseUrl()}/ws/groups/${groupId}/?token=${encodeURIComponent(token ?? "")}`); socket.onmessage = (message) => { try { onEvent(JSON.parse(message.data)); } catch { onEvent({ event: "error", version: 1, data: { message: "Invalid event payload." } }); } }; return socket; }
export function sendGroupSocketEvent(socket: WebSocket | null, event: string, data: Record<string, unknown> = {}, requestId = `${Date.now()}`) { if (!socket || socket.readyState !== WebSocket.OPEN) return false; socket.send(JSON.stringify({ event, version: 1, data, request_id: requestId })); return true; }
