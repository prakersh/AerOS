import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/api/client";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type ProviderStatus = "active" | "inactive" | "error";

interface AIProvider {
  id: number;
  provider_name: string;
  display_name: string;
  capability: string;
  model_id: string | null;
  status: ProviderStatus;
  is_default?: boolean;
}

interface TestResult {
  ok: boolean;
  error?: string;
}

/* ------------------------------------------------------------------ */
/* Status badge                                                        */
/* ------------------------------------------------------------------ */

const STATUS_STYLES: Record<ProviderStatus, string> = {
  active: "bg-green-900/40 text-green-400",
  inactive: "bg-zinc-700/50 text-zinc-400",
  error: "bg-red-900/40 text-red-400",
};

/* ------------------------------------------------------------------ */
/* Provider icon                                                       */
/* ------------------------------------------------------------------ */

function ProviderIcon() {
  return (
    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-900/30">
      <svg
        className="h-5 w-5 text-indigo-400"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={1.5}
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z"
        />
      </svg>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function AdminAIProviders() {
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});

  const {
    data: providers = [],
    isLoading,
    error,
  } = useQuery<AIProvider[]>({
    queryKey: ["admin", "ai-providers"],
    queryFn: () => api.get<AIProvider[]>("/api/admin/ai/providers"),
  });

  const testMutation = useMutation({
    mutationFn: (providerName: string) =>
      api.post<TestResult>("/api/admin/ai/providers/test", {
        provider_name: providerName,
      }),
    onSuccess: (data, providerName) => {
      setTestResults((prev) => ({ ...prev, [providerName]: data }));
    },
    onError: (_err, providerName) => {
      setTestResults((prev) => ({
        ...prev,
        [providerName]: { ok: false, error: "Connection test failed" },
      }));
    },
  });

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100">AI Providers</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Configure AI models, toggle providers, set token caps and failover
          priority.
        </p>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-indigo-500" />
          <span className="ml-3 text-sm text-zinc-500">Loading providers...</span>
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div className="rounded-xl border border-red-800/50 bg-red-900/20 p-4">
          <p className="text-sm text-red-400">Failed to load AI providers.</p>
        </div>
      )}

      {/* Provider Cards */}
      {!isLoading && !error && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {providers.map((provider) => {
            const result = testResults[provider.provider_name];
            const isTesting =
              testMutation.isPending &&
              testMutation.variables === provider.provider_name;

            return (
              <div
                key={provider.id}
                className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 transition hover:border-zinc-700"
              >
                <div className="flex items-start gap-4">
                  <ProviderIcon />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-medium text-zinc-200">
                        {provider.display_name}
                      </h3>
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${STATUS_STYLES[provider.status]}`}
                      >
                        {provider.status}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-zinc-500">
                      {provider.capability}
                    </p>
                    {provider.model_id && (
                      <p className="mt-2 rounded-md bg-zinc-950 px-2.5 py-1.5 font-mono text-xs text-zinc-400">
                        {provider.model_id}
                      </p>
                    )}
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between">
                  {/* Test result message */}
                  <div className="text-xs">
                    {result?.ok === true && (
                      <span className="text-green-400">Connection OK</span>
                    )}
                    {result?.ok === false && (
                      <span className="text-red-400">
                        {result.error ?? "Failed"}
                      </span>
                    )}
                  </div>

                  <button
                    type="button"
                    disabled={isTesting}
                    onClick={() => testMutation.mutate(provider.provider_name)}
                    className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-400 transition hover:border-zinc-600 hover:text-zinc-300 disabled:opacity-50"
                  >
                    {isTesting ? "Testing..." : "Test Connection"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <p className="text-xs text-zinc-600">
        Provider management and failover configuration will be available in a
        future release.
      </p>
    </div>
  );
}
