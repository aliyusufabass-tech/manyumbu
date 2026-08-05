import { getGroupWsToken } from "../api/groups";
import type { ChatEvent } from "../types/messaging";
import { websocketBaseUrl } from "../config/env";

export function groupWebsocketBaseUrl() { return websocketBaseUrl(); }
export async function openGroupSocket(groupId: string, onEvent: (event: ChatEvent) => void) { const token = await getGroupWsToken(); const socket = new WebSocket(`${websocketBaseUrl()}/ws/groups/${groupId}/?token=${encodeURIComponent(token ?? "")}`); socket.onmessage = (message) => { try { onEvent(JSON.parse(message.data)); } catch { onEvent({ event: "error", version: 1, data: { message: "Invalid event payload." } }); } }; return socket; }
export function sendGroupSocketEvent(socket: WebSocket | null, event: string, data: Record<string, unknown> = {}, requestId = `${Date.now()}`) { if (!socket || socket.readyState !== WebSocket.OPEN) return false; socket.send(JSON.stringify({ event, version: 1, data, request_id: requestId })); return true; }
