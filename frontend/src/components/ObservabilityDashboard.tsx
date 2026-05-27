import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface ObservabilitySummary {
  total_llm_calls: number;
  total_tokens: number;
  total_cost_usd: number;
  error_rate: number;
  avg_latency_ms: number;
}

interface LLMCall {
  id: number;
  model: string;
  tokens: number;
  latency_ms: number;
  cost: number;
  status: string;
  timestamp: string;
}

interface ObservabilityDashboardProps {
  scope: "buyer" | "admin";
}

/* ------------------------------------------------------------------ */
/* KPI card                                                            */
/* ------------------------------------------------------------------ */

function KpiCard({
  label,
  value,
  accent = "text-zinc-100",
}: {
  label: string;
  value: string | number;
  accent?: string;
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
      <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
        {label}
      </p>
      <p className={`mt-2 text-3xl font-semibold tabular-nums ${accent}`}>
        {value}
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function formatTimestamp(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`;
}

function formatPercent(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

const STATUS_STYLES: Record<string, string> = {
  success: "bg-green-900/40 text-green-400",
  ok: "bg-green-900/40 text-green-400",
  error: "bg-red-900/40 text-red-400",
  failed: "bg-red-900/40 text-red-400",
};

const SCOPE_SUBTITLE: Record<ObservabilityDashboardProps["scope"], string> = {
  buyer: "AI call telemetry, latency tracking, and cost reporting.",
  admin: "Cross-tenant AI telemetry, latency distributions, and cost dashboards.",
};

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function ObservabilityDashboard({ scope }: ObservabilityDashboardProps) {
  const {
    data: summary,
    isLoading: summaryLoading,
  } = useQuery<ObservabilitySummary>({
    queryKey: [scope, "observability", "summary"],
    queryFn: () =>
      api.get<ObservabilitySummary>("/api/observability/summary?days=7"),
  });

  const {
    data: calls = [],
    isLoading: callsLoading,
  } = useQuery<LLMCall[]>({
    queryKey: [scope, "observability", "calls"],
    queryFn: () => api.get<LLMCall[]>("/api/observability/calls?limit=50"),
  });

  const isLoading = summaryLoading || callsLoading;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100">Observability</h1>
        <p className="mt-1 text-sm text-zinc-500">
          {SCOPE_SUBTITLE[scope]}
        </p>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-indigo-500" />
          <span className="ml-3 text-sm text-zinc-500">Loading telemetry...</span>
        </div>
      )}

      {/* Summary cards */}
      {!isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <KpiCard
            label="Total LLM Calls"
            value={summary?.total_llm_calls ?? 0}
            accent="text-indigo-400"
          />
          <KpiCard
            label="Total Tokens"
            value={summary?.total_tokens?.toLocaleString() ?? "0"}
            accent="text-blue-400"
          />
          <KpiCard
            label="Cost USD"
            value={formatCost(summary?.total_cost_usd ?? 0)}
            accent="text-green-400"
          />
          <KpiCard
            label="Error Rate"
            value={formatPercent(summary?.error_rate ?? 0)}
            accent="text-red-400"
          />
          <KpiCard
            label="Avg Latency"
            value={`${Math.round(summary?.avg_latency_ms ?? 0)}ms`}
            accent="text-amber-400"
          />
        </div>
      )}

      {/* Recent calls table */}
      {!isLoading && (
        <div className="overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-900">
          <div className="px-5 py-4 border-b border-zinc-800">
            <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-500">
              Recent LLM Calls
            </h2>
          </div>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-800">
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Model
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Tokens
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Latency
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Cost
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Status
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Timestamp
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              {calls.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-sm text-zinc-600">
                    No LLM calls recorded yet.
                  </td>
                </tr>
              )}
              {calls.map((call) => (
                <tr
                  key={call.id}
                  className="transition hover:bg-zinc-800/40"
                >
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-zinc-300">
                    {call.model}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums text-zinc-400">
                    {call.tokens.toLocaleString()}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums text-zinc-400">
                    {call.latency_ms}ms
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums text-zinc-400">
                    {formatCost(call.cost)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${STATUS_STYLES[call.status.toLowerCase()] ?? "bg-zinc-700/50 text-zinc-400"}`}
                    >
                      {call.status}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums text-zinc-500">
                    {formatTimestamp(call.timestamp)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
