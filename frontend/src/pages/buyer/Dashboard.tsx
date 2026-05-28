import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import {
  KpiCard,
  StatusBadge,
  PageHeader,
  LoadingSpinner,
  ErrorState,
  EmptyState,
  Modal,
  FilterChips,
} from "@/components/ui";
import { formatTimeRemaining } from "@/lib/format";
import type { RfxSummary, Vendor, RfxStatus } from "@/types";

/* ------------------------------------------------------------------ */
/* Filter options                                                       */
/* ------------------------------------------------------------------ */

const STATUS_FILTER_OPTIONS = [
  { label: "All", value: "all" },
  { label: "Drafting", value: "drafting" },
  { label: "Dispatched", value: "dispatched" },
  { label: "Collecting", value: "collecting" },
  { label: "Comparing", value: "comparing" },
  { label: "Awarded", value: "awarded" },
  { label: "Cancelled", value: "cancelled" },
];

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function BuyerDashboard() {
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedRfx, setSelectedRfx] = useState<RfxSummary | null>(null);

  const {
    data: rfxList = [],
    isLoading: rfxLoading,
    error: rfxError,
  } = useQuery<RfxSummary[]>({
    queryKey: ["buyer", "rfx"],
    queryFn: () => api.get<RfxSummary[]>("/api/buyer/rfx"),
  });

  const {
    data: vendors = [],
    isLoading: vendorsLoading,
    error: vendorsError,
  } = useQuery<Vendor[]>({
    queryKey: ["buyer", "vendors"],
    queryFn: () => api.get<Vendor[]>("/api/buyer/vendors"),
  });

  const isLoading = rfxLoading || vendorsLoading;
  const error = rfxError || vendorsError;

  /* KPI derivation */
  const openRfx = rfxList.filter(
    (r) => r.status !== "awarded" && r.status !== "cancelled",
  ).length;
  const awaitingQuotes = rfxList.filter(
    (r) => r.status === "collecting" || r.status === "dispatched",
  ).length;
  const awardedToday = rfxList.filter((r) => {
    if (r.status !== "awarded") return false;
    const created = new Date(r.created_at).toDateString();
    return created === new Date().toDateString();
  }).length;
  const vendorCount = vendors.length;

  /* Filtered RFx list */
  const filteredRfx =
    statusFilter === "all"
      ? rfxList
      : rfxList.filter((r) => r.status === (statusFilter as RfxStatus));

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Dashboard"
        subtitle="Procurement overview and active RFx summary."
        actions={
          <Link
            to="/buyer/chat"
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
          >
            Draft New Request
          </Link>
        }
      />

      {/* Loading State */}
      {isLoading && <LoadingSpinner message="Loading dashboard..." />}

      {/* Error State */}
      {error && !isLoading && (
        <ErrorState message="Failed to load dashboard data. Please try again." />
      )}

      {/* KPI Cards */}
      {!isLoading && !error && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard label="Open RFx" value={openRfx} accent="text-indigo-400" />
            <KpiCard label="Awaiting Quotes" value={awaitingQuotes} accent="text-amber-400" />
            <KpiCard label="Awarded Today" value={awardedToday} accent="text-green-400" />
            <KpiCard label="Vendors" value={vendorCount} />
          </div>

          {/* RFx Section */}
          <div>
            <h2 className="mb-3 text-sm font-medium text-zinc-400">
              Active Requests
            </h2>

            <FilterChips
              options={STATUS_FILTER_OPTIONS}
              active={statusFilter}
              onChange={setStatusFilter}
            />

            {filteredRfx.length === 0 ? (
              <div className="mt-3">
                <EmptyState
                  title="No RFx found"
                  description={
                    statusFilter !== "all"
                      ? "No RFx match the selected filter."
                      : "Start by drafting a new procurement request."
                  }
                  action={
                    statusFilter !== "all"
                      ? { label: "Clear filter", onClick: () => setStatusFilter("all") }
                      : { label: "Draft your first request", to: "/buyer/chat" }
                  }
                />
              </div>
            ) : (
              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {filteredRfx.map((rfx) => (
                  <button
                    key={rfx.id}
                    type="button"
                    onClick={() => setSelectedRfx(rfx)}
                    className="group rounded-xl border border-zinc-800 bg-zinc-900 p-4 text-left transition-all duration-200 hover:border-zinc-700 hover:bg-zinc-800/50 hover:shadow-lg hover:shadow-black/20"
                  >
                    <div className="flex items-start justify-between">
                      <h3 className="text-sm font-medium text-zinc-200 group-hover:text-zinc-100 truncate pr-3">
                        {rfx.title}
                      </h3>
                      <StatusBadge status={rfx.status} variant="rfx" />
                    </div>
                    {rfx.line_items && rfx.line_items.length > 0 && (
                      <p className="mt-1.5 text-xs text-zinc-600">
                        {rfx.line_items.length} line item{rfx.line_items.length > 1 ? "s" : ""}
                      </p>
                    )}
                    <div className="mt-3 flex items-center gap-3 text-xs text-zinc-500">
                      <span className="flex items-center gap-1">
                        <svg className="h-3 w-3 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
                        </svg>
                        {rfx.vendor_count} {rfx.vendor_count === 1 ? "vendor" : "vendors"}
                      </span>
                      <span className="h-3 w-px bg-zinc-800" />
                      <span className="flex items-center gap-1">
                        <svg className="h-3 w-3 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {formatTimeRemaining(rfx.deadline)}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* Quick-View Modal */}
      <Modal
        open={!!selectedRfx}
        onClose={() => setSelectedRfx(null)}
        title={selectedRfx?.title ?? "RFx Details"}
        size="md"
      >
        {selectedRfx && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-zinc-500">Status</label>
                <div className="mt-1">
                  <StatusBadge status={selectedRfx.status} variant="rfx" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500">Vendors</label>
                <p className="mt-1 text-sm text-zinc-200">
                  {selectedRfx.vendor_count}{" "}
                  {selectedRfx.vendor_count === 1 ? "vendor" : "vendors"}
                </p>
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500">Deadline</label>
                <p className="mt-1 text-sm text-zinc-200">
                  {selectedRfx.deadline
                    ? new Date(selectedRfx.deadline).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                        hour: "numeric",
                        minute: "2-digit",
                      })
                    : "No deadline"}
                </p>
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500">Time Remaining</label>
                <p className="mt-1 text-sm text-zinc-200">
                  {formatTimeRemaining(selectedRfx.deadline)}
                </p>
              </div>
            </div>
            <div className="flex justify-end pt-2">
              <Link
                to={`/buyer/rfx/${selectedRfx.id}`}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
              >
                View Full Details
              </Link>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
