import { describe, expect, it } from "vitest";
import { validateComposerDraft } from "./composerValidation";

describe("validateComposerDraft", () => {
  it("rejects empty posts", () => {
    expect(validateComposerDraft({ caption: "", media: [], audience: "public", commentsEnabled: true })).toContain("Post must include text or media.");
  });

  it("accepts text-only posts", () => {
    expect(validateComposerDraft({ caption: "Hello Manyumbu", media: [], audience: "public", commentsEnabled: true })).toEqual([]);
  });

  it("rejects mixed image and video posts", () => {
    const errors = validateComposerDraft({ caption: "mixed", media: [{ type: "image/jpeg" }, { type: "video/mp4" }], audience: "public", commentsEnabled: true });
    expect(errors).toContain("Choose one video or up to 10 images, not mixed media.");
  });

  it("rejects oversized images", () => {
    const errors = validateComposerDraft({ caption: "photo", media: [{ type: "image/jpeg", size: 9 * 1024 * 1024 }], audience: "public", commentsEnabled: true });
    expect(errors).toContain("Each image must be 8MB or smaller.");
  });
});
