import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import {
  StatusBadge,
  PageHeader,
  LoadingSpinner,
  ErrorState,
  EmptyState,
  FilterChips,
} from "@/components/ui";
import { formatDate, formatCountdown } from "@/lib/format";
import { useDebounce } from "@/hooks/useDebounce";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type InboxStatus = "invited" | "viewed" | "quoted" | "declined" | "expired";
type SortKey = "deadline" | "dispatched" | "status";

interface InboxItem {
  rfx_id: string;
  title: string;
  buyer_name?: string;
  status: InboxStatus;
  rfx_status?: string;
  dispatched_at: string;
  deadline: string;
  item_count?: number;
}

/* ------------------------------------------------------------------ */
/* Constants                                                           */
/* ------------------------------------------------------------------ */

const FILTER_OPTIONS = [
  { label: "All", value: "all" },
  { label: "Invited", value: "invited" },
  { label: "Viewed", value: "viewed" },
  { label: "Quoted", value: "quoted" },
  { label: "Declined", value: "declined" },
  { label: "Expired", value: "expired" },
];

const SORT_OPTIONS: { label: string; value: SortKey }[] = [
  { label: "Deadline (soonest)", value: "deadline" },
  { label: "Recently dispatched", value: "dispatched" },
  { label: "Status", value: "status" },
];

const STATUS_ORDER: Record<InboxStatus, number> = {
  invited: 0,
  viewed: 1,
  quoted: 2,
  declined: 3,
  expired: 4,
};

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function isUrgent(deadline: string): boolean {
  if (!deadline) return false;
  const diff = new Date(deadline).getTime() - Date.now();
  if (isNaN(diff) || diff <= 0) return true;
  return diff <= 24 * 60 * 60 * 1000;
}

function isWarning(deadline: string): boolean {
  if (!deadline) return false;
  const diff = new Date(deadline).getTime() - Date.now();
  if (isNaN(diff) || diff <= 0) return true;
  return diff <= 48 * 60 * 60 * 1000;
}

function urgencyLevel(deadline: string): "critical" | "warning" | "normal" {
  if (isUrgent(deadline)) return "critical";
  if (isWarning(deadline)) return "warning";
  return "normal";
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function VendorInbox() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortKey>("deadline");

  const debouncedSearch = useDebounce(searchQuery, 300);

  const { data, isLoading, error, refetch } = useQuery<InboxItem[]>({
    queryKey: ["vendor", "inbox"],
    queryFn: () => api.get<InboxItem[]>("/api/vendor/inbox"),
  });

  const processedData = useMemo(() => {
    if (!data) return [];

    let items = data;

    // Filter by status
    if (statusFilter !== "all") {
      items = items.filter((item) => item.status === statusFilter);
    }

    // Filter by search query
    if (debouncedSearch.trim()) {
      const query = debouncedSearch.toLowerCase();
      items = items.filter((item) =>
        item.title.toLowerCase().includes(query),
      );
    }

    // Sort
    const sorted = [...items];
    sorted.sort((a, b) => {
      switch (sortBy) {
        case "deadline":
          return (
            new Date(a.deadline).getTime() - new Date(b.deadline).getTime()
          );
        case "dispatched":
          return (
            new Date(b.dispatched_at).getTime() -
            new Date(a.dispatched_at).getTime()
          );
        case "status":
          return STATUS_ORDER[a.status] - STATUS_ORDER[b.status];
        default:
          return 0;
      }
    });

    return sorted;
  }, [data, statusFilter, debouncedSearch, sortBy]);

  const hasActiveFilters =
    statusFilter !== "all" || debouncedSearch.trim().length > 0;

  return (
    <div className="p-6">
      <PageHeader
        title="Inbox"
        subtitle="Active RFx invitations and conversation threads."
      />

      {/* Search input */}
      <div className="mt-6 mb-3">
        <div className="relative">
          <svg
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
            />
          </svg>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search RFx by title..."
            data-testid="inbox-search"
            className="w-full rounded-lg border border-zinc-800 bg-zinc-900 py-2 pl-9 pr-3 text-sm text-zinc-100 placeholder-zinc-500 outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* Filter chips and sort controls */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <FilterChips
          options={FILTER_OPTIONS}
          active={statusFilter}
          onChange={setStatusFilter}
        />

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as SortKey)}
          data-testid="inbox-sort"
          className="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs text-zinc-300 outline-none transition focus:border-indigo-500"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {isLoading && <LoadingSpinner message="Loading inbox..." />}

      {error && (
        <ErrorState
          message={`Failed to load inbox. ${error instanceof Error ? error.message : "Please try again."}`}
          onRetry={() => refetch()}
        />
      )}

      {data && data.length === 0 && (
        <EmptyState
          icon={
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21.75 9v.906a2.25 2.25 0 01-1.183 1.981l-6.478 3.488M2.25 9v.906a2.25 2.25 0 001.183 1.981l6.478 3.488m8.839 2.51l-4.66-2.51m0 0l-1.023-.55a2.25 2.25 0 00-2.134 0l-1.022.55m0 0l-4.661 2.51"
              />
            </svg>
          }
          title="No RFx invitations yet."
          description="Complete your profile to appear in buyer searches."
        />
      )}

      {data && data.length > 0 && processedData.length === 0 && (
        <EmptyState
          title="No RFx matches your filters."
          description="Try adjusting your search or selecting a different status filter."
        />
      )}

      {processedData.length > 0 && (
        <div className="space-y-2" data-testid="inbox-list">
          {processedData.map((item) => {
            const countdown = formatCountdown(item.deadline);
            const urgency = urgencyLevel(item.deadline);
            const isUnread = item.status === "invited";

            return (
              <button
                key={item.rfx_id}
                onClick={() => navigate(`/vendor/rfx/${item.rfx_id}`)}
                data-testid="inbox-item"
                className={`flex w-full items-center gap-4 rounded-lg border px-5 py-4 text-left transition-all duration-200 hover:bg-zinc-800/60 hover:shadow-md hover:shadow-black/10 ${
                  urgency === "critical"
                    ? "border-red-800/60 bg-red-950/20 hover:border-red-700/60"
                    : urgency === "warning"
                      ? "border-amber-800/50 bg-amber-950/10 hover:border-amber-700/50"
                      : "border-zinc-800 bg-zinc-900 hover:border-zinc-700"
                } ${isUnread ? "border-l-4 border-l-blue-500" : ""}`}
              >
                {/* Unread dot */}
                {isUnread && (
                  <span
                    className="h-2 w-2 shrink-0 rounded-full bg-blue-500"
                    aria-label="Unread"
                  />
                )}

                {/* Title, buyer, and meta */}
                <div className="min-w-0 flex-1">
                  <p
                    className={`truncate text-sm ${
                      isUnread
                        ? "font-semibold text-zinc-100"
                        : "font-medium text-zinc-200"
                    }`}
                  >
                    {item.title}
                  </p>
                  <div className="mt-1 flex items-center gap-2 text-xs text-zinc-500">
                    {item.buyer_name && (
                      <>
                        <span>{item.buyer_name}</span>
                        <span className="text-zinc-700">&middot;</span>
                      </>
                    )}
                    <span>Dispatched {formatDate(item.dispatched_at)}</span>
                    {item.item_count != null && item.item_count > 0 && (
                      <>
                        <span className="text-zinc-700">&middot;</span>
                        <span>
                          {item.item_count}{" "}
                          {item.item_count === 1 ? "item" : "items"}
                        </span>
                      </>
                    )}
                  </div>
                </div>

                {/* Status badge */}
                <div className="flex shrink-0 flex-col items-end gap-1">
                  <StatusBadge status={item.status} variant="lane" />
                  {item.rfx_status &&
                    ["cancelled", "awarded", "expired"].includes(item.rfx_status) && (
                      <span className="rounded-full bg-zinc-700/50 px-2 py-0.5 text-[10px] font-medium text-zinc-400">
                        RFx {item.rfx_status}
                      </span>
                    )}
                </div>

                {/* Deadline / countdown */}
                <div className="shrink-0 text-right">
                  <p className="text-xs text-zinc-500">
                    {formatDate(item.deadline)}
                  </p>
                  <p
                    className={`text-[11px] font-medium ${
                      urgency === "critical"
                        ? "text-red-400"
                        : urgency === "warning"
                          ? "text-amber-400"
                          : "text-zinc-500"
                    }`}
                  >
                    {countdown}
                  </p>
                </div>

                {/* Chevron */}
                <svg
                  className="h-4 w-4 shrink-0 text-zinc-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
