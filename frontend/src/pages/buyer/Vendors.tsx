import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type KycStatus = "approved" | "pending" | "rejected";

interface Vendor {
  id: number;
  name: string;
  primary_email: string;
  category_ids_csv: string;
  performance_score: number;
  kyc_status: KycStatus;
  preferred_rank: number;
}

/* ------------------------------------------------------------------ */
/* KYC badge palette                                                   */
/* ------------------------------------------------------------------ */

const KYC_STYLES: Record<KycStatus, string> = {
  approved: "bg-green-900/40 text-green-400",
  pending: "bg-amber-900/40 text-amber-400",
  rejected: "bg-red-900/40 text-red-400",
};

function KycBadge({ status }: { status: KycStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${KYC_STYLES[status] ?? "bg-zinc-700/50 text-zinc-400"}`}
    >
      {status}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Star Rating                                                         */
/* ------------------------------------------------------------------ */

function StarRating({ score }: { score: number }) {
  const fullStars = Math.floor(score);
  const hasHalf = score - fullStars >= 0.5;
  const emptyStars = 5 - fullStars - (hasHalf ? 1 : 0);

  return (
    <div className="flex items-center gap-0.5" title={`${score.toFixed(1)} / 5`}>
      {Array.from({ length: fullStars }).map((_, i) => (
        <StarFull key={`full-${i}`} />
      ))}
      {hasHalf && <StarHalf />}
      {Array.from({ length: emptyStars }).map((_, i) => (
        <StarEmpty key={`empty-${i}`} />
      ))}
      <span className="ml-1.5 text-xs tabular-nums text-zinc-400">
        {score.toFixed(1)}
      </span>
    </div>
  );
}

function StarFull() {
  return (
    <svg
      className="h-4 w-4 text-amber-400"
      fill="currentColor"
      viewBox="0 0 20 20"
    >
      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
    </svg>
  );
}

function StarHalf() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20">
      <defs>
        <linearGradient id="half-grad">
          <stop offset="50%" stopColor="currentColor" className="text-amber-400" />
          <stop offset="50%" stopColor="currentColor" className="text-zinc-700" />
        </linearGradient>
      </defs>
      <path
        fill="url(#half-grad)"
        d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
      />
    </svg>
  );
}

function StarEmpty() {
  return (
    <svg
      className="h-4 w-4 text-zinc-700"
      fill="currentColor"
      viewBox="0 0 20 20"
    >
      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function Vendors() {
  const {
    data: vendors = [],
    isLoading,
    error,
  } = useQuery<Vendor[]>({
    queryKey: ["buyer", "vendors"],
    queryFn: () => api.get<Vendor[]>("/api/buyer/vendors"),
  });

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100">Vendors</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Vendor directory and performance tracking.
        </p>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-indigo-500" />
          <span className="ml-3 text-sm text-zinc-500">Loading vendors...</span>
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <div className="rounded-xl border border-red-800/50 bg-red-900/20 p-4">
          <p className="text-sm text-red-400">
            Failed to load vendors. Please try again.
          </p>
        </div>
      )}

      {/* Vendor Cards Grid */}
      {!isLoading && !error && (
        <>
          {vendors.length === 0 ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-8 text-center">
              <p className="text-sm text-zinc-500">No vendors found.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {vendors.map((vendor) => (
                <div
                  key={vendor.id}
                  className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 transition hover:border-zinc-700"
                >
                  {/* Name + KYC */}
                  <div className="flex items-start justify-between">
                    <div className="min-w-0">
                      <h3 className="truncate text-sm font-medium text-zinc-200">
                        {vendor.name}
                      </h3>
                      <p className="mt-0.5 truncate text-xs text-zinc-500">
                        {vendor.primary_email}
                      </p>
                    </div>
                    <KycBadge status={vendor.kyc_status} />
                  </div>

                  {/* Categories */}
                  <div className="mt-3">
                    <div className="flex flex-wrap gap-1.5">
                      {(vendor.category_ids_csv || "").split(",").filter(Boolean).map((catId) => (
                        <span
                          key={catId.trim()}
                          className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-400"
                        >
                          Category {catId.trim()}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Score + Rank */}
                  <div className="mt-4 flex items-center justify-between">
                    <StarRating score={vendor.performance_score} />
                    <span className="rounded bg-zinc-800 px-2 py-0.5 text-[10px] font-medium text-zinc-500">
                      Rank #{vendor.preferred_rank}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
