import { describe, expect, it } from "vitest";
import { validateReelDraft, validateStoryDraft } from "./validation";

describe("phase4 validation", () => {
  it("rejects empty stories", () => { expect(validateStoryDraft({ text: "" })).toContain("Story needs text or media."); });
  it("validates story polls", () => { expect(validateStoryDraft({ text: "poll", pollOptions: ["Yes"] })).toContain("Polls need two to four options."); });
  it("validates story links", () => { expect(validateStoryDraft({ text: "link", linkUrl: "manyumbu.test" })).toContain("Links must start with http or https."); });
  it("rejects missing reel video", () => { expect(validateReelDraft({ caption: "" })).toContain("Reel video is required."); });
  it("rejects oversized reels", () => { expect(validateReelDraft({ caption: "", video: { type: "video/mp4", size: 121 * 1024 * 1024 } })).toContain("Reel video must be 120MB or smaller."); });
});
