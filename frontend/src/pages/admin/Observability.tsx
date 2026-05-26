/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface PlaceholderMetric {
  label: string;
  description: string;
}

/* ------------------------------------------------------------------ */
/* Placeholder metrics                                                 */
/* ------------------------------------------------------------------ */

const METRICS: PlaceholderMetric[] = [
  {
    label: "LLM Token Usage",
    description: "Total input + output tokens consumed across all providers",
  },
  {
    label: "API Latency (p50 / p95)",
    description: "Server-side response time percentiles for all endpoints",
  },
  {
    label: "Error Rate",
    description: "Percentage of 4xx/5xx responses in the last 24 hours",
  },
  {
    label: "Avg Response Time",
    description: "Mean time for vendor quote submissions across all RFx",
  },
  {
    label: "Extraction Success Rate",
    description: "AI line-item extraction accuracy (correct items / total)",
  },
  {
    label: "Vendor Response Rate",
    description: "Percentage of dispatched RFx with at least one quote",
  },
];

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function AdminObservability() {
  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100">Observability</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Cross-tenant AI telemetry, latency distributions, and cost dashboards.
        </p>
      </div>

      {/* Coming soon banner */}
      <div className="rounded-xl border border-dashed border-zinc-700 bg-zinc-900/50 p-6 text-center">
        <svg
          className="mx-auto h-8 w-8 text-zinc-600"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
          />
        </svg>
        <p className="mt-3 text-sm font-medium text-zinc-300">
          Observability dashboard coming soon
        </p>
        <p className="mt-1 text-xs text-zinc-600">
          System-wide metrics, LLM cost tracking, and latency distributions will
          appear here once instrumentation is enabled.
        </p>
      </div>

      {/* Placeholder metric cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {METRICS.map((metric) => (
          <div
            key={metric.label}
            className="rounded-xl border border-dashed border-zinc-700 bg-zinc-900/50 p-5"
          >
            <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
              {metric.label}
            </p>
            <div className="mt-3 h-8 w-24 animate-pulse rounded-md bg-zinc-800" />
            <p className="mt-3 text-xs text-zinc-600">{metric.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
