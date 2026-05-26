import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface UserInfo {
  id: number;
  email: string;
  role: string;
  display_name: string;
  org_id: number;
}

interface BuyerDefaults {
  payment_terms: string;
  delivery_terms: string;
  quote_validity_days: number;
  currency: string;
  tax_treatment: string;
  delivery_window: string;
}

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function BuyerSettings() {
  const {
    data: user,
    isLoading,
    error,
  } = useQuery<UserInfo>({
    queryKey: ["auth", "me"],
    queryFn: () => api.get<UserInfo>("/api/auth/me"),
  });

  const { data: defaults } = useQuery<BuyerDefaults>({
    queryKey: ["buyer", "defaults"],
    queryFn: () => api.get<BuyerDefaults>("/api/buyer/defaults"),
  });

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100">Settings</h1>
        <p className="mt-1 text-sm text-zinc-500">
          User profile, default terms, and preferences.
        </p>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-indigo-500" />
          <span className="ml-3 text-sm text-zinc-500">Loading profile...</span>
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <div className="rounded-xl border border-red-800/50 bg-red-900/20 p-4">
          <p className="text-sm text-red-400">
            Failed to load profile. Please try again.
          </p>
        </div>
      )}

      {/* Profile Card */}
      {!isLoading && !error && user && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
          <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-500">
            Profile
          </h2>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium text-zinc-500">
                Display Name
              </label>
              <p className="mt-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200">
                {user.display_name}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500">
                Email
              </label>
              <p className="mt-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200">
                {user.email}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500">
                Role
              </label>
              <p className="mt-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 capitalize">
                {user.role}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500">
                Organization ID
              </label>
              <p className="mt-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200">
                {user.org_id}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Default Terms */}
      {!isLoading && !error && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
          <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-500">
            Default Terms
          </h2>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { label: "Payment Terms", value: defaults?.payment_terms ?? "NET30" },
              { label: "Delivery Terms", value: defaults?.delivery_terms ?? "doorstep" },
              { label: "Currency", value: defaults?.currency ?? "INR" },
              { label: "Quote Validity", value: `${defaults?.quote_validity_days ?? 7} days` },
              { label: "Tax Treatment", value: defaults?.tax_treatment ?? "exclusive" },
              { label: "Delivery Window", value: defaults?.delivery_window ?? "next day" },
            ].map((term) => (
              <div key={term.label}>
                <label className="block text-xs font-medium text-zinc-500">
                  {term.label}
                </label>
                <p className="mt-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm font-medium text-zinc-200 capitalize">
                  {term.value}
                </p>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs text-zinc-600">
            These defaults are applied automatically to new RFx.
          </p>
        </div>
      )}
    </div>
  );
}
