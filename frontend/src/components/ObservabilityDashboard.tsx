import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import {
  KpiCard,
  StatusBadge,
  PageHeader,
  LoadingSpinner,
  EmptyState,
  Modal,
  DetailView,
  FilterChips,
} from "@/components/ui";
import { formatTimestampAbsolute, formatCost, formatPercent } from "@/lib/format";

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
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  cost_usd: number;
  status: string;
  created_at: string;
}

interface ObservabilityDashboardProps {
  scope: "buyer" | "admin";
}

/* ------------------------------------------------------------------ */
/* Constants                                                            */
/* ------------------------------------------------------------------ */

const SCOPE_SUBTITLE: Record<ObservabilityDashboardProps["scope"], string> = {
  buyer: "AI call telemetry, latency tracking, and cost reporting.",
  admin: "Cross-tenant AI telemetry, latency distributions, and cost dashboards.",
};

const DAY_FILTER_OPTIONS = [
  { label: "7 days", value: "7" },
  { label: "14 days", value: "14" },
  { label: "30 days", value: "30" },
  { label: "90 days", value: "90" },
];

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function ObservabilityDashboard({ scope }: ObservabilityDashboardProps) {
  const [days, setDays] = useState("7");
  const [modelFilter, setModelFilter] = useState("all");
  const [selectedCall, setSelectedCall] = useState<LLMCall | null>(null);

  const {
    data: summary,
    isLoading: summaryLoading,
  } = useQuery<ObservabilitySummary>({
    queryKey: [scope, "observability", "summary", days],
    queryFn: () =>
      api.get<ObservabilitySummary>(`/api/observability/summary?days=${days}`),
  });

  const {
    data: calls = [],
    isLoading: callsLoading,
  } = useQuery<LLMCall[]>({
    queryKey: [scope, "observability", "calls", days],
    queryFn: () => api.get<LLMCall[]>(`/api/observability/calls?limit=50&days=${days}`),
  });

  const isLoading = summaryLoading || callsLoading;

  /* Extract unique models for dropdown filter */
  const uniqueModels = useMemo(() => {
    const models = new Set(calls.map((c) => c.model));
    return Array.from(models).sort();
  }, [calls]);

  /* Filtered calls by model */
  const filteredCalls = useMemo(
    () =>
      modelFilter === "all"
        ? calls
        : calls.filter((c) => c.model === modelFilter),
    [calls, modelFilter],
  );

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <PageHeader
        title="Observability"
        subtitle={SCOPE_SUBTITLE[scope]}
      />

      {/* Loading state */}
      {isLoading && <LoadingSpinner message="Loading telemetry..." />}

      {/* Date range filter */}
      {!isLoading && (
        <FilterChips
          options={DAY_FILTER_OPTIONS}
          active={days}
          onChange={setDays}
        />
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

      {/* Model filter dropdown */}
      {!isLoading && uniqueModels.length > 1 && (
        <div className="flex items-center gap-3">
          <label className="text-xs font-medium text-zinc-500">Model:</label>
          <select
            value={modelFilter}
            onChange={(e) => setModelFilter(e.target.value)}
            className="rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-200 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          >
            <option value="all">All Models</option>
            {uniqueModels.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
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

          {filteredCalls.length === 0 ? (
            <div className="p-6">
              <EmptyState
                title="No LLM calls recorded"
                description={
                  modelFilter !== "all"
                    ? "No calls match the selected model filter."
                    : "No LLM calls recorded for this period."
                }
              />
            </div>
          ) : (
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
                {filteredCalls.map((call) => (
                  <tr
                    key={call.id}
                    className="cursor-pointer transition hover:bg-zinc-800/40"
                    onClick={() => setSelectedCall(call)}
                  >
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-zinc-300">
                      {call.model}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 tabular-nums text-zinc-400">
                      <span title={`In: ${call.prompt_tokens.toLocaleString()} / Out: ${call.completion_tokens.toLocaleString()}`}>
                        {call.total_tokens.toLocaleString()}
                        <span className="ml-1 text-xs text-zinc-600">
                          ({call.prompt_tokens.toLocaleString()}↓ {call.completion_tokens.toLocaleString()}↑)
                        </span>
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 tabular-nums text-zinc-400">
                      {call.latency_ms}ms
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 tabular-nums text-zinc-400">
                      {formatCost(call.cost_usd)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <StatusBadge
                        status={call.status}
                        variant="health"
                      />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 tabular-nums text-zinc-500">
                      {formatTimestampAbsolute(call.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* LLM Call Detail Modal */}
      <Modal
        open={!!selectedCall}
        onClose={() => setSelectedCall(null)}
        title="LLM Call Details"
        size="md"
      >
        {selectedCall && (
          <DetailView
            items={[
              { label: "Model", value: selectedCall.model },
              { label: "Total Tokens", value: selectedCall.total_tokens.toLocaleString() },
              { label: "Latency", value: `${selectedCall.latency_ms}ms` },
              { label: "Cost", value: formatCost(selectedCall.cost_usd) },
              { label: "Status", value: selectedCall.status },
              { label: "Timestamp", value: formatTimestampAbsolute(selectedCall.created_at) },
            ]}
            columns={2}
          />
        )}
      </Modal>
    </div>
  );
}
