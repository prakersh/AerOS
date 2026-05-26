import { useState, useRef, useEffect, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/api/client";

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
  data?: Record<string, unknown>;
  timestamp: Date;
}

interface DraftLineItem {
  sku_name: string;
  qty: number;
  unit: string;
  target_price?: number;
}

interface SuggestedVendor {
  vendor_id: number;
  vendor_name: string;
  categories: string;
  recommended_channel: string;
}

export default function ChatCopilot() {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [createdRfxId, setCreatedRfxId] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg: ChatMsg = {
      role: "user",
      content: input,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const resp = await api.post<{
        message: string;
        data: Record<string, unknown>;
        success: boolean;
      }>("/api/chat", { message: input, history });

      const assistantMsg: ChatMsg = {
        role: "assistant",
        content: resp.message,
        data: resp.data,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      const errMsg =
        err && typeof err === "object" && "message" in err
          ? String((err as { message: string }).message)
          : "Failed to get response";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${errMsg}`, timestamp: new Date() },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmDraft = async (draft: Record<string, unknown>) => {
    setActionLoading(true);
    try {
      const resp = await api.post<{
        message: string;
        data: Record<string, unknown>;
        success: boolean;
      }>("/api/chat/create-rfx", { draft });

      const rfxId = resp.data?.rfx_id as number | undefined;
      if (rfxId) setCreatedRfxId(rfxId);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: resp.message,
          data: resp.data,
          timestamp: new Date(),
        },
      ]);
    } catch (err: unknown) {
      const errMsg =
        err && typeof err === "object" && "message" in err
          ? String((err as { message: string }).message)
          : "Failed to create RFx";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${errMsg}`, timestamp: new Date() },
      ]);
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmDispatch = async (
    rfxId: number,
    plan: Array<Record<string, unknown>>,
  ) => {
    setActionLoading(true);
    try {
      const resp = await api.post<{
        message: string;
        data: Record<string, unknown>;
        success: boolean;
      }>("/api/chat/dispatch", { rfx_id: rfxId, dispatch_plan: plan });

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: resp.message,
          data: resp.data,
          timestamp: new Date(),
        },
      ]);
    } catch (err: unknown) {
      const errMsg =
        err && typeof err === "object" && "message" in err
          ? String((err as { message: string }).message)
          : "Failed to dispatch";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${errMsg}`, timestamp: new Date() },
      ]);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="shrink-0 border-b border-zinc-800 px-6 py-4">
        <h1 className="text-lg font-semibold text-zinc-100">Chat Co-pilot</h1>
        <p className="text-xs text-zinc-500">
          Tell me what you need — I'll draft the purchase request.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <p className="text-zinc-400 text-sm">
                Start by telling me what you need to procure.
              </p>
              <p className="text-zinc-600 text-xs mt-2">
                Example: "I need 150kg tomatoes, 80kg onions, and 500L milk by tomorrow 5 AM"
              </p>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white"
                  : "bg-zinc-800 text-zinc-200"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              {!!msg.data?.draft && (
                <DraftCard
                  draft={msg.data.draft as Record<string, unknown>}
                  onConfirm={handleConfirmDraft}
                  confirmed={!!createdRfxId}
                  loading={actionLoading}
                />
              )}
              {!!msg.data?.terms_confirmation && (
                <TermsChip terms={msg.data.terms_confirmation as Record<string, unknown>} />
              )}
              {!!msg.data?.suggested_vendors && (
                <VendorSuggestions vendors={msg.data.suggested_vendors as SuggestedVendor[]} />
              )}
              {!!msg.data?.dispatch_plan && (
                <DispatchPlanCard
                  plan={msg.data.dispatch_plan as Array<Record<string, unknown>>}
                  rfxId={createdRfxId}
                  onConfirm={handleConfirmDispatch}
                  loading={actionLoading}
                />
              )}
              {!!msg.data?.rfx_id && msg.data?.status === "created" && (
                <button
                  type="button"
                  onClick={() => navigate(`/buyer/rfx/${msg.data!.rfx_id}`)}
                  className="mt-2 text-xs text-indigo-400 hover:text-indigo-300 underline"
                >
                  View RFx Details
                </button>
              )}
              {msg.data?.status === "dispatched" && (
                <div className="mt-2 flex items-center gap-2">
                  <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
                  <span className="text-xs text-green-400">Dispatched successfully</span>
                </div>
              )}
              <p className="text-[10px] mt-1 opacity-50">
                {msg.timestamp.toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-zinc-800 rounded-xl px-4 py-3">
              <div className="flex gap-1">
                <span className="h-2 w-2 rounded-full bg-zinc-500 animate-bounce [animation-delay:0ms]" />
                <span className="h-2 w-2 rounded-full bg-zinc-500 animate-bounce [animation-delay:150ms]" />
                <span className="h-2 w-2 rounded-full bg-zinc-500 animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={sendMessage} className="shrink-0 border-t border-zinc-800 px-6 py-4">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your procurement request..."
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}

function DraftCard({
  draft,
  onConfirm,
  confirmed,
  loading,
}: {
  draft: Record<string, unknown>;
  onConfirm: (draft: Record<string, unknown>) => void;
  confirmed: boolean;
  loading: boolean;
}) {
  const items = (draft.line_items as DraftLineItem[]) || [];
  return (
    <div className="mt-3 rounded-lg border border-zinc-700 bg-zinc-900 p-3">
      <p className="text-xs font-semibold text-indigo-400 mb-2">Draft RFQ</p>
      {!!draft.title && <p className="text-xs text-zinc-300 mb-2">{String(draft.title)}</p>}
      <table className="w-full text-xs">
        <thead>
          <tr className="text-zinc-500 border-b border-zinc-800">
            <th className="text-left py-1">Item</th>
            <th className="text-right py-1">Qty</th>
            <th className="text-right py-1">Unit</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={i} className="border-b border-zinc-800/50">
              <td className="py-1 text-zinc-300">{item.sku_name}</td>
              <td className="py-1 text-right text-zinc-300">{item.qty}</td>
              <td className="py-1 text-right text-zinc-400">{item.unit}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!confirmed && (
        <button
          type="button"
          disabled={loading}
          onClick={() => onConfirm(draft)}
          className="mt-3 w-full rounded-lg bg-indigo-600 px-3 py-2 text-xs font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
        >
          {loading ? "Creating..." : "Confirm & Create RFx"}
        </button>
      )}
      {confirmed && (
        <div className="mt-2 flex items-center gap-1.5 text-xs text-green-400">
          <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          RFx Created
        </div>
      )}
    </div>
  );
}

function TermsChip({ terms }: { terms: Record<string, unknown> }) {
  return (
    <div className="mt-3 rounded-lg border border-amber-800/50 bg-amber-900/20 p-3">
      <p className="text-xs font-semibold text-amber-400 mb-2">Terms (confirm or change)</p>
      <div className="grid grid-cols-2 gap-1 text-xs">
        {Object.entries(terms).map(([key, val]) => (
          <div key={key} className="flex justify-between">
            <span className="text-zinc-500">{key.replace(/_/g, " ")}</span>
            <span className="text-zinc-300">{String(val)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function VendorSuggestions({ vendors }: { vendors: SuggestedVendor[] }) {
  return (
    <div className="mt-3 rounded-lg border border-zinc-700 bg-zinc-900 p-3">
      <p className="text-xs font-semibold text-green-400 mb-2">Suggested Vendors</p>
      {vendors.map((v, i) => (
        <div key={i} className="flex items-center justify-between py-1 text-xs border-b border-zinc-800/50 last:border-0">
          <span className="text-zinc-300">{v.vendor_name}</span>
          <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-zinc-500">{v.recommended_channel}</span>
        </div>
      ))}
    </div>
  );
}

function DispatchPlanCard({
  plan,
  rfxId,
  onConfirm,
  loading,
}: {
  plan: Array<Record<string, unknown>>;
  rfxId: number | null;
  onConfirm: (rfxId: number, plan: Array<Record<string, unknown>>) => void;
  loading: boolean;
}) {
  const [dispatched, setDispatched] = useState(false);

  const handleClick = () => {
    if (!rfxId) return;
    onConfirm(rfxId, plan);
    setDispatched(true);
  };

  return (
    <div className="mt-3 rounded-lg border border-blue-800/50 bg-blue-900/20 p-3">
      <p className="text-xs font-semibold text-blue-400 mb-2">Dispatch Plan</p>
      {plan.map((entry, i) => (
        <div key={i} className="flex items-center justify-between py-1 text-xs border-b border-blue-800/30 last:border-0">
          <span className="text-zinc-300">{String(entry.vendor_name)}</span>
          <div className="flex items-center gap-2">
            <span className="text-zinc-500">via {String(entry.channel)}</span>
            <span className="text-zinc-600 text-[10px]">{String(entry.channel_detail)}</span>
          </div>
        </div>
      ))}
      {!dispatched && rfxId && (
        <button
          type="button"
          disabled={loading}
          onClick={handleClick}
          className="mt-3 w-full rounded-lg bg-green-600 px-3 py-2 text-xs font-medium text-white transition hover:bg-green-500 disabled:opacity-50"
        >
          {loading ? "Dispatching..." : "Confirm & Dispatch to Vendors"}
        </button>
      )}
      {!rfxId && !dispatched && (
        <p className="mt-2 text-[10px] text-zinc-500">Create the RFx first before dispatching</p>
      )}
    </div>
  );
}
