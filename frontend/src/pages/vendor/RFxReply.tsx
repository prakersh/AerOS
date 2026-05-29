import {
  useState,
  useRef,
  useEffect,
  useCallback,
  useMemo,
  type FormEvent,
  type DragEvent,
  type KeyboardEvent,
} from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import {
  Modal,
  PageHeader,
  LoadingSpinner,
  ErrorState,
  StatusBadge,
  VoiceInput,
  showToast,
  AgentBlocks,
} from "@/components/ui";
import type { AgentBlock } from "@/components/ui";
import {
  formatTimestamp,
  formatFileSize,
  formatCurrency,
  formatCountdown,
  formatDate,
} from "@/lib/format";
import {
  senderLabel,
  channelLabel,
  extractionLabel,
  rfxStatusLabel,
} from "@/lib/labels";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type SenderKind = "buyer" | "vendor" | "system" | "agent";
type Channel = "email" | "telegram" | "in_app";
type ExtractionStatus = "pending" | "extracted" | "failed";
type DeclineCategory = "out-of-stock" | "pricing" | "capacity" | "other";
type Tab = "quote" | "chat" | "upload";

interface ThreadMessage {
  id: string;
  body_text: string;
  sender_kind: SenderKind;
  channel: Channel;
  created_at: string;
}

interface UploadedFile {
  id: string;
  filename: string;
  size_bytes: number;
  extraction_status: ExtractionStatus;
}

interface LineItem {
  id: string;
  sku: string;
  description: string;
  quantity: number;
  unit: string;
  target_price: number | null;
}

interface LineItemQuote {
  line_item_id: string;
  unit_price: string;
  lead_time_days: string;
  notes: string;
}

interface QuoteDraft {
  line_items: LineItemQuote[];
  payment_terms: string;
  delivery_terms: string;
  validity_until: string;
  vendor_remarks: string;
}

interface ExistingQuoteLineItem {
  line_item_id: number | null;
  unit_price: number;
  lead_time_days: number | null;
  notes: string | null;
}

interface ExistingQuote {
  offer_id: number;
  revision_no: number;
  line_items: ExistingQuoteLineItem[];
  total_quote: number | null;
  payment_terms: string | null;
  delivery_terms: string | null;
  validity_until: string | null;
  vendor_remarks: string | null;
}

interface RfxThreadResponse {
  rfx_id: string;
  rfx_title: string;
  rfx_status: string;
  vendor_status: string;
  deadline: string | null;
  currency: string;
  payment_terms: string | null;
  delivery_terms: string | null;
  tax_terms: string | null;
  line_items: LineItem[];
  existing_quote: ExistingQuote | null;
  messages: ThreadMessage[];
  attachments: UploadedFile[];
}

/* ------------------------------------------------------------------ */
/* Badge / display maps                                                */
/* ------------------------------------------------------------------ */

const SENDER_COLORS: Record<SenderKind, string> = {
  buyer: "bg-indigo-600/20 text-indigo-400",
  vendor: "bg-green-600/20 text-green-400",
  system: "bg-zinc-700/40 text-zinc-500",
  agent: "bg-amber-600/20 text-amber-400",
};

const CHANNEL_COLORS: Record<Channel, string> = {
  email: "bg-blue-600/15 text-blue-400",
  telegram: "bg-sky-600/15 text-sky-400",
  in_app: "bg-zinc-700/30 text-zinc-500",
};

const EXTRACTION_COLORS: Record<ExtractionStatus, string> = {
  pending: "bg-amber-600/20 text-amber-400",
  extracted: "bg-green-600/20 text-green-400",
  failed: "bg-red-600/20 text-red-400",
};

const ACCEPT_TYPES = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "text/csv",
  "image/png",
  "image/jpeg",
  "image/webp",
].join(",");

/* ------------------------------------------------------------------ */
/* localStorage helpers                                                */
/* ------------------------------------------------------------------ */

const DRAFT_PREFIX = "aeros_vendor_quote_draft_";

function loadDraft(rfxId: string): QuoteDraft | null {
  try {
    const raw = localStorage.getItem(DRAFT_PREFIX + rfxId);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveDraft(rfxId: string, draft: QuoteDraft): void {
  try {
    localStorage.setItem(DRAFT_PREFIX + rfxId, JSON.stringify(draft));
  } catch {
    // storage full or unavailable — silently ignore
  }
}

function clearDraft(rfxId: string): void {
  try {
    localStorage.removeItem(DRAFT_PREFIX + rfxId);
  } catch {
    // ignore
  }
}

/* ------------------------------------------------------------------ */
/* Sub-components                                                      */
/* ------------------------------------------------------------------ */

function MessageBubble({ msg }: { msg: ThreadMessage }) {
  if (msg.sender_kind === "system") {
    return (
      <div className="flex justify-center py-1">
        <div className="max-w-[80%] rounded-md bg-zinc-800/50 px-3 py-1.5">
          <p className="text-center text-xs text-zinc-500">{msg.body_text}</p>
          <p className="mt-0.5 text-center text-[10px] text-zinc-600">
            {formatTimestamp(msg.created_at)}
          </p>
        </div>
      </div>
    );
  }

  const isVendor = msg.sender_kind === "vendor";

  return (
    <div className={`flex ${isVendor ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-xl px-4 py-3 ${
          isVendor ? "bg-indigo-600 text-white" : "bg-zinc-800 text-zinc-200"
        }`}
      >
        <div className="mb-1.5 flex items-center gap-2">
          <span
            className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${SENDER_COLORS[msg.sender_kind]}`}
          >
            {senderLabel(msg.sender_kind)}
          </span>
          <span
            className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${CHANNEL_COLORS[msg.channel]}`}
          >
            {channelLabel(msg.channel)}
          </span>
        </div>
        <p className="text-sm whitespace-pre-wrap">{msg.body_text}</p>
        <p className="mt-1 text-[10px] opacity-50">
          {formatTimestamp(msg.created_at)}
        </p>
      </div>
    </div>
  );
}

/* ---------- RFx Context Panel ---------- */

function RfxContextPanel({
  rfx,
  expanded,
  onToggleExpand,
}: {
  rfx: RfxThreadResponse;
  expanded: boolean;
  onToggleExpand: () => void;
}) {
  const isExpired =
    rfx.deadline && new Date(rfx.deadline).getTime() < Date.now();

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5">
      {/* Top row: title + status + deadline */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3">
            <h2 className="truncate text-lg font-semibold text-zinc-100">
              {rfx.rfx_title || `RFx #${rfx.rfx_id}`}
            </h2>
            <StatusBadge status={rfx.rfx_status} variant="rfx" />
            {rfx.vendor_status && rfx.vendor_status !== rfx.rfx_status && (
              <StatusBadge status={rfx.vendor_status} variant="lane" />
            )}
          </div>
        </div>

        {rfx.deadline && (
          <div
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium ${
              isExpired
                ? "bg-red-900/30 text-red-400"
                : "bg-zinc-800 text-zinc-300"
            }`}
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            {formatCountdown(rfx.deadline)}
          </div>
        )}
      </div>

      {/* Compact summary row */}
      <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-zinc-400">
        {rfx.payment_terms && (
          <span>
            <span className="text-zinc-600">Payment:</span>{" "}
            {rfx.payment_terms}
          </span>
        )}
        {rfx.delivery_terms && (
          <span>
            <span className="text-zinc-600">Delivery:</span>{" "}
            {rfx.delivery_terms}
          </span>
        )}
        {rfx.currency && (
          <span>
            <span className="text-zinc-600">Currency:</span> {rfx.currency}
          </span>
        )}
        {rfx.tax_terms && (
          <span>
            <span className="text-zinc-600">Tax:</span> {rfx.tax_terms}
          </span>
        )}
        <span>
          <span className="text-zinc-600">Line items:</span>{" "}
          {rfx.line_items.length}
        </span>
      </div>

      {/* Expand toggle */}
      <button
        type="button"
        onClick={onToggleExpand}
        className="mt-3 flex items-center gap-1 text-xs font-medium text-indigo-400 transition hover:text-indigo-300"
      >
        {expanded ? "Hide Details" : "View Full Details"}
        <svg
          className={`h-3.5 w-3.5 transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="mt-4 grid grid-cols-1 gap-4 rounded-lg border border-zinc-800 bg-zinc-950/50 p-4 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <label className="block text-[10px] font-medium uppercase tracking-wider text-zinc-600">
              Reference
            </label>
            <p className="mt-1 text-sm text-zinc-300">#{rfx.rfx_id}</p>
          </div>
          <div>
            <label className="block text-[10px] font-medium uppercase tracking-wider text-zinc-600">
              Status
            </label>
            <p className="mt-1 text-sm text-zinc-300">
              {rfxStatusLabel(rfx.rfx_status)}
            </p>
          </div>
          {rfx.deadline && (
            <div>
              <label className="block text-[10px] font-medium uppercase tracking-wider text-zinc-600">
                Deadline
              </label>
              <p className="mt-1 text-sm text-zinc-300">
                {formatDate(rfx.deadline)}
              </p>
            </div>
          )}
          {rfx.payment_terms && (
            <div>
              <label className="block text-[10px] font-medium uppercase tracking-wider text-zinc-600">
                Payment Terms
              </label>
              <p className="mt-1 text-sm text-zinc-300">
                {rfx.payment_terms}
              </p>
            </div>
          )}
          {rfx.delivery_terms && (
            <div>
              <label className="block text-[10px] font-medium uppercase tracking-wider text-zinc-600">
                Delivery Terms
              </label>
              <p className="mt-1 text-sm text-zinc-300">
                {rfx.delivery_terms}
              </p>
            </div>
          )}
          {rfx.tax_terms && (
            <div>
              <label className="block text-[10px] font-medium uppercase tracking-wider text-zinc-600">
                Tax Terms
              </label>
              <p className="mt-1 text-sm text-zinc-300">{rfx.tax_terms}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ---------- Tab 1: Quote Form ---------- */

function QuoteFormTab({
  rfx,
  rfxId,
}: {
  rfx: RfxThreadResponse;
  rfxId: string;
}) {
  const savedDraft = useMemo(() => loadDraft(rfxId), [rfxId]);
  const eq = rfx.existing_quote;

  const [lineQuotes, setLineQuotes] = useState<LineItemQuote[]>(() => {
    if (savedDraft?.line_items?.length) return savedDraft.line_items;
    // Pre-fill from existing submitted quote
    if (eq?.line_items?.length) {
      const offerByLineItem = new Map<number, ExistingQuoteLineItem>();
      for (const oli of eq.line_items) {
        if (oli.line_item_id != null) offerByLineItem.set(oli.line_item_id, oli);
      }
      return rfx.line_items.map((li) => {
        const match = offerByLineItem.get(parseInt(li.id, 10));
        return {
          line_item_id: li.id,
          unit_price: match ? String(match.unit_price) : "",
          lead_time_days: match?.lead_time_days != null ? String(match.lead_time_days) : "",
          notes: match?.notes ?? "",
        };
      });
    }
    return rfx.line_items.map((li) => ({
      line_item_id: li.id,
      unit_price: "",
      lead_time_days: "",
      notes: "",
    }));
  });

  const [paymentTerms, setPaymentTerms] = useState(
    () => savedDraft?.payment_terms ?? eq?.payment_terms ?? "",
  );
  const [deliveryTerms, setDeliveryTerms] = useState(
    () => savedDraft?.delivery_terms ?? eq?.delivery_terms ?? "",
  );
  const [validityUntil, setValidityUntil] = useState(
    () => savedDraft?.validity_until ?? eq?.validity_until ?? "",
  );
  const [vendorRemarks, setVendorRemarks] = useState(
    () => savedDraft?.vendor_remarks ?? eq?.vendor_remarks ?? "",
  );

  const isRfxClosed = ["cancelled", "awarded", "closed", "expired"].includes(rfx.rfx_status);

  const queryClient = useQueryClient();

  const submitMutation = useMutation({
    mutationFn: () =>
      api.post(`/api/vendor/rfx/${rfxId}/submit-quote`, {
        line_items: lineQuotes
          .filter((lq) => lq.unit_price.trim() !== "")
          .map((lq) => ({
            line_item_id: parseInt(lq.line_item_id, 10) || 0,
            unit_price: parseFloat(lq.unit_price) || 0,
            lead_time_days: parseInt(lq.lead_time_days, 10) || null,
            notes: lq.notes || undefined,
          })),
        payment_terms: paymentTerms || undefined,
        delivery_terms: deliveryTerms || undefined,
        validity_until: validityUntil || undefined,
        vendor_remarks: vendorRemarks || undefined,
      }),
    onSuccess: () => {
      clearDraft(rfxId);
      showToast("Quote submitted successfully", "success");
      queryClient.invalidateQueries({
        queryKey: ["vendor", "rfx", rfxId, "thread"],
      });
    },
    onError: () => {
      showToast("Failed to submit quote. Please try again.", "error");
    },
  });

  const handleLineFieldChange = (
    index: number,
    field: keyof LineItemQuote,
    value: string,
  ) => {
    setLineQuotes((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };

  const handleSaveDraft = () => {
    const draft: QuoteDraft = {
      line_items: lineQuotes,
      payment_terms: paymentTerms,
      delivery_terms: deliveryTerms,
      validity_until: validityUntil,
      vendor_remarks: vendorRemarks,
    };
    saveDraft(rfxId, draft);
    showToast("Draft saved locally", "success");
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const hasAtLeastOnePrice = lineQuotes.some(
      (lq) => lq.unit_price.trim() !== "",
    );
    if (!hasAtLeastOnePrice) {
      showToast(
        "Enter at least one unit price before submitting",
        "error",
      );
      return;
    }
    submitMutation.mutate();
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {isRfxClosed && (
        <div className="rounded-lg border border-amber-800/50 bg-amber-900/20 px-4 py-3 text-sm text-amber-400">
          This request is <span className="font-semibold">{rfxStatusLabel(rfx.rfx_status)}</span>, so new quotes can't be submitted.
        </div>
      )}
      {eq && !isRfxClosed && (
        <div className="rounded-lg border border-indigo-800/50 bg-indigo-900/20 px-4 py-3 text-sm text-indigo-400">
          Showing your submitted quote (revision {eq.revision_no}). Edit and resubmit to update.
        </div>
      )}
      {/* Line items table */}
      <div className="overflow-x-auto rounded-xl border border-zinc-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900/60">
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                SKU
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                Description
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-zinc-500">
                Qty
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                Unit
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-zinc-500">
                Target Price
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-zinc-500">
                Your Unit Price
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-zinc-500">
                Lead Time (days)
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                Notes
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/60">
            {rfx.line_items.map((li, i) => {
              const lq = lineQuotes[i];
              return (
                <tr key={li.id} className="hover:bg-zinc-800/20">
                  <td className="px-4 py-3 font-mono text-xs text-zinc-300">
                    {li.sku}
                  </td>
                  <td className="px-4 py-3 text-xs text-zinc-400">
                    {li.description}
                  </td>
                  <td className="px-4 py-3 text-right text-xs text-zinc-300">
                    {li.quantity}
                  </td>
                  <td className="px-4 py-3 text-xs text-zinc-400">
                    {li.unit}
                  </td>
                  <td className="px-4 py-3 text-right text-xs text-zinc-400">
                    {li.target_price != null
                      ? formatCurrency(li.target_price, rfx.currency)
                      : "--"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={lq?.unit_price ?? ""}
                      onChange={(e) =>
                        handleLineFieldChange(i, "unit_price", e.target.value)
                      }
                      placeholder="0.00"
                      className="w-24 rounded-md border border-zinc-700 bg-zinc-800 px-2 py-1.5 text-right text-xs text-zinc-100 placeholder-zinc-600 outline-none focus:border-indigo-500"
                    />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <input
                      type="number"
                      min="0"
                      value={lq?.lead_time_days ?? ""}
                      onChange={(e) =>
                        handleLineFieldChange(
                          i,
                          "lead_time_days",
                          e.target.value,
                        )
                      }
                      placeholder="--"
                      className="w-20 rounded-md border border-zinc-700 bg-zinc-800 px-2 py-1.5 text-right text-xs text-zinc-100 placeholder-zinc-600 outline-none focus:border-indigo-500"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="text"
                      value={lq?.notes ?? ""}
                      onChange={(e) =>
                        handleLineFieldChange(i, "notes", e.target.value)
                      }
                      placeholder="Optional"
                      className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-2 py-1.5 text-xs text-zinc-100 placeholder-zinc-600 outline-none focus:border-indigo-500"
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Quote-level fields */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-400">
            Payment Terms
          </label>
          <input
            type="text"
            value={paymentTerms}
            onChange={(e) => setPaymentTerms(e.target.value)}
            placeholder="e.g. Net 30"
            className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-400">
            Delivery Terms
          </label>
          <input
            type="text"
            value={deliveryTerms}
            onChange={(e) => setDeliveryTerms(e.target.value)}
            placeholder="e.g. FOB Destination"
            className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-400">
            Validity Until
          </label>
          <input
            type="date"
            value={validityUntil}
            onChange={(e) => setValidityUntil(e.target.value)}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2.5 text-sm text-zinc-100 outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-zinc-400">
          Vendor Remarks
        </label>
        <textarea
          value={vendorRemarks}
          onChange={(e) => setVendorRemarks(e.target.value)}
          rows={3}
          placeholder="Any additional notes for the buyer..."
          className="w-full resize-none rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-indigo-500"
        />
      </div>

      {/* Action buttons */}
      <div className="flex items-center justify-between border-t border-zinc-800 pt-4">
        <button
          type="button"
          onClick={handleSaveDraft}
          className="rounded-lg border border-zinc-700 bg-zinc-800 px-5 py-2.5 text-sm font-medium text-zinc-300 transition hover:bg-zinc-700"
        >
          Save as Draft
        </button>
        <button
          type="submit"
          disabled={submitMutation.isPending || isRfxClosed}
          className="rounded-lg bg-indigo-600 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
        >
          {submitMutation.isPending
            ? "Submitting..."
            : eq
              ? "Resubmit Quote"
              : "Submit Quote"}
        </button>
      </div>
    </form>
  );
}

/* ---------- Tab 2: Chat / Messages ---------- */

function ChatTab({
  rfxId,
  messages,
  isLoading,
  error,
  onRetry,
}: {
  rfxId: string;
  messages: ThreadMessage[];
  isLoading: boolean;
  error: unknown;
  onRetry: () => void;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [replyText, setReplyText] = useState("");
  const queryClient = useQueryClient();

  const replyMutation = useMutation({
    mutationFn: (body_text: string) =>
      api.post(`/api/vendor/rfx/${rfxId}/reply`, { body_text }),
    onSuccess: () => {
      setReplyText("");
      queryClient.invalidateQueries({
        queryKey: ["vendor", "rfx", rfxId, "thread"],
      });
    },
    onError: () => {
      showToast("Failed to send message", "error");
    },
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleVoiceResult = useCallback((text: string) => {
    setReplyText((prev) => (prev ? `${prev} ${text}` : text));
  }, []);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      if (replyText.trim() && !replyMutation.isPending) {
        replyMutation.mutate(replyText.trim());
      }
    }
  };

  const handleSendReply = (e: FormEvent) => {
    e.preventDefault();
    if (!replyText.trim() || replyMutation.isPending) return;
    replyMutation.mutate(replyText.trim());
  };

  return (
    <div className="flex flex-col">
      {/* Messages */}
      <div className="max-h-[50vh] min-h-[200px] flex-1 space-y-4 overflow-y-auto">
        {isLoading && <LoadingSpinner message="Loading messages..." />}

        {!!error && (
          <ErrorState message="Failed to load messages." onRetry={onRetry} />
        )}

        {!isLoading && !error && messages.length === 0 && (
          <div className="flex items-center justify-center py-12">
            <p className="text-sm text-zinc-500">No messages yet.</p>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Reply area */}
      <form onSubmit={handleSendReply} className="mt-4 border-t border-zinc-800 pt-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
          Reply
        </p>
        <div className="flex gap-2">
          <textarea
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={3}
            placeholder="Type your reply... (Ctrl+Enter to send)"
            className="flex-1 resize-none rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
          <VoiceInput
            onResult={handleVoiceResult}
            className="self-end"
          />
        </div>

        {replyMutation.isError && (
          <p className="mt-2 text-xs text-red-400">Failed to send. Please try again.</p>
        )}

        <div className="mt-3 flex justify-end">
          <button
            type="submit"
            disabled={!replyText.trim() || replyMutation.isPending}
            className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
          >
            {replyMutation.isPending ? "Sending..." : "Send"}
          </button>
        </div>
      </form>
    </div>
  );
}

/* ---------- Tab 3: Upload & Analyze ---------- */

function UploadAnalyzeTab({
  rfxId,
  uploads,
  isLoading,
}: {
  rfxId: string;
  uploads: UploadedFile[];
  isLoading: boolean;
}) {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [analyzingFileId, setAnalyzingFileId] = useState<string | null>(null);
  const [aiAnswer, setAiAnswer] = useState<string | null>(null);
  const [aiBlocks, setAiBlocks] = useState<AgentBlock[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const handleFile = useCallback(
    async (file: File) => {
      setUploading(true);
      setUploadError(null);
      try {
        await api.upload(`/api/vendor/rfx/${rfxId}/upload`, file);
        queryClient.invalidateQueries({
          queryKey: ["vendor", "rfx", rfxId, "thread"],
        });
        showToast("File uploaded", "success");
      } catch (err: unknown) {
        const msg =
          err && typeof err === "object" && "message" in err
            ? String((err as { message: string }).message)
            : "Upload failed";
        setUploadError(msg);
        showToast(msg, "error");
      } finally {
        setUploading(false);
      }
    },
    [rfxId, queryClient],
  );

  const handleMultipleFiles = useCallback(
    async (files: FileList | File[]) => {
      const arr = Array.from(files);
      for (const file of arr) {
        await handleFile(file);
      }
    },
    [handleFile],
  );

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files.length) {
      handleMultipleFiles(e.dataTransfer.files);
    }
  };

  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(true);
  };

  const onDragLeave = () => setDragActive(false);

  const onBrowse = () => fileInputRef.current?.click();

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      handleMultipleFiles(e.target.files);
    }
    e.target.value = "";
  };

  const handleAskAI = async (fileId: string, filename: string) => {
    setAnalyzingFileId(fileId);
    setAiAnswer(null);
    setAiBlocks([]);
    try {
      const res = await api.post<{ message?: string; data?: { blocks?: AgentBlock[] } }>("/api/chat", {
        message: `I uploaded "${filename}". Show me what this RFx is requesting and help me review my quote against its requirements.`,
        history: [],
        rfx_id: Number(rfxId),
      });
      setAiAnswer(res.message || "No response from co-pilot.");
      setAiBlocks(res.data?.blocks ?? []);
    } catch {
      showToast("Failed to get co-pilot response", "error");
    } finally {
      setAnalyzingFileId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload zone */}
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
          Upload Documents
        </p>
        <div
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onClick={onBrowse}
          className={`cursor-pointer rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
            dragActive
              ? "border-indigo-500 bg-indigo-600/10"
              : "border-zinc-700 bg-zinc-800/30 hover:border-zinc-600"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPT_TYPES}
            multiple
            className="hidden"
            onChange={onFileChange}
          />
          {uploading ? (
            <div className="flex flex-col items-center gap-2">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-indigo-500" />
              <p className="text-sm text-zinc-400">Uploading...</p>
            </div>
          ) : (
            <>
              <svg
                className="mx-auto h-8 w-8 text-zinc-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                />
              </svg>
              <p className="mt-2 text-sm text-zinc-400">
                Drop files here or{" "}
                <span className="text-indigo-400">browse</span>
              </p>
              <p className="mt-1 text-xs text-zinc-600">
                PDF, Word, Excel, CSV, or images -- multiple files supported
              </p>
            </>
          )}
        </div>

        {uploadError && (
          <p className="mt-2 text-xs text-red-400">{uploadError}</p>
        )}
      </div>

      {/* Uploaded files list */}
      {isLoading && <LoadingSpinner message="Loading attachments..." />}

      {uploads.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Uploaded Files
          </p>
          <div className="space-y-2">
            {uploads.map((f) => (
              <div
                key={f.id}
                className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-zinc-300">{f.filename}</p>
                  <p className="text-xs text-zinc-600">
                    {formatFileSize(f.size_bytes)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${EXTRACTION_COLORS[f.extraction_status]}`}
                  >
                    {extractionLabel(f.extraction_status)}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleAskAI(f.id, f.filename)}
                    disabled={analyzingFileId === f.id}
                    className="rounded-lg bg-indigo-600/20 px-3 py-1.5 text-xs font-medium text-indigo-400 transition hover:bg-indigo-600/30 disabled:opacity-50"
                  >
                    {analyzingFileId === f.id
                      ? "Analyzing..."
                      : "Ask AI about this document"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {aiAnswer && (
        <div className="rounded-xl border border-indigo-700/40 bg-indigo-600/10 p-4">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-indigo-300">
              Vendor Co-pilot
            </p>
            <button
              type="button"
              onClick={() => {
                setAiAnswer(null);
                setAiBlocks([]);
              }}
              className="text-xs text-zinc-500 hover:text-zinc-300"
            >
              Dismiss
            </button>
          </div>
          <p className="whitespace-pre-wrap text-sm text-zinc-200">{aiAnswer}</p>
          {aiBlocks.length > 0 && <AgentBlocks blocks={aiBlocks} />}
        </div>
      )}
    </div>
  );
}

/* ---------- Decline Modal ---------- */

function DeclineModal({
  open,
  onClose,
  onConfirm,
  loading,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: (reason: string, category: DeclineCategory) => void;
  loading: boolean;
}) {
  const [reason, setReason] = useState("");
  const [category, setCategory] = useState<DeclineCategory>("other");

  useEffect(() => {
    if (!open) {
      setReason("");
      setCategory("other");
    }
  }, [open]);

  return (
    <Modal open={open} onClose={onClose} title="Decline this RFx" size="sm">
      <p className="text-xs text-zinc-500">
        Let the buyer know why you are declining.
      </p>

      <div className="mt-4">
        <label className="mb-1 block text-xs font-medium text-zinc-400">
          Category
        </label>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as DeclineCategory)}
          className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500"
        >
          <option value="out-of-stock">Out of stock</option>
          <option value="pricing">Pricing</option>
          <option value="capacity">Capacity</option>
          <option value="other">Other</option>
        </select>
      </div>

      <div className="mt-3">
        <label className="mb-1 block text-xs font-medium text-zinc-400">
          Reason
        </label>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={3}
          placeholder="Optionally explain why..."
          className="w-full resize-none rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-indigo-500"
        />
      </div>

      <div className="mt-5 flex justify-end gap-3">
        <button
          onClick={onClose}
          disabled={loading}
          className="rounded-lg px-4 py-2 text-sm text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-200 disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          onClick={() => onConfirm(reason, category)}
          disabled={loading}
          className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-500 disabled:opacity-50"
        >
          {loading ? "Declining..." : "Decline RFx"}
        </button>
      </div>
    </Modal>
  );
}

/* ------------------------------------------------------------------ */
/* Main page                                                           */
/* ------------------------------------------------------------------ */

export default function VendorRFxReply() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<Tab>("quote");
  const [declineOpen, setDeclineOpen] = useState(false);
  const [contextExpanded, setContextExpanded] = useState(false);

  /* ----- data fetching ----- */
  const threadQuery = useQuery<RfxThreadResponse>({
    queryKey: ["vendor", "rfx", id, "thread"],
    queryFn: () => api.get<RfxThreadResponse>(`/api/vendor/rfx/${id}/thread`),
    enabled: !!id,
  });

  const rfx = threadQuery.data;

  /* ----- mutations ----- */
  const declineMutation = useMutation({
    mutationFn: (payload: { reason: string; category: DeclineCategory }) =>
      api.post(`/api/vendor/rfx/${id}/decline`, payload),
    onSuccess: () => {
      setDeclineOpen(false);
      showToast("RFx declined", "success");
      queryClient.invalidateQueries({
        queryKey: ["vendor", "rfx", id, "thread"],
      });
      queryClient.invalidateQueries({ queryKey: ["vendor", "inbox"] });
    },
    onError: () => {
      showToast("Failed to decline RFx", "error");
    },
  });

  const handleDecline = (reason: string, category: DeclineCategory) => {
    declineMutation.mutate({ reason, category });
  };

  /* ----- tab definitions ----- */
  const tabs: { key: Tab; label: string }[] = [
    { key: "quote", label: "Quote Form" },
    { key: "chat", label: "Chat" },
    { key: "upload", label: "Upload & Analyze" },
  ];

  /* ----- loading / error states ----- */
  if (threadQuery.isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingSpinner message="Loading RFx details..." />
      </div>
    );
  }

  if (threadQuery.error || !rfx) {
    return (
      <div className="flex h-full items-center justify-center">
        <ErrorState
          message="Failed to load RFx details."
          onRetry={() => threadQuery.refetch()}
        />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Page header */}
      <div className="shrink-0 border-b border-zinc-800 px-6 py-4">
        <PageHeader
          title="RFx Reply"
          subtitle={`#${rfx.rfx_id}`}
          actions={
            <button
              onClick={() => setDeclineOpen(true)}
              className="rounded-lg border border-red-800/50 bg-red-900/20 px-4 py-2 text-sm font-medium text-red-400 transition hover:bg-red-900/40"
            >
              Decline
            </button>
          }
        />
      </div>

      {/* Main content area */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="mx-auto max-w-5xl space-y-6">
          {/* Context Panel */}
          <RfxContextPanel
            rfx={rfx}
            expanded={contextExpanded}
            onToggleExpand={() => setContextExpanded((prev) => !prev)}
          />

          {/* Tab bar */}
          <div className="flex gap-1 rounded-lg border border-zinc-800 bg-zinc-900/40 p-1">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex-1 rounded-md px-4 py-2.5 text-sm font-medium transition ${
                  activeTab === tab.key
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6">
            {activeTab === "quote" && (
              <QuoteFormTab rfx={rfx} rfxId={id!} />
            )}
            {activeTab === "chat" && (
              <ChatTab
                rfxId={id!}
                messages={rfx.messages}
                isLoading={false}
                error={null}
                onRetry={() =>
                  queryClient.invalidateQueries({
                    queryKey: ["vendor", "rfx", id, "thread"],
                  })
                }
              />
            )}
            {activeTab === "upload" && (
              <UploadAnalyzeTab
                rfxId={id!}
                uploads={rfx.attachments ?? []}
                isLoading={false}
              />
            )}
          </div>
        </div>
      </div>

      {/* Decline Modal -- preserves e2e selector */}
      <DeclineModal
        open={declineOpen}
        onClose={() => setDeclineOpen(false)}
        onConfirm={handleDecline}
        loading={declineMutation.isPending}
      />
    </div>
  );
}
