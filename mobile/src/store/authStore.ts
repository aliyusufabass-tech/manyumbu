import * as SecureStore from "expo-secure-store";
import { create } from "zustand";
import type { AuthTokens, ManyumbuUser } from "../types/auth";

type AuthState = {
  user: ManyumbuUser | null;
  tokens: AuthTokens | null;
  setSession: (user: ManyumbuUser, tokens: AuthTokens) => Promise<void>;
  signOut: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  tokens: null,
  async setSession(user, tokens) {
    await SecureStore.setItemAsync("manyumbu_access", tokens.access);
    await SecureStore.setItemAsync("manyumbu_refresh", tokens.refresh);
    set({ user, tokens });
  },
  async signOut() {
    await SecureStore.deleteItemAsync("manyumbu_access");
    await SecureStore.deleteItemAsync("manyumbu_refresh");
    set({ user: null, tokens: null });
  },
}));
