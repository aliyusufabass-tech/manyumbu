import { getWsToken } from "../api/messaging";
import type { ChatEvent } from "../types/messaging";
import { websocketBaseUrl } from "../config/env";

export async function openConversationSocket(conversationId: string, onEvent: (event: ChatEvent) => void) { const token = await getWsToken(); const socket = new WebSocket(`${websocketBaseUrl()}/ws/chat/${conversationId}/?token=${encodeURIComponent(token ?? "")}`); socket.onmessage = (message) => { try { onEvent(JSON.parse(message.data)); } catch { onEvent({ event: "error", version: 1, data: { message: "Invalid event payload." } }); } }; return socket; }
export function sendSocketEvent(socket: WebSocket | null, event: string, data: Record<string, unknown> = {}, requestId = `${Date.now()}`) { if (!socket || socket.readyState !== WebSocket.OPEN) return false; socket.send(JSON.stringify({ event, version: 1, data, request_id: requestId })); return true; }
