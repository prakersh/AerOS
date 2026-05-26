import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type RfxStatus =
  | "drafting"
  | "dispatched"
  | "collecting"
  | "comparing"
  | "awarded"
  | "cancelled";

interface RfxLineItem {
  sku_code: string;
  sku_name: string;
  qty: number;
  unit: string;
  target_price?: number;
}

interface RfxSummary {
  id: number;
  title: string;
  status: RfxStatus;
  vendor_count: number;
  deadline: string;
  created_at: string;
  line_items?: RfxLineItem[];
}

interface Vendor {
  id: number;
  name: string;
  email: string;
  categories: string;
  performance_score: number;
  kyc_status: string;
  preferred_rank: number;
}

/* ------------------------------------------------------------------ */
/* Status badge palette                                                */
/* ------------------------------------------------------------------ */

const STATUS_STYLES: Record<RfxStatus, string> = {
  drafting: "bg-zinc-700/50 text-zinc-300",
  dispatched: "bg-blue-900/40 text-blue-400",
  collecting: "bg-amber-900/40 text-amber-400",
  comparing: "bg-indigo-900/40 text-indigo-400",
  awarded: "bg-green-900/40 text-green-400",
  cancelled: "bg-red-900/40 text-red-400",
};

function StatusBadge({ status }: { status: RfxStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${STATUS_STYLES[status] ?? "bg-zinc-700/50 text-zinc-300"}`}
    >
      {status}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function timeRemaining(deadline: string): string {
  const diff = new Date(deadline).getTime() - Date.now();
  if (diff <= 0) return "Expired";

  const hours = Math.floor(diff / 3_600_000);
  const minutes = Math.floor((diff % 3_600_000) / 60_000);

  if (hours >= 24) {
    const days = Math.floor(hours / 24);
    return `${days}d ${hours % 24}h left`;
  }
  return `${hours}h ${minutes}m left`;
}

/* ------------------------------------------------------------------ */
/* KPI Card                                                            */
/* ------------------------------------------------------------------ */

interface KpiCardProps {
  label: string;
  value: number;
  accent?: string;
}

function KpiCard({ label, value, accent = "text-zinc-100" }: KpiCardProps) {
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
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function BuyerDashboard() {
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

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100">Dashboard</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Procurement overview and active RFx summary.
          </p>
        </div>
        <Link
          to="/buyer/chat"
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
        >
          Draft New Request
        </Link>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-indigo-500" />
          <span className="ml-3 text-sm text-zinc-500">Loading dashboard...</span>
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <div className="rounded-xl border border-red-800/50 bg-red-900/20 p-4">
          <p className="text-sm text-red-400">
            Failed to load dashboard data. Please try again.
          </p>
        </div>
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

          {/* RFx Tiles */}
          <div>
            <h2 className="mb-3 text-sm font-medium text-zinc-400">
              Active Requests
            </h2>
            {rfxList.length === 0 ? (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-8 text-center">
                <p className="text-sm text-zinc-500">No RFx found.</p>
                <Link
                  to="/buyer/chat"
                  className="mt-2 inline-block text-sm text-indigo-400 hover:text-indigo-300"
                >
                  Draft your first request
                </Link>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {rfxList.map((rfx) => (
                  <Link
                    key={rfx.id}
                    to={`/buyer/rfx/${rfx.id}`}
                    className="group rounded-xl border border-zinc-800 bg-zinc-900 p-4 transition hover:border-zinc-700 hover:bg-zinc-800/70"
                  >
                    <div className="flex items-start justify-between">
                      <h3 className="text-sm font-medium text-zinc-200 group-hover:text-zinc-100 truncate pr-3">
                        {rfx.title}
                      </h3>
                      <StatusBadge status={rfx.status} />
                    </div>
                    <div className="mt-3 flex items-center gap-4 text-xs text-zinc-500">
                      <span>
                        {rfx.vendor_count}{" "}
                        {rfx.vendor_count === 1 ? "vendor" : "vendors"}
                      </span>
                      <span className="text-zinc-700">|</span>
                      <span>{timeRemaining(rfx.deadline)}</span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
