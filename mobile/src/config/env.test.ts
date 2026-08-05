import { describe, expect, it } from "vitest";
import { websocketBaseUrl } from "./env";

describe("mobile environment config", () => {
  it("derives websocket origins from API URLs", () => {
    expect(websocketBaseUrl("https://api.example.com/api/v1")).toBe("wss://api.example.com");
    expect(websocketBaseUrl("http://127.0.0.1:8000/api/v1")).toBe("ws://127.0.0.1:8000");
  });
});
