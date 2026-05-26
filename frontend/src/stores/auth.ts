import { create } from "zustand";
import { api } from "@/api/client";

export type UserRole = "buyer" | "vendor" | "admin";

export interface AuthUser {
  id: string;
  email: string;
  role: UserRole;
  display_name: string;
}

interface AuthState {
  user: AuthUser | null;
  loading: boolean;
  error: string | null;

  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchMe: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ loading: true, error: null });
    try {
      const user = await api.post<AuthUser>("/api/auth/login", {
        email,
        password,
      });
      set({ user, loading: false });
    } catch (err: unknown) {
      const message =
        err && typeof err === "object" && "message" in err
          ? String((err as { message: string }).message)
          : "Login failed";
      set({ error: message, loading: false });
    }
  },

  logout: async () => {
    try {
      await api.post("/api/auth/logout");
    } finally {
      set({ user: null, error: null });
    }
  },

  fetchMe: async () => {
    set({ loading: true });
    try {
      const user = await api.get<AuthUser>("/api/auth/me");
      set({ user, loading: false });
    } catch {
      set({ user: null, loading: false });
    }
  },

  clearError: () => set({ error: null }),
}));
