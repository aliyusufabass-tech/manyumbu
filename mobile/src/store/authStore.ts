import { create } from "zustand";
import type { AuthTokens, ManyumbuUser } from "../types/auth";
import { deleteTokenItem, setTokenItem } from "./tokenStorage";

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
    await setTokenItem("manyumbu_access", tokens.access);
    await setTokenItem("manyumbu_refresh", tokens.refresh);
    set({ user, tokens });
  },
  async signOut() {
    await deleteTokenItem("manyumbu_access");
    await deleteTokenItem("manyumbu_refresh");
    set({ user: null, tokens: null });
  },
}));
