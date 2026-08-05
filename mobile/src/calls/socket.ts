import { getCallWsToken } from "../api/phase7";
import type { CallEvent } from "../types/phase7";

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";
export function callWebsocketBaseUrl() { return API_URL.replace(/^http/, "ws").replace(/\/api\/v1\/?$/, ""); }
export async function openCallSocket(callId: string, onEvent: (event: CallEvent) => void) { const token = await getCallWsToken(); const socket = new WebSocket(`${callWebsocketBaseUrl()}/ws/calls/${callId}/?token=${encodeURIComponent(token ?? "")}`); socket.onmessage = (message) => { try { onEvent(JSON.parse(message.data)); } catch { onEvent({ event: "error", version: 1, data: { message: "Invalid call event payload." } }); } }; return socket; }
export function sendCallSocketEvent(socket: WebSocket | null, event: string, data: Record<string, unknown> = {}, requestId = `${Date.now()}`) { if (!socket || socket.readyState !== WebSocket.OPEN) return false; socket.send(JSON.stringify({ event, version: 1, data, request_id: requestId })); return true; }
