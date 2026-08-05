import { describe, expect, it } from "vitest";
import { callIsTerminal, callSupportsVideo, nativeWebRtcStatus, validateAppeal, validateBusinessForm, validateCallTarget, validateCreatorForm, validateVerification } from "./validation";

describe("Phase 7 call and professional validation", () => {
  it("validates call targets and states", () => {
    expect(validateCallTarget("private", "abc")).toBeNull();
    expect(validateCallTarget("group", "")).toContain("Group");
    expect(callSupportsVideo("group_video")).toBe(true);
    expect(callIsTerminal("missed")).toBe(true);
  });
  it("reports native WebRTC capability accurately", () => {
    expect(nativeWebRtcStatus({ native_webrtc_required: true, expo_go_supported: false, turn_configured: false })).toBe("development_build_required");
    expect(nativeWebRtcStatus({ native_webrtc_required: false })).toBe("available");
  });
  it("validates creator, business, verification, and appeal forms", () => {
    expect(validateCreatorForm("Travel", "bio")).toBeNull();
    expect(validateBusinessForm("Shop", "Retail", "ftp://bad")).toContain("website");
    expect(validateVerification("Too short", ["https://example.com"])).toContain("20");
    expect(validateAppeal("please review this action")).toBeNull();
  });
});
