import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import {
  PageHeader,
  LoadingSpinner,
  ErrorState,
  EmptyState,
  Modal,
  DetailView,
  FilterChips,
} from "@/components/ui";
import { formatTimestamp } from "@/lib/format";
import type { AuditEntry } from "@/types";

/* ------------------------------------------------------------------ */
/* Action badge styles (page-specific)                                 */
/* ------------------------------------------------------------------ */

const ACTION_COLORS: Record<string, string> = {
  create_rfx: "bg-indigo-900/40 text-indigo-400",
  dispatch_rfx: "bg-blue-900/40 text-blue-400",
  award_rfx: "bg-emerald-900/40 text-emerald-400",
  cancel_rfx: "bg-red-900/40 text-red-400",
  override_offer_field: "bg-amber-900/40 text-amber-400",
};

function detailsSummary(details: Record<string, unknown>): string {
  const parts: string[] = [];
  if (details.title) parts.push(String(details.title));
  if (details.status) parts.push(`status: ${details.status}`);
  if (details.vendor_count != null) parts.push(`${details.vendor_count} vendors`);
  if (details.reason) parts.push(`reason: ${details.reason}`);
  if (details.field) parts.push(`${details.field} = ${details.new_value}`);
  return parts.join(", ") || "—";
}

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function AdminAudit() {
  const { data: logs = [], isLoading, error, refetch } = useQuery<AuditEntry[]>({
    queryKey: ["admin", "audit"],
    queryFn: () => api.get<AuditEntry[]>("/api/admin/audit"),
  });

  const [actionFilter, setActionFilter] = useState("all");
  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null);

  /* Derive unique action types for filter chips */
  const actionFilterOptions = useMemo(() => {
    const actions = Array.from(new Set(logs.map((l) => l.action)));
    return [
      { label: "All", value: "all" },
      ...actions.map((a) => ({ label: a.replace(/_/g, " "), value: a })),
    ];
  }, [logs]);

  const filtered = useMemo(() => {
    if (actionFilter === "all") return logs;
    return logs.filter((l) => l.action === actionFilter);
  }, [logs, actionFilter]);

  if (isLoading) return <LoadingSpinner message="Loading audit log..." />;
  if (error) return <ErrorState message="Failed to load audit log." onRetry={refetch} />;

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Audit Log"
        subtitle="Complete record of all system actions."
      />

      {logs.length > 0 && (
        <FilterChips
          options={actionFilterOptions}
          active={actionFilter}
          onChange={setActionFilter}
        />
      )}

      {filtered.length === 0 ? (
        <EmptyState
          title="No audit entries"
          description={
            actionFilter !== "all"
              ? "No entries match the selected action filter."
              : "No audit entries have been recorded yet."
          }
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-900">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-800">
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">Timestamp</th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">Actor</th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">Action</th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">Entity</th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              {filtered.map((entry) => (
                <tr
                  key={entry.id}
                  className="cursor-pointer transition hover:bg-zinc-800/40"
                  onClick={() => setSelectedEntry(entry)}
                >
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums text-zinc-500">
                    {formatTimestamp(entry.created_at)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-zinc-300">
                    {entry.actor_name}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${ACTION_COLORS[entry.action] ?? "bg-zinc-700/50 text-zinc-400"}`}
                    >
                      {entry.action.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-zinc-400">
                    {entry.entity_type} #{entry.entity_id}
                  </td>
                  <td className="max-w-xs truncate px-4 py-3 text-xs text-zinc-500">
                    {detailsSummary(entry.details)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-zinc-600">
        {filtered.length} of {logs.length} {logs.length === 1 ? "entry" : "entries"} shown.
      </p>

      {/* Detail modal */}
      <Modal
        open={!!selectedEntry}
        onClose={() => setSelectedEntry(null)}
        title="Audit Entry Details"
      >
        {selectedEntry && (
          <DetailView
            columns={1}
            items={[
              { label: "Action", value: selectedEntry.action.replace(/_/g, " ") },
              { label: "Actor", value: `${selectedEntry.actor_name}${selectedEntry.actor_role ? ` (${selectedEntry.actor_role})` : ""}` },
              { label: "Entity", value: `${selectedEntry.entity_type} #${selectedEntry.entity_id}` },
              { label: "Details", value: detailsSummary(selectedEntry.details) },
              { label: "Timestamp", value: formatTimestamp(selectedEntry.created_at) },
            ]}
          />
        )}
      </Modal>
    </div>
  );
}
