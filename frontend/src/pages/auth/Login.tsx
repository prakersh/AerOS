import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useLocation, Link } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, initialized, login, loading, error, clearError } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const successMessage = (location.state as { message?: string })?.message;

  if (initialized && user) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    clearError();
    await login(email, password);
    if (useAuthStore.getState().user) {
      navigate("/", { replace: true });
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight text-zinc-100">
            AEROS
          </h1>
          <p className="mt-1 text-sm text-zinc-500">AI Procurement OS</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-xl border border-zinc-800 bg-zinc-900 p-6"
        >
          <div>
            <label
              htmlFor="email"
              className="mb-1 block text-xs font-medium text-zinc-400"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-1 block text-xs font-medium text-zinc-400"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              placeholder="Password"
            />
          </div>

          {successMessage && (
            <p className="text-sm text-green-400">{successMessage}</p>
          )}

          {error && (
            <p className="text-sm text-red-400">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="mt-4 text-sm text-zinc-500 text-center">
          Don't have an account?{" "}
          <Link to="/register" className="text-indigo-600 hover:underline">
            Register
          </Link>
        </p>

        {import.meta.env.DEV && (
        <div className="mt-6 rounded-lg border border-zinc-800/50 bg-zinc-900/50 p-4">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-600">
            Demo Credentials
          </p>
          <div className="space-y-1.5 text-[11px]">
            <button
              type="button"
              onClick={() => { setEmail("buyer@aeros.demo"); setPassword("buyer123"); }}
              className="flex w-full items-center justify-between rounded px-2 py-1 text-left hover:bg-zinc-800/60"
            >
              <span className="text-zinc-400">Buyer</span>
              <span className="text-zinc-600">buyer@aeros.demo</span>
            </button>
            <button
              type="button"
              onClick={() => { setEmail("freshfarm@vendor.demo"); setPassword("vendor123"); }}
              className="flex w-full items-center justify-between rounded px-2 py-1 text-left hover:bg-zinc-800/60"
            >
              <span className="text-zinc-400">Vendor</span>
              <span className="text-zinc-600">freshfarm@vendor.demo</span>
            </button>
            <button
              type="button"
              onClick={() => { setEmail("admin@aeros.demo"); setPassword("admin123"); }}
              className="flex w-full items-center justify-between rounded px-2 py-1 text-left hover:bg-zinc-800/60"
            >
              <span className="text-zinc-400">Admin</span>
              <span className="text-zinc-600">admin@aeros.demo</span>
            </button>
          </div>
        </div>
        )}
      </div>
    </div>
  );
}
