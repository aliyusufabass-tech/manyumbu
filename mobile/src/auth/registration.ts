import type { RegisterResponseData } from "../api/auth";

export type RegistrationNextStep = { screen: "login" };

export function registrationNextStep(_data: RegisterResponseData): RegistrationNextStep {
  return { screen: "login" };
}