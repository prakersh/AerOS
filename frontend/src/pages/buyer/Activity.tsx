import { useState } from "react";
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
import type { ActivityEntry } from "@/types";

/* ------------------------------------------------------------------ */
/* Filter options                                                       */
/* ------------------------------------------------------------------ */

const ACTION_FILTER_OPTIONS = [
  { label: "All", value: "all" },
  { label: "Create RFx", value: "create_rfx" },
  { label: "Dispatch RFx", value: "dispatch_rfx" },
  { label: "Award RFx", value: "award_rfx" },
  { label: "Cancel RFx", value: "cancel_rfx" },
];

/* ------------------------------------------------------------------ */
/* Styles (page-specific)                                               */
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

/* ------------------------------------------------------------------ */
/* Action label (page-specific logic)                                  */
/* ------------------------------------------------------------------ */

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

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function Activity() {
  const [actionFilter, setActionFilter] = useState("all");
  const [selectedEntry, setSelectedEntry] = useState<ActivityEntry | null>(null);

  const { data: entries = [], isLoading, error } = useQuery<ActivityEntry[]>({
    queryKey: ["buyer", "activity"],
    queryFn: () => api.get<ActivityEntry[]>("/api/buyer/activity"),
  });

  /* Filtered entries */
  const filteredEntries =
    actionFilter === "all"
      ? entries
      : entries.filter((e) => e.action === actionFilter);

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Activity"
        subtitle="Recent actions and event timeline."
      />

      {isLoading && <LoadingSpinner message="Loading activity..." />}

      {error && !isLoading && (
        <ErrorState message="Failed to load activity." />
      )}

      {!isLoading && !error && (
        <FilterChips
          options={ACTION_FILTER_OPTIONS}
          active={actionFilter}
          onChange={setActionFilter}
        />
      )}

      {!isLoading && !error && filteredEntries.length === 0 && (
        <EmptyState
          title="No activity found"
          description={
            actionFilter !== "all"
              ? "No activity matches the selected filter."
              : "No activity yet. Start by drafting an RFx."
          }
          action={
            actionFilter !== "all"
              ? { label: "Clear filter", onClick: () => setActionFilter("all") }
              : { label: "Draft your first request", to: "/buyer/chat" }
          }
        />
      )}

      {!isLoading && !error && filteredEntries.length > 0 && (
        <div className="space-y-2">
          {filteredEntries.map((entry) => {
            const borderClass = ACTION_BORDER[entry.action] ?? "border-l-zinc-700";
            const iconPath = ACTION_ICON[entry.action] ?? "M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z";
            return (
              <button
                key={entry.id}
                type="button"
                onClick={() => setSelectedEntry(entry)}
                className={`flex w-full items-start gap-4 rounded-lg border border-zinc-800 border-l-4 bg-zinc-900 px-4 py-3 text-left transition-all duration-200 hover:bg-zinc-800/50 hover:shadow-md hover:shadow-black/10 ${borderClass}`}
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
              </button>
            );
          })}
        </div>
      )}

      {/* Activity Detail Modal */}
      <Modal
        open={!!selectedEntry}
        onClose={() => setSelectedEntry(null)}
        title="Activity Details"
        size="md"
      >
        {selectedEntry && (
          <DetailView
            items={[
              { label: "Action", value: selectedEntry.action.replace(/_/g, " ") },
              { label: "Description", value: actionLabel(selectedEntry) },
              { label: "Entity Type", value: selectedEntry.entity_type },
              { label: "Entity ID", value: selectedEntry.entity_id },
              {
                label: "Details",
                value: Object.keys(selectedEntry.details).length > 0
                  ? JSON.stringify(selectedEntry.details, null, 2)
                  : "--",
              },
              { label: "Timestamp", value: formatTimestamp(selectedEntry.created_at) },
            ]}
            columns={2}
          />
        )}
      </Modal>
    </div>
  );
}
