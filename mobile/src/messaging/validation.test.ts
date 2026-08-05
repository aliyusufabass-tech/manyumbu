import { describe, expect, it } from "vitest";
import { queueTextMessage, cancelQueuedMessage, queuedMessages } from "./queue";
import { validateDocument, validateTextMessage, validateVoiceNote } from "./validation";

describe("messaging validation", () => {
  it("rejects empty and oversized text", () => { expect(validateTextMessage("   ")).toBeTruthy(); expect(validateTextMessage("x".repeat(5001))).toBeTruthy(); expect(validateTextMessage("hello\nworld")).toBeNull(); });
  it("validates voice notes", () => { expect(validateVoiceNote(5, 1024, "audio/webm")).toBeNull(); expect(validateVoiceNote(901, 1024, "audio/webm")).toBeTruthy(); expect(validateVoiceNote(5, 1024, "video/mp4")).toBeTruthy(); });
  it("blocks dangerous documents", () => { expect(validateDocument("safe.pdf", 2000, "application/pdf")).toBeNull(); expect(validateDocument("run.exe", 2000, "application/octet-stream")).toBeTruthy(); });
  it("queues and cancels local outgoing messages", () => { const item = queueTextMessage("conversation", "hello"); expect(queuedMessages().some((msg) => msg.id === item.id)).toBe(true); cancelQueuedMessage(item.id); expect(queuedMessages().some((msg) => msg.id === item.id)).toBe(false); });
});
