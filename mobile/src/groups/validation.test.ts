import { describe, expect, it } from "vitest";
import { canModerateRole, parseMemberInput, validateGroupDescription, validateGroupMessage, validateGroupName } from "./validation";

describe("group validation", () => {
  it("validates names and descriptions", () => {
    expect(validateGroupName("Family")).toBeNull();
    expect(validateGroupName("   ")).toBe("Group name is required.");
    expect(validateGroupName("x".repeat(121))).toContain("120");
    expect(validateGroupDescription("x".repeat(1001))).toContain("1000");
  });
  it("normalizes member entry and message bodies", () => {
    expect(parseMemberInput("asha, bob bob\ncaro")).toEqual(["asha", "bob", "caro"]);
    expect(validateGroupMessage("", false)).toContain("required");
    expect(validateGroupMessage("", true)).toBeNull();
    expect(validateGroupMessage("hello", false)).toBeNull();
  });
  it("detects moderation roles", () => {
    expect(canModerateRole("admin")).toBe(true);
    expect(canModerateRole("member")).toBe(false);
  });
});
