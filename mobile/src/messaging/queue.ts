import type { QueuedMessage } from "../types/messaging";
import { sendTextMessage } from "../api/messaging";

const memoryQueue: QueuedMessage[] = [];
export function createClientMessageId() { return `client-${Date.now()}-${Math.random().toString(36).slice(2)}`; }
export function queueTextMessage(conversationId: string, text: string, replyToId?: string) { const queued: QueuedMessage = { id: createClientMessageId(), conversationId, text, replyToId, createdAt: new Date().toISOString(), status: "queued" }; memoryQueue.push(queued); return queued; }
export function queuedMessages() { return [...memoryQueue]; }
export function cancelQueuedMessage(id: string) { const index = memoryQueue.findIndex((item) => item.id === id); if (index >= 0) memoryQueue.splice(index, 1); }
export async function flushQueue() { const { sendTextMessage } = await import("../api/messaging"); const sent: string[] = []; for (const item of memoryQueue) { item.status = "sending"; try { await sendTextMessage(item.conversationId, item.text, item.id, item.replyToId); sent.push(item.id); } catch { item.status = "failed"; } } sent.forEach(cancelQueuedMessage); return { sent, remaining: queuedMessages() }; }

