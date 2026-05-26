import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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

type VendorLaneStatus = "invited" | "viewed" | "quoted" | "declined";

interface LineItem {
  id: number;
  sku_code: string;
  sku_name: string;
  qty: number;
  unit: string;
  target_price?: number;
}

interface OfferLineItem {
  line_item_id: number;
  unit_price: number;
  confidence?: number;
}

interface VendorOffer {
  vendor_id: number;
  vendor_name: string;
  status: VendorLaneStatus;
  total_quote?: number;
  lead_time?: string;
  payment_terms?: string;
  decline_reason?: string;
  line_items?: OfferLineItem[];
}

interface RfxDetail {
  id: number;
  title: string;
  status: RfxStatus;
  delivery_window: string;
  deadline: string;
  created_at: string;
  line_items: LineItem[];
  vendor_offers: VendorOffer[];
}

interface AwardDecision {
  line_item_id: number;
  vendor_id: number;
}

/* ------------------------------------------------------------------ */
/* Status badge palette                                                */
/* ------------------------------------------------------------------ */

const RFX_STATUS_STYLES: Record<RfxStatus, string> = {
  drafting: "bg-zinc-700/50 text-zinc-300",
  dispatched: "bg-blue-900/40 text-blue-400",
  collecting: "bg-amber-900/40 text-amber-400",
  comparing: "bg-indigo-900/40 text-indigo-400",
  awarded: "bg-green-900/40 text-green-400",
  cancelled: "bg-red-900/40 text-red-400",
};

const LANE_STATUS_STYLES: Record<VendorLaneStatus, string> = {
  invited: "bg-zinc-700/50 text-zinc-300",
  viewed: "bg-blue-900/40 text-blue-400",
  quoted: "bg-green-900/40 text-green-400",
  declined: "bg-red-900/40 text-red-400",
};

function StatusBadge({ status, styles }: { status: string; styles: Record<string, string> }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${styles[status] ?? "bg-zinc-700/50 text-zinc-300"}`}
    >
      {status}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Confidence dot                                                      */
/* ------------------------------------------------------------------ */

function ConfidenceDot({ confidence }: { confidence?: number }) {
  if (confidence == null) return null;
  let colorClass = "bg-red-500";
  if (confidence >= 0.7) colorClass = "bg-green-500";
  else if (confidence >= 0.5) colorClass = "bg-yellow-500";

  return (
    <span
      className={`ml-1.5 inline-block h-2 w-2 rounded-full ${colorClass}`}
      title={`Confidence: ${(confidence * 100).toFixed(0)}%`}
    />
  );
}

/* ------------------------------------------------------------------ */
/* Countdown hook                                                      */
/* ------------------------------------------------------------------ */

function useCountdown(deadline: string): string {
  const calcRemaining = useCallback((): string => {
    const diff = new Date(deadline).getTime() - Date.now();
    if (diff <= 0) return "Expired";

    const days = Math.floor(diff / 86_400_000);
    const hours = Math.floor((diff % 86_400_000) / 3_600_000);
    const minutes = Math.floor((diff % 3_600_000) / 60_000);
    const seconds = Math.floor((diff % 60_000) / 1_000);

    if (days > 0) return `${days}d ${hours}h ${minutes}m ${seconds}s`;
    return `${hours}h ${minutes}m ${seconds}s`;
  }, [deadline]);

  const [remaining, setRemaining] = useState<string>(() => calcRemaining());

  useEffect(() => {
    const interval = setInterval(() => {
      setRemaining(calcRemaining());
    }, 1_000);
    return () => clearInterval(interval);
  }, [calcRemaining]);

  return remaining;
}

/* ------------------------------------------------------------------ */
/* Cancel Confirmation Modal                                           */
/* ------------------------------------------------------------------ */

function CancelModal({
  open,
  onClose,
  onConfirm,
  isPending,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => void;
  isPending: boolean;
}) {
  const [reason, setReason] = useState("");

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-md rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <h3 className="text-lg font-semibold text-zinc-100">Withdraw RFx</h3>
        <p className="mt-2 text-sm text-zinc-400">
          This will cancel the RFx and notify all vendors. This action cannot be
          undone.
        </p>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Reason for withdrawal..."
          rows={3}
          className="mt-4 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500"
        />
        <div className="mt-4 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 transition hover:bg-zinc-800"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!reason.trim() || isPending}
            onClick={() => onConfirm(reason.trim())}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-500 disabled:opacity-50"
          >
            {isPending ? "Withdrawing..." : "Confirm Withdraw"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Comparison Matrix                                                   */
/* ------------------------------------------------------------------ */

function ComparisonMatrix({
  lineItems,
  vendorOffers,
  awards,
  onToggleAward,
}: {
  lineItems: LineItem[];
  vendorOffers: VendorOffer[];
  awards: Map<number, number>;
  onToggleAward: (lineItemId: number, vendorId: number) => void;
}) {
  const quotedVendors = vendorOffers.filter((v) => v.status === "quoted");

  if (quotedVendors.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6 text-center">
        <p className="text-sm text-zinc-500">
          No vendor quotes received yet.
        </p>
      </div>
    );
  }

  /** Build a price lookup: lineItemId -> vendorId -> { price, confidence } */
  const priceLookup = new Map<number, Map<number, { price: number; confidence?: number }>>();
  for (const vendor of quotedVendors) {
    for (const ol of vendor.line_items ?? []) {
      if (!priceLookup.has(ol.line_item_id)) {
        priceLookup.set(ol.line_item_id, new Map());
      }
      priceLookup.get(ol.line_item_id)!.set(vendor.vendor_id, {
        price: ol.unit_price,
        confidence: ol.confidence,
      });
    }
  }

  /** Find min/max per line item */
  function priceRangeForItem(lineItemId: number): { min: number; max: number } {
    const vendorPrices = priceLookup.get(lineItemId);
    if (!vendorPrices || vendorPrices.size === 0) return { min: 0, max: 0 };
    const prices = Array.from(vendorPrices.values()).map((v) => v.price);
    return { min: Math.min(...prices), max: Math.max(...prices) };
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-zinc-800">
      <table className="w-full text-sm">
        {/* Header: Vendor names + totals */}
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900">
            <th className="sticky left-0 bg-zinc-900 px-4 py-3 text-left text-xs font-medium text-zinc-400">
              Line Item
            </th>
            {quotedVendors.map((v) => (
              <th
                key={v.vendor_id}
                className="min-w-[160px] px-4 py-3 text-center text-xs font-medium text-zinc-300"
              >
                <div>{v.vendor_name}</div>
                <div className="mt-1 space-y-0.5 text-[10px] text-zinc-500 font-normal">
                  {v.total_quote != null && (
                    <div>Total: {formatCurrency(v.total_quote)}</div>
                  )}
                  {v.lead_time && <div>Lead: {v.lead_time}</div>}
                  {v.payment_terms && <div>Terms: {v.payment_terms}</div>}
                </div>
              </th>
            ))}
          </tr>
        </thead>

        {/* Body: One row per line item */}
        <tbody>
          {lineItems.map((li) => {
            const { min, max } = priceRangeForItem(li.id);
            return (
              <tr
                key={li.id}
                className="border-b border-zinc-800/50 hover:bg-zinc-800/30"
              >
                <td className="sticky left-0 bg-zinc-900 px-4 py-3 text-zinc-300">
                  <div className="font-medium">{li.sku_code}</div>
                  <div className="text-xs text-zinc-500">
                    {li.qty} {li.unit}
                    {li.target_price != null && (
                      <span className="ml-2">
                        target {formatCurrency(li.target_price)}
                      </span>
                    )}
                  </div>
                </td>
                {quotedVendors.map((v) => {
                  const entry = priceLookup.get(li.id)?.get(v.vendor_id);
                  const isAwarded = awards.get(li.id) === v.vendor_id;

                  let cellBg = "";
                  if (entry && min !== max) {
                    if (entry.price === min) cellBg = "bg-green-900/20";
                    else if (entry.price === max) cellBg = "bg-red-900/15";
                  }

                  return (
                    <td
                      key={v.vendor_id}
                      className={`px-4 py-3 text-center ${cellBg}`}
                    >
                      {entry ? (
                        <div className="flex flex-col items-center gap-1.5">
                          <span className="text-zinc-200 font-medium tabular-nums">
                            {formatCurrency(entry.price)}
                            <ConfidenceDot confidence={entry.confidence} />
                          </span>
                          <button
                            type="button"
                            onClick={() => onToggleAward(li.id, v.vendor_id)}
                            className={`rounded px-2.5 py-1 text-[11px] font-medium transition ${
                              isAwarded
                                ? "bg-green-600 text-white"
                                : "border border-zinc-700 text-zinc-400 hover:border-indigo-500 hover:text-indigo-400"
                            }`}
                          >
                            {isAwarded ? "Awarded" : "Award"}
                          </button>
                        </div>
                      ) : (
                        <span className="text-zinc-600">--</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(amount);
}

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function RFxDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [awards, setAwards] = useState<Map<number, number>>(new Map());

  const {
    data: rfx,
    isLoading,
    error,
  } = useQuery<RfxDetail>({
    queryKey: ["buyer", "rfx", id],
    queryFn: () => api.get<RfxDetail>(`/api/buyer/rfx/${id}`),
    enabled: !!id,
  });

  const countdown = useCountdown(rfx?.deadline ?? new Date().toISOString());

  /* Award mutation */
  const awardMutation = useMutation({
    mutationFn: (decisions: AwardDecision[]) =>
      api.post(`/api/buyer/rfx/${id}/award`, { decisions }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["buyer", "rfx", id] });
      queryClient.invalidateQueries({ queryKey: ["buyer", "rfx"] });
    },
  });

  /* Cancel mutation */
  const cancelMutation = useMutation({
    mutationFn: (reason: string) =>
      api.post(`/api/buyer/rfx/${id}/cancel`, { reason }),
    onSuccess: () => {
      setCancelModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ["buyer", "rfx", id] });
      queryClient.invalidateQueries({ queryKey: ["buyer", "rfx"] });
    },
  });

  /** Toggle award for a specific line item + vendor */
  function handleToggleAward(lineItemId: number, vendorId: number): void {
    setAwards((prev) => {
      const next = new Map(prev);
      if (next.get(lineItemId) === vendorId) {
        next.delete(lineItemId);
      } else {
        next.set(lineItemId, vendorId);
      }
      return next;
    });
  }

  /** Submit all awards */
  function handleSubmitAwards(): void {
    const decisions: AwardDecision[] = Array.from(awards.entries()).map(
      ([line_item_id, vendor_id]) => ({ line_item_id, vendor_id }),
    );
    awardMutation.mutate(decisions);
  }

  /* Loading */
  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-16">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-indigo-500" />
        <span className="ml-3 text-sm text-zinc-500">Loading RFx...</span>
      </div>
    );
  }

  /* Error */
  if (error || !rfx) {
    return (
      <div className="p-6">
        <div className="rounded-xl border border-red-800/50 bg-red-900/20 p-4">
          <p className="text-sm text-red-400">Failed to load RFx details.</p>
          <button
            type="button"
            onClick={() => navigate("/buyer/dashboard")}
            className="mt-2 text-sm text-indigo-400 hover:text-indigo-300"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const quotedVendors = rfx.vendor_offers.filter((v) => v.status === "quoted");
  const declinedVendors = rfx.vendor_offers.filter((v) => v.status === "declined");
  const isCancelledOrAwarded =
    rfx.status === "cancelled" || rfx.status === "awarded";

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-zinc-100">{rfx.title}</h1>
            <StatusBadge status={rfx.status} styles={RFX_STATUS_STYLES} />
          </div>
          <div className="mt-2 flex flex-wrap gap-4 text-xs text-zinc-500">
            <span>Delivery: {rfx.delivery_window}</span>
            <span className="text-zinc-700">|</span>
            <span className="tabular-nums">Deadline: {countdown}</span>
          </div>
        </div>
        {!isCancelledOrAwarded && (
          <button
            type="button"
            onClick={() => setCancelModalOpen(true)}
            className="rounded-lg border border-red-800/50 px-4 py-2 text-sm font-medium text-red-400 transition hover:bg-red-900/20"
          >
            Withdraw RFx
          </button>
        )}
      </div>

      {/* Line Items Table */}
      <section>
        <h2 className="mb-3 text-sm font-medium text-zinc-400">Line Items</h2>
        <div className="overflow-x-auto rounded-xl border border-zinc-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900">
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400">
                  SKU
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-zinc-400">
                  Qty
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400">
                  Unit
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-zinc-400">
                  Target Price
                </th>
              </tr>
            </thead>
            <tbody>
              {rfx.line_items.map((li) => (
                <tr
                  key={li.id}
                  className="border-b border-zinc-800/50 hover:bg-zinc-800/30"
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-zinc-200">{li.sku_code}</div>
                    <div className="text-xs text-zinc-500">{li.sku_name}</div>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-zinc-300">
                    {li.qty}
                  </td>
                  <td className="px-4 py-3 text-zinc-400">{li.unit}</td>
                  <td className="px-4 py-3 text-right tabular-nums text-zinc-300">
                    {li.target_price != null
                      ? formatCurrency(li.target_price)
                      : "--"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Vendor Lanes */}
      <section>
        <h2 className="mb-3 text-sm font-medium text-zinc-400">
          Vendor Responses
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {rfx.vendor_offers.map((vendor) => (
            <div
              key={vendor.vendor_id}
              className="rounded-xl border border-zinc-800 bg-zinc-900 p-4"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-zinc-200">
                  {vendor.vendor_name}
                </span>
                <StatusBadge status={vendor.status} styles={LANE_STATUS_STYLES} />
              </div>
              {vendor.status === "quoted" && (
                <div className="mt-3 space-y-1 text-xs text-zinc-400">
                  {vendor.total_quote != null && (
                    <p>
                      Total:{" "}
                      <span className="text-zinc-200">
                        {formatCurrency(vendor.total_quote)}
                      </span>
                    </p>
                  )}
                  {vendor.lead_time && (
                    <p>
                      Lead Time:{" "}
                      <span className="text-zinc-200">{vendor.lead_time}</span>
                    </p>
                  )}
                  {vendor.payment_terms && (
                    <p>
                      Terms:{" "}
                      <span className="text-zinc-200">{vendor.payment_terms}</span>
                    </p>
                  )}
                </div>
              )}
              {vendor.status === "declined" && vendor.decline_reason && (
                <div className="mt-3 rounded-lg border border-red-800/30 bg-red-900/10 px-3 py-2">
                  <p className="text-xs text-red-400">
                    Declined: {vendor.decline_reason}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Comparison Matrix */}
      {quotedVendors.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-medium text-zinc-400">
            Comparison Matrix
          </h2>
          <ComparisonMatrix
            lineItems={rfx.line_items}
            vendorOffers={rfx.vendor_offers}
            awards={awards}
            onToggleAward={handleToggleAward}
          />
          {!isCancelledOrAwarded && awards.size > 0 && (
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={handleSubmitAwards}
                disabled={awardMutation.isPending}
                className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
              >
                {awardMutation.isPending
                  ? "Awarding..."
                  : `Award Selected (${awards.size})`}
              </button>
            </div>
          )}
          {awardMutation.isError && (
            <p className="mt-2 text-sm text-red-400">
              Failed to submit awards. Please try again.
            </p>
          )}
          {awardMutation.isSuccess && (
            <p className="mt-2 text-sm text-green-400">
              Awards submitted successfully.
            </p>
          )}
        </section>
      )}

      {/* Declined vendors detail */}
      {declinedVendors.length > 0 && quotedVendors.length === 0 && (
        <section>
          <h2 className="mb-3 text-sm font-medium text-zinc-400">
            Declined Vendors
          </h2>
          <div className="space-y-2">
            {declinedVendors.map((v) => (
              <div
                key={v.vendor_id}
                className="rounded-xl border border-red-800/30 bg-red-900/10 p-4"
              >
                <p className="text-sm font-medium text-zinc-300">
                  {v.vendor_name}
                </p>
                {v.decline_reason && (
                  <p className="mt-1 text-xs text-red-400">
                    {v.decline_reason}
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Cancel Modal */}
      <CancelModal
        open={cancelModalOpen}
        onClose={() => setCancelModalOpen(false)}
        onConfirm={(reason) => cancelMutation.mutate(reason)}
        isPending={cancelMutation.isPending}
      />
    </div>
  );
}
