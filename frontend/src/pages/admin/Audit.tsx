import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface AuditEntry {
  id: number;
  created_at: string;
  actor_name: string;
  actor_role: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, unknown>;
}

/* ------------------------------------------------------------------ */
/* Badge styles                                                        */
/* ------------------------------------------------------------------ */

const ACTION_COLORS: Record<string, string> = {
  create_rfx: "bg-indigo-900/40 text-indigo-400",
  dispatch_rfx: "bg-blue-900/40 text-blue-400",
  award_rfx: "bg-emerald-900/40 text-emerald-400",
  cancel_rfx: "bg-red-900/40 text-red-400",
  override_offer_field: "bg-amber-900/40 text-amber-400",
};

function formatTimestamp(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

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
  const { data: logs = [], isLoading, error } = useQuery<AuditEntry[]>({
    queryKey: ["admin", "audit"],
    queryFn: () => api.get<AuditEntry[]>("/api/admin/audit"),
  });

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100">Audit Log</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Complete record of all system actions.
        </p>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-indigo-500" />
          <span className="ml-3 text-sm text-zinc-500">Loading audit log...</span>
        </div>
      )}

      {error && !isLoading && (
        <div className="rounded-xl border border-red-800/50 bg-red-900/20 p-4">
          <p className="text-sm text-red-400">Failed to load audit log.</p>
        </div>
      )}

      {!isLoading && !error && (
        <div className="overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-900">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-800">
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Timestamp
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Actor
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Action
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Entity
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Details
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              {logs.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-zinc-600">
                    No audit entries yet.
                  </td>
                </tr>
              )}
              {logs.map((entry) => (
                <tr
                  key={entry.id}
                  className="transition hover:bg-zinc-800/40"
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
        {logs.length} {logs.length === 1 ? "entry" : "entries"} recorded.
      </p>
    </div>
  );
}
