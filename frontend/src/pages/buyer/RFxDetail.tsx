import { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import {
  StatusBadge,
  Modal,
  ConfirmDialog,
  LoadingSpinner,
  ErrorState,
  LifecycleStepper,
  PageHeader,
  showToast,
} from "@/components/ui";
import { formatCurrency, formatTimeRemaining } from "@/lib/format";
import type { RfxStatus } from "@/types";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type VendorLaneStatus = "invited" | "viewed" | "quoted" | "declined" | "expired";

interface LineItem {
  id: number;
  sku_code: string;
  sku_name: string;
  qty: number;
  unit: string;
  target_price?: number;
  notes?: string;
}

interface OfferLineItem {
  line_item_id: number;
  unit_price: number;
  confidence?: number;
}

interface UnmappedItem {
  name: string;
  unit_price?: number | null;
  qty?: number | null;
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
  unmapped_items?: UnmappedItem[];
  assigned_line_item_ids?: number[] | null;
}

interface RfxDetail {
  id: number;
  title: string;
  status: RfxStatus;
  delivery_window: string;
  deadline: string;
  created_at: string;
  payment_terms?: string;
  delivery_terms?: string;
  currency?: string;
  tax_treatment?: string;
  notes_for_vendors?: string;
  line_items: LineItem[];
  vendor_offers: VendorOffer[];
}

interface AwardDecision {
  line_item_id: number;
  vendor_id: number;
  unit_price?: number;
  qty?: number;
}

interface VendorSuggestion {
  vendor_id: number;
  vendor_name: string;
  matching_items: { line_item_id: number; sku_code: string; sku_name: string; qty: number; unit: string }[];
  match_score: number;
  performance_score: number;
}

interface Assignment {
  vendor_id: number;
  line_item_ids: number[];
}

/* ------------------------------------------------------------------ */
/* Lifecycle steps                                                     */
/* ------------------------------------------------------------------ */

const LIFECYCLE_STEPS = [
  { key: "drafting", label: "Drafting", description: "RFx is being prepared" },
  { key: "dispatched", label: "Dispatched", description: "Sent to vendors" },
  { key: "collecting", label: "Collecting", description: "Gathering vendor responses" },
  { key: "comparing", label: "Comparing", description: "Evaluating quotes" },
  { key: "awarded", label: "Awarded", description: "Vendors selected" },
];

const CANCELLED_STEP = { key: "cancelled", label: "Cancelled", description: "RFx was withdrawn" };

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
    if (!deadline) return "No deadline";
    const diff = new Date(deadline).getTime() - Date.now();
    if (isNaN(diff) || diff <= 0) return "Expired";
    const days = Math.floor(diff / 86_400_000);
    const hours = Math.floor((diff % 86_400_000) / 3_600_000);
    const minutes = Math.floor((diff % 3_600_000) / 60_000);
    const seconds = Math.floor((diff % 60_000) / 1_000);
    if (days > 0) return `${days}d ${hours}h ${minutes}m ${seconds}s`;
    return `${hours}h ${minutes}m ${seconds}s`;
  }, [deadline]);

  const [remaining, setRemaining] = useState(calcRemaining);
  useEffect(() => {
    const interval = setInterval(() => setRemaining(calcRemaining()), 1000);
    return () => clearInterval(interval);
  }, [calcRemaining]);
  return remaining;
}

/* ------------------------------------------------------------------ */
/* Smart Combination Card                                              */
/* ------------------------------------------------------------------ */

function SmartCombination({
  lineItems,
  vendorOffers,
  onApply,
}: {
  lineItems: LineItem[];
  vendorOffers: VendorOffer[];
  onApply: (assignments: Assignment[]) => void;
}) {
  const quotedVendors = vendorOffers.filter((v) => v.status === "quoted");

  const bestCombination = useMemo(() => {
    if (quotedVendors.length === 0) return null;

    // Build price map: lineItemId -> vendorId -> unit_price
    const priceMap = new Map<number, Map<number, number>>();
    for (const v of quotedVendors) {
      for (const ol of v.line_items ?? []) {
        if (!priceMap.has(ol.line_item_id)) priceMap.set(ol.line_item_id, new Map());
        priceMap.get(ol.line_item_id)!.set(v.vendor_id, ol.unit_price);
      }
    }

    // For each item, find the cheapest vendor
    const assignments = new Map<number, { vendor_id: number; vendor_name: string; unit_price: number }>();
    let totalCost = 0;

    for (const item of lineItems) {
      const vendorPrices = priceMap.get(item.id);
      if (!vendorPrices || vendorPrices.size === 0) continue;

      let bestVendorId = 0;
      let bestPrice = Infinity;
      let bestName = "";

      for (const [vId, price] of vendorPrices) {
        if (price < bestPrice) {
          bestPrice = price;
          bestVendorId = vId;
          bestName = quotedVendors.find((v) => v.vendor_id === vId)?.vendor_name ?? "";
        }
      }

      if (bestVendorId > 0) {
        assignments.set(item.id, { vendor_id: bestVendorId, vendor_name: bestName, unit_price: bestPrice });
        totalCost += bestPrice * item.qty;
      }
    }

    return { assignments, totalCost };
  }, [lineItems, quotedVendors]);

  if (!bestCombination || bestCombination.assignments.size === 0) return null;

  // Group by vendor
  const vendorGroups = new Map<number, { name: string; items: { line_item_id: number; sku_code: string; cost: number }[]; total: number }>();
  for (const [itemId, info] of bestCombination.assignments) {
    const item = lineItems.find((li) => li.id === itemId);
    if (!item) continue;
    if (!vendorGroups.has(info.vendor_id)) {
      vendorGroups.set(info.vendor_id, { name: info.vendor_name, items: [], total: 0 });
    }
    const group = vendorGroups.get(info.vendor_id)!;
    group.items.push({ line_item_id: itemId, sku_code: item.sku_code, cost: info.unit_price * item.qty });
    group.total += info.unit_price * item.qty;
  }

  function handleApply() {
    const assignments: Assignment[] = [];
    for (const [vendorId, group] of vendorGroups) {
      assignments.push({ vendor_id: vendorId, line_item_ids: group.items.map((i) => i.line_item_id) });
    }
    onApply(assignments);
  }

  return (
    <div className="rounded-xl border border-indigo-800/50 bg-indigo-900/10 p-5">
      <div className="flex items-center gap-2 mb-3">
        <svg className="h-5 w-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
        </svg>
        <h3 className="text-sm font-semibold text-indigo-300">
          Optimal Combination
        </h3>
        <span className="ml-auto text-lg font-bold text-indigo-200 tabular-nums">
          {formatCurrency(bestCombination.totalCost)}
        </span>
      </div>
      <p className="text-xs text-zinc-400 mb-3">
        Most cost-efficient vendor assignment across {vendorGroups.size} vendor{vendorGroups.size > 1 ? "s" : ""}.
      </p>
      <div className="space-y-2">
        {Array.from(vendorGroups.entries()).map(([vId, group]) => (
          <div key={vId} className="flex items-center gap-3 rounded-lg bg-zinc-800/50 px-3 py-2">
            <span className="text-sm font-medium text-zinc-200">{group.name}</span>
            <span className="text-xs text-zinc-500">
              {group.items.map((i) => i.sku_code).join(", ")}
            </span>
            <span className="ml-auto text-xs tabular-nums text-zinc-400">
              {formatCurrency(group.total)}
            </span>
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={handleApply}
        className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
      >
        Apply This Combination
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Vendor Assignment Panel                                             */
/* ------------------------------------------------------------------ */

function VendorAssignmentPanel({
  lineItems,
  vendorOffers,
  assignments,
  onChange,
  suggestions,
  suggestionsLoading,
}: {
  lineItems: LineItem[];
  vendorOffers: VendorOffer[];
  assignments: Assignment[];
  onChange: (assignments: Assignment[]) => void;
  suggestions: VendorSuggestion[] | null;
  suggestionsLoading: boolean;
}) {
  const availableVendors = vendorOffers.filter(
    (v) => v.status === "invited" || v.status === "viewed" || v.status === "quoted"
  );

  function toggleItemVendor(lineItemId: number, vendorId: number) {
    const existing = assignments.find((a) => a.vendor_id === vendorId);
    let newAssignments = [...assignments];

    if (existing) {
      if (existing.line_item_ids.includes(lineItemId)) {
        existing.line_item_ids = existing.line_item_ids.filter((id) => id !== lineItemId);
        if (existing.line_item_ids.length === 0) {
          newAssignments = newAssignments.filter((a) => a.vendor_id !== vendorId);
        }
      } else {
        existing.line_item_ids = [...existing.line_item_ids, lineItemId];
      }
    } else {
      newAssignments.push({ vendor_id: vendorId, line_item_ids: [lineItemId] });
    }
    onChange(newAssignments);
  }

  function applySuggestion(suggestion: VendorSuggestion) {
    const existing = assignments.find((a) => a.vendor_id === suggestion.vendor_id);
    const newAssignments = assignments.filter((a) => a.vendor_id !== suggestion.vendor_id);
    const itemIds = suggestion.matching_items.map((i) => i.line_item_id);
    if (existing) {
      const merged = new Set([...existing.line_item_ids, ...itemIds]);
      newAssignments.push({ vendor_id: suggestion.vendor_id, line_item_ids: Array.from(merged) });
    } else {
      newAssignments.push({ vendor_id: suggestion.vendor_id, line_item_ids: itemIds });
    }
    onChange(newAssignments);
  }

  function getAssignedVendors(lineItemId: number): number[] {
    return assignments.filter((a) => a.line_item_ids.includes(lineItemId)).map((a) => a.vendor_id);
  }

  return (
    <div className="space-y-4">
      {/* Item-Vendor Matrix */}
      <div className="overflow-x-auto rounded-xl border border-zinc-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900">
              <th className="sticky left-0 bg-zinc-900 px-4 py-3 text-left text-xs font-medium text-zinc-400 z-10">
                Item
              </th>
              {availableVendors.map((v) => (
                <th key={v.vendor_id} className="px-3 py-3 text-center text-xs font-medium text-zinc-400">
                  {v.vendor_name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lineItems.map((li) => {
              const assignedTo = getAssignedVendors(li.id);
              const isUnassigned = assignedTo.length === 0;
              return (
                <tr key={li.id} className={`border-b border-zinc-800/50 ${isUnassigned ? "bg-red-900/10" : ""}`}>
                  <td className="sticky left-0 bg-zinc-900 px-4 py-3 z-10">
                    <div className="font-medium text-zinc-200">{li.sku_code}</div>
                    <div className="text-xs text-zinc-500">{li.qty} {li.unit}</div>
                  </td>
                  {availableVendors.map((v) => {
                    const isAssigned = assignedTo.includes(v.vendor_id);
                    const canSupply = (v.line_items ?? []).some((ol) => ol.line_item_id === li.id);
                    return (
                      <td key={v.vendor_id} className="px-3 py-3 text-center">
                        <button
                          type="button"
                          onClick={() => toggleItemVendor(li.id, v.vendor_id)}
                          className={`h-7 w-7 rounded-md text-xs font-bold transition ${
                            isAssigned
                              ? "bg-green-600 text-white"
                              : canSupply
                                ? "border border-zinc-600 text-zinc-400 hover:border-indigo-500 hover:text-indigo-400"
                                : "border border-zinc-800 text-zinc-700 cursor-not-allowed opacity-50"
                          }`}
                          title={canSupply ? (isAssigned ? "Remove assignment" : "Assign to this vendor") : "Vendor cannot supply this item"}
                        >
                          {isAssigned ? "✓" : canSupply ? "+" : "—"}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Unassigned items warning */}
      {lineItems.some((li) => getAssignedVendors(li.id).length === 0) && (
        <div className="rounded-lg border border-amber-800/50 bg-amber-900/10 px-4 py-3">
          <p className="text-sm text-amber-400">
            Some items have no vendor assigned. Each item must be assigned to at least one vendor.
          </p>
        </div>
      )}

      {/* AI Suggestions */}
      {suggestions && suggestions.length > 0 && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
          <h4 className="text-xs font-medium uppercase tracking-wider text-zinc-500 mb-3">
            Suggested Assignments
          </h4>
          <div className="space-y-2">
            {suggestions.map((s) => (
              <div key={s.vendor_id} className="flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2">
                <div className="min-w-0 flex-1">
                  <span className="text-sm font-medium text-zinc-200">{s.vendor_name}</span>
                  <span className="ml-2 text-xs text-zinc-500">
                    {s.matching_items.map((i) => i.sku_code).join(", ")}
                  </span>
                </div>
                <span className="text-xs text-zinc-600">
                  {Math.round(s.match_score * 100)}% match
                </span>
                <button
                  type="button"
                  onClick={() => applySuggestion(s)}
                  className="rounded-md bg-indigo-600/20 px-2.5 py-1 text-xs text-indigo-400 hover:bg-indigo-600/30"
                >
                  Apply
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
      {suggestionsLoading && (
        <p className="text-xs text-zinc-500">Loading vendor suggestions...</p>
      )}
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
  assignments,
}: {
  lineItems: LineItem[];
  vendorOffers: VendorOffer[];
  awards: Map<number, number>;
  onToggleAward: (lineItemId: number, vendorId: number) => void;
  assignments: Assignment[];
}) {
  const quotedVendors = vendorOffers.filter((v) => v.status === "quoted");

  if (quotedVendors.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6 text-center">
        <p className="text-sm text-zinc-500">No vendor quotes received yet.</p>
      </div>
    );
  }

  const priceLookup = new Map<number, Map<number, { price: number; confidence?: number }>>();
  for (const vendor of quotedVendors) {
    for (const ol of vendor.line_items ?? []) {
      if (!priceLookup.has(ol.line_item_id)) priceLookup.set(ol.line_item_id, new Map());
      priceLookup.get(ol.line_item_id)!.set(vendor.vendor_id, { price: ol.unit_price, confidence: ol.confidence });
    }
  }

  function priceRangeForItem(lineItemId: number): { min: number; max: number } {
    const vendorPrices = priceLookup.get(lineItemId);
    if (!vendorPrices || vendorPrices.size === 0) return { min: 0, max: 0 };
    const prices = Array.from(vendorPrices.values()).map((v) => v.price);
    return { min: Math.min(...prices), max: Math.max(...prices) };
  }

  // Filter to only show vendors that are assigned items (or all if no assignments)
  const hasAssignments = assignments.length > 0;
  const visibleVendors = hasAssignments
    ? quotedVendors.filter((v) => assignments.some((a) => a.vendor_id === v.vendor_id))
    : quotedVendors;

  const vendorsWithUnmapped = visibleVendors.filter(
    (v) => (v.unmapped_items?.length ?? 0) > 0
  );

  return (
    <div className="space-y-3">
    <div className="overflow-x-auto rounded-xl border border-zinc-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900">
            <th className="sticky left-0 bg-zinc-900 px-4 py-3 text-left text-xs font-medium text-zinc-400">
              Line Item
            </th>
            {visibleVendors.map((v) => (
              <th key={v.vendor_id} className="min-w-[160px] px-4 py-3 text-center text-xs font-medium text-zinc-300">
                <div>{v.vendor_name}</div>
                <div className="mt-1 space-y-0.5 text-[10px] text-zinc-500 font-normal">
                  {v.total_quote != null && <div>Total: {formatCurrency(v.total_quote)}</div>}
                  {v.lead_time && <div>Lead: {v.lead_time}</div>}
                  {v.payment_terms && <div>Terms: {v.payment_terms}</div>}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {lineItems.map((li) => {
            const { min, max } = priceRangeForItem(li.id);
            return (
              <tr key={li.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                <td className="sticky left-0 bg-zinc-900 px-4 py-3 text-zinc-300">
                  <div className="font-medium">{li.sku_code}</div>
                  <div className="text-xs text-zinc-500">
                    {li.qty} {li.unit}
                    {li.target_price != null && (
                      <span className="ml-2">target {formatCurrency(li.target_price)}</span>
                    )}
                  </div>
                </td>
                {visibleVendors.map((v) => {
                  const entry = priceLookup.get(li.id)?.get(v.vendor_id);
                  const isAwarded = awards.get(li.id) === v.vendor_id;
                  const isAssignedToThis = assignments.some(
                    (a) => a.vendor_id === v.vendor_id && a.line_item_ids.includes(li.id)
                  );

                  let cellBg = "";
                  if (entry && min !== max) {
                    if (entry.price === min) cellBg = "bg-green-900/20";
                    else if (entry.price === max) cellBg = "bg-red-900/15";
                  }
                  if (hasAssignments && !isAssignedToThis) cellBg = "opacity-40";

                  return (
                    <td key={v.vendor_id} className={`px-4 py-3 text-center ${cellBg}`}>
                      {entry ? (
                        <div className="flex flex-col items-center gap-1.5">
                          <span className="text-zinc-200 font-medium tabular-nums">
                            {formatCurrency(entry.price)}
                            <ConfidenceDot confidence={entry.confidence} />
                          </span>
                          {entry.price === min && min !== max && (
                            <span className="text-[10px] text-green-400 font-medium">Best Price</span>
                          )}
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

      {vendorsWithUnmapped.length > 0 && (
        <div className="rounded-xl border border-amber-700/40 bg-amber-600/10 p-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-amber-300">
            Quoted items that couldn't be auto-matched
          </p>
          <p className="mb-3 text-xs text-zinc-400">
            These vendors quoted items the system couldn't map to a line above —
            review them manually so nothing is missed.
          </p>
          <div className="space-y-2">
            {vendorsWithUnmapped.map((v) => (
              <div key={v.vendor_id} className="text-sm">
                <span className="font-medium text-zinc-200">{v.vendor_name}:</span>{" "}
                <span className="text-zinc-400">
                  {(v.unmapped_items ?? [])
                    .map(
                      (it) =>
                        `${it.name}${
                          it.unit_price != null
                            ? ` @ ${formatCurrency(it.unit_price)}`
                            : ""
                        }`
                    )
                    .join(", ")}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function RFxDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [awards, setAwards] = useState<Map<number, number>>(new Map());
  const [awardConfirmOpen, setAwardConfirmOpen] = useState(false);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [dispatchConfirmOpen, setDispatchConfirmOpen] = useState(false);

  const { data: rfx, isLoading, error } = useQuery<RfxDetail>({
    queryKey: ["buyer", "rfx", id],
    queryFn: () => api.get<RfxDetail>(`/api/buyer/rfx/${id}`),
    enabled: !!id,
  });

  // Fetch vendor suggestions
  const { data: suggestions, isLoading: suggestionsLoading } = useQuery<VendorSuggestion[]>({
    queryKey: ["buyer", "rfx", id, "vendor-suggestions"],
    queryFn: () => api.get<VendorSuggestion[]>(`/api/buyer/rfx/${id}/vendor-suggestions`).catch(() => []),
    enabled: !!id && rfx?.status === "drafting",
  });

  const countdown = useCountdown(rfx?.deadline ?? new Date().toISOString());

  // Initialize assignments from existing vendor data
  useEffect(() => {
    if (rfx?.vendor_offers) {
      const initial: Assignment[] = rfx.vendor_offers.map((v) => ({
        vendor_id: v.vendor_id,
        line_item_ids: v.assigned_line_item_ids ?? rfx.line_items.map((li) => li.id),
      }));
      if (assignments.length === 0 && initial.length > 0) {
        setAssignments(initial);
      }
    }
  }, [rfx?.vendor_offers]);

  const awardMutation = useMutation({
    mutationFn: (decisions: AwardDecision[]) =>
      api.post(`/api/buyer/rfx/${id}/award`, { decisions }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["buyer", "rfx", id] });
      queryClient.invalidateQueries({ queryKey: ["buyer", "rfx"] });
      showToast("Awards submitted successfully");
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (reason: string) =>
      api.post(`/api/buyer/rfx/${id}/cancel`, { reason }),
    onSuccess: () => {
      setCancelModalOpen(false);
      setCancelReason("");
      queryClient.invalidateQueries({ queryKey: ["buyer", "rfx", id] });
      queryClient.invalidateQueries({ queryKey: ["buyer", "rfx"] });
      showToast("RFx withdrawn");
    },
  });

  const assignMutation = useMutation({
    mutationFn: (assigns: Assignment[]) =>
      api.post(`/api/buyer/rfx/${id}/assign-vendors`, { assignments: assigns }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["buyer", "rfx", id] });
      showToast("Vendor assignments saved");
      setAssignModalOpen(false);
    },
    onError: () => {
      showToast("Assignments saved locally (backend pending)", "success");
      setAssignModalOpen(false);
    },
  });

  function handleToggleAward(lineItemId: number, vendorId: number) {
    setAwards((prev) => {
      const next = new Map(prev);
      if (next.get(lineItemId) === vendorId) next.delete(lineItemId);
      else next.set(lineItemId, vendorId);
      return next;
    });
  }

  function handleSubmitAwards() {
    setAwardConfirmOpen(true);
  }

  function confirmSubmitAwards() {
    const decisions: AwardDecision[] = Array.from(awards.entries()).map(([line_item_id, vendor_id]) => {
      const vendor = rfx?.vendor_offers.find((v) => v.vendor_id === vendor_id);
      const offerItem = vendor?.line_items?.find((ol) => ol.line_item_id === line_item_id);
      const lineItem = rfx?.line_items.find((li) => li.id === line_item_id);
      return {
        line_item_id,
        vendor_id,
        unit_price: offerItem?.unit_price,
        qty: lineItem?.qty,
      };
    });
    awardMutation.mutate(decisions);
    setAwardConfirmOpen(false);
  }

  function handleApplyCombination(newAssignments: Assignment[]) {
    setAssignments(newAssignments);
    showToast("Optimal combination applied");
  }

  if (isLoading) return <LoadingSpinner message="Loading RFx..." />;

  if (error || !rfx) {
    return (
      <div className="p-6">
        <ErrorState message="Failed to load RFx details." onRetry={() => navigate("/buyer/dashboard")} />
      </div>
    );
  }

  const isCancelledOrAwarded = rfx.status === "cancelled" || rfx.status === "awarded";
  const isDrafting = rfx.status === "drafting";
  const isDispatched = rfx.status === "dispatched";
  const hasQuotes = rfx.vendor_offers.some((v) => v.status === "quoted");
  const quotedVendors = rfx.vendor_offers.filter((v) => v.status === "quoted");

  const lifecycleSteps = rfx.status === "cancelled"
    ? [...LIFECYCLE_STEPS.slice(0, 1), CANCELLED_STEP]
    : LIFECYCLE_STEPS;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <PageHeader
        title={rfx.title}
        subtitle={`${rfx.line_items.length} item${rfx.line_items.length > 1 ? "s" : ""} · Deadline: ${countdown}`}
        actions={
          !isCancelledOrAwarded && (
            <button
              type="button"
              onClick={() => setCancelModalOpen(true)}
              className="rounded-lg border border-red-800/50 px-4 py-2 text-sm font-medium text-red-400 transition hover:bg-red-900/20"
            >
              Withdraw RFx
            </button>
          )
        }
      />

      {/* Lifecycle Stepper */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
          RFx Journey
        </h3>
        <LifecycleStepper
          steps={lifecycleSteps}
          currentStep={rfx.status}
        />
        <p className="mt-3 text-xs text-zinc-500">
          {rfx.status === "drafting" && "Preparing RFx. Assign vendors and dispatch when ready."}
          {rfx.status === "dispatched" && "Waiting for vendor responses. Reminders are sent automatically."}
          {rfx.status === "collecting" && "Vendors are submitting their quotes."}
          {rfx.status === "comparing" && "Quotes received. Review the comparison matrix below to make awards."}
          {rfx.status === "awarded" && "Awards have been submitted. Purchase orders are being generated."}
          {rfx.status === "cancelled" && "This RFx has been withdrawn."}
        </p>
      </div>

      {/* RFx Terms */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
          Terms & Details
        </h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {[
            { label: "Payment", value: rfx.payment_terms ?? "NET30" },
            { label: "Delivery", value: rfx.delivery_terms ?? "doorstep" },
            { label: "Currency", value: rfx.currency ?? "INR" },
            { label: "Validity", value: `${rfx.line_items.length} days` },
            { label: "Tax", value: rfx.tax_treatment ?? "exclusive" },
          ].map((t) => (
            <div key={t.label}>
              <label className="block text-[10px] font-medium text-zinc-600">{t.label}</label>
              <p className="mt-0.5 text-sm font-medium text-zinc-200 capitalize">{t.value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Line Items + Vendor Assignment */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-zinc-400">Line Items</h2>
          {!isCancelledOrAwarded && isDrafting && (
            <button
              type="button"
              onClick={() => setAssignModalOpen(true)}
              className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-indigo-500"
            >
              Assign Vendors
            </button>
          )}
        </div>
        <div className="overflow-x-auto rounded-xl border border-zinc-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900">
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400">SKU</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-zinc-400">Qty</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400">Unit</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-zinc-400">Target Price</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400">Assigned To</th>
              </tr>
            </thead>
            <tbody>
              {rfx.line_items.map((li) => {
                const assignedVendors = assignments
                  .filter((a) => a.line_item_ids.includes(li.id))
                  .map((a) => rfx.vendor_offers.find((v) => v.vendor_id === a.vendor_id)?.vendor_name ?? `Vendor #${a.vendor_id}`);
                return (
                  <tr key={li.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                    <td className="px-4 py-3">
                      <div className="font-medium text-zinc-200">{li.sku_code}</div>
                      <div className="text-xs text-zinc-500">{li.sku_name}</div>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-zinc-300">{li.qty}</td>
                    <td className="px-4 py-3 text-zinc-400">{li.unit}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-zinc-300">
                      {li.target_price != null ? formatCurrency(li.target_price) : "--"}
                    </td>
                    <td className="px-4 py-3">
                      {assignedVendors.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {assignedVendors.map((name) => (
                            <span key={name} className="rounded-full bg-indigo-900/30 px-2 py-0.5 text-[10px] text-indigo-400">
                              {name}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-xs text-amber-400">Unassigned</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Smart Combination (only when quotes received) */}
      {hasQuotes && isDrafting && (
        <SmartCombination
          lineItems={rfx.line_items}
          vendorOffers={rfx.vendor_offers}
          onApply={handleApplyCombination}
        />
      )}

      {/* Dispatch Button (drafting state with assignments) */}
      {isDrafting && assignments.length > 0 && (
        <div className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900 p-4">
          <div>
            <p className="text-sm font-medium text-zinc-200">Ready to dispatch?</p>
            <p className="text-xs text-zinc-500">
              {assignments.length} vendor{assignments.length > 1 ? "s" : ""} will receive this RFx with their assigned items.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setDispatchConfirmOpen(true)}
            className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-500"
          >
            Dispatch to Vendors
          </button>
        </div>
      )}

      {/* Vendor Responses */}
      <section>
        <h2 className="mb-3 text-sm font-medium text-zinc-400">Vendor Responses</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {rfx.vendor_offers.map((vendor) => {
            const vendorAssignment = assignments.find((a) => a.vendor_id === vendor.vendor_id);
            const assignedCount = vendorAssignment?.line_item_ids.length ?? rfx.line_items.length;
            return (
              <div key={vendor.vendor_id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-zinc-200">{vendor.vendor_name}</span>
                  <StatusBadge status={vendor.status} variant="lane" />
                </div>
                <p className="mt-1 text-xs text-zinc-500">
                  {assignedCount} of {rfx.line_items.length} items assigned
                </p>
                {vendor.status === "quoted" && (
                  <div className="mt-3 space-y-1 text-xs text-zinc-400">
                    {vendor.total_quote != null && (
                      <p>Total: <span className="text-zinc-200">{formatCurrency(vendor.total_quote)}</span></p>
                    )}
                    {vendor.lead_time && <p>Lead: <span className="text-zinc-200">{vendor.lead_time}</span></p>}
                    {vendor.payment_terms && <p>Terms: <span className="text-zinc-200">{vendor.payment_terms}</span></p>}
                  </div>
                )}
                {vendor.status === "declined" && vendor.decline_reason && (
                  <div className="mt-3 rounded-lg border border-red-800/30 bg-red-900/10 px-3 py-2">
                    <p className="text-xs text-red-400">Declined: {vendor.decline_reason}</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* Comparison Matrix */}
      {quotedVendors.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-medium text-zinc-400">Comparison Matrix</h2>
          <ComparisonMatrix
            lineItems={rfx.line_items}
            vendorOffers={rfx.vendor_offers}
            awards={awards}
            onToggleAward={handleToggleAward}
            assignments={assignments}
          />
          {!isCancelledOrAwarded && awards.size > 0 && (
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={handleSubmitAwards}
                disabled={awardMutation.isPending}
                className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
              >
                {awardMutation.isPending ? "Awarding..." : `Award Selected (${awards.size})`}
              </button>
            </div>
          )}
          {awardMutation.isError && <p className="mt-2 text-sm text-red-400">Failed to submit awards.</p>}
          {awardMutation.isSuccess && <p className="mt-2 text-sm text-green-400">Awards submitted successfully.</p>}
        </section>
      )}

      {/* Vendor Assignment Modal */}
      <Modal open={assignModalOpen} onClose={() => setAssignModalOpen(false)} title="Assign Vendors to Items" size="lg">
        <VendorAssignmentPanel
          lineItems={rfx.line_items}
          vendorOffers={rfx.vendor_offers}
          assignments={assignments}
          onChange={setAssignments}
          suggestions={suggestions ?? null}
          suggestionsLoading={suggestionsLoading}
        />
        <div className="mt-4 flex justify-end gap-3">
          <button
            type="button"
            onClick={() => setAssignModalOpen(false)}
            className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-800"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => assignMutation.mutate(assignments)}
            disabled={assignMutation.isPending}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {assignMutation.isPending ? "Saving..." : "Save Assignments"}
          </button>
        </div>
      </Modal>

      {/* Cancel Modal */}
      <Modal
        open={cancelModalOpen}
        onClose={() => { setCancelModalOpen(false); setCancelReason(""); }}
        title="Withdraw RFx"
        size="md"
      >
        <p className="text-sm text-zinc-400">This will cancel the RFx and notify all vendors. This action cannot be undone.</p>
        <textarea
          value={cancelReason}
          onChange={(e) => setCancelReason(e.target.value)}
          placeholder="Reason for withdrawal..."
          rows={3}
          className="mt-4 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500"
        />
        <div className="mt-4 flex justify-end gap-3">
          <button type="button" onClick={() => { setCancelModalOpen(false); setCancelReason(""); }} className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-800">
            Cancel
          </button>
          <button
            type="button"
            disabled={!cancelReason.trim() || cancelMutation.isPending}
            onClick={() => cancelMutation.mutate(cancelReason.trim())}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-500 disabled:opacity-50"
          >
            {cancelMutation.isPending ? "Withdrawing..." : "Confirm Withdraw"}
          </button>
        </div>
      </Modal>

      {/* Award Confirmation */}
      <ConfirmDialog
        open={awardConfirmOpen}
        onClose={() => setAwardConfirmOpen(false)}
        onConfirm={confirmSubmitAwards}
        title="Confirm Award"
        message={`Award ${awards.size} line item${awards.size > 1 ? "s" : ""}? Selected vendors will be notified and POs will be generated.`}
        confirmLabel="Confirm Award"
        confirmVariant="primary"
        isPending={awardMutation.isPending}
      />

      {/* Dispatch Confirmation */}
      <ConfirmDialog
        open={dispatchConfirmOpen}
        onClose={() => setDispatchConfirmOpen(false)}
        onConfirm={() => {
          setDispatchConfirmOpen(false);
          // Navigate to chat to dispatch, or call dispatch API
          navigate("/buyer/chat", { state: { rfxId: rfx.id, action: "dispatch" } });
        }}
        title="Dispatch RFx"
        message={`Send this RFx to ${assignments.length} vendor${assignments.length > 1 ? "s" : ""} with their assigned items?`}
        confirmLabel="Dispatch Now"
        confirmVariant="primary"
      />
    </div>
  );
}
