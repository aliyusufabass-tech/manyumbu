import { describe, expect, it } from "vitest";
import { registrationNextStep } from "./registration";
import type { ManyumbuUser } from "../types/auth";

const user: ManyumbuUser = {
  phone_number: "+255714123456",
  email: "asha@example.com",
  username: "asha",
  full_name: "Asha Manyumbu",
  is_email_verified: true,
  is_active: true,
};

describe("registration navigation", () => {
  it("sends completed registrations to Sign in", () => {
    expect(registrationNextStep({ user, requires_verification: false, access: "access-token", refresh: "refresh-token" })).toEqual({
      screen: "login",
    });
  });

  it("sends verification-required registrations to Sign in", () => {
    expect(registrationNextStep({ user: { ...user, is_email_verified: false, is_active: false } })).toEqual({
      screen: "login",
    });
  });
});