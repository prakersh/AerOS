import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface ActivityEntry {
  id: number;
  action: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, unknown>;
  created_at: string;
}

/* ------------------------------------------------------------------ */
/* Styles                                                              */
/* ------------------------------------------------------------------ */

const ACTION_BORDER: Record<string, string> = {
  create_rfx: "border-l-indigo-500",
  dispatch_rfx: "border-l-blue-500",
  award_rfx: "border-l-emerald-500",
  cancel_rfx: "border-l-red-500",
  override_offer_field: "border-l-amber-500",
};

const ACTION_ICON: Record<string, string> = {
  create_rfx: "M12 4v16m8-8H4",
  dispatch_rfx: "M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5",
  award_rfx: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  cancel_rfx: "M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
};

function actionLabel(entry: ActivityEntry): string {
  const d = entry.details;
  switch (entry.action) {
    case "create_rfx":
      return `Created RFx "${d.title ?? `#${entry.entity_id}`}"`;
    case "dispatch_rfx":
      return `Dispatched RFx #${entry.entity_id} to ${d.vendor_count ?? "?"} vendors`;
    case "award_rfx":
      return `Awarded RFx #${entry.entity_id} (${d.decisions_count ?? "?"} decisions)`;
    case "cancel_rfx":
      return `Cancelled RFx #${entry.entity_id}`;
    case "override_offer_field":
      return `Overrode ${d.field} on Offer #${entry.entity_id}`;
    default:
      return `${entry.action.replace(/_/g, " ")} — ${entry.entity_type} #${entry.entity_id}`;
  }
}

function formatTimestamp(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 60_000) return "Just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function Activity() {
  const { data: entries = [], isLoading, error } = useQuery<ActivityEntry[]>({
    queryKey: ["buyer", "activity"],
    queryFn: () => api.get<ActivityEntry[]>("/api/buyer/activity"),
  });

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100">Activity</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Recent actions and event timeline.
        </p>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-indigo-500" />
          <span className="ml-3 text-sm text-zinc-500">Loading activity...</span>
        </div>
      )}

      {error && !isLoading && (
        <div className="rounded-xl border border-red-800/50 bg-red-900/20 p-4">
          <p className="text-sm text-red-400">Failed to load activity.</p>
        </div>
      )}

      {!isLoading && !error && entries.length === 0 && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-8 text-center">
          <p className="text-sm text-zinc-500">No activity yet. Start by drafting an RFx.</p>
        </div>
      )}

      {!isLoading && !error && entries.length > 0 && (
        <div className="space-y-2">
          {entries.map((entry) => {
            const borderClass = ACTION_BORDER[entry.action] ?? "border-l-zinc-700";
            const iconPath = ACTION_ICON[entry.action] ?? "M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z";
            return (
              <div
                key={entry.id}
                className={`flex items-start gap-4 rounded-lg border border-zinc-800 border-l-4 bg-zinc-900 px-4 py-3 ${borderClass}`}
              >
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-zinc-800">
                  <svg className="h-4 w-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d={iconPath} />
                  </svg>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-zinc-200">{actionLabel(entry)}</p>
                  <p className="mt-0.5 text-xs text-zinc-500">
                    {entry.entity_type} #{entry.entity_id}
                  </p>
                </div>
                <span className="shrink-0 text-[11px] tabular-nums text-zinc-600">
                  {formatTimestamp(entry.created_at)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
