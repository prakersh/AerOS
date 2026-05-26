import { useState, useRef, useEffect, useCallback, type FormEvent, type DragEvent } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type SenderKind = "buyer" | "vendor" | "system" | "agent";
type Channel = "email" | "telegram" | "in_app";
type ExtractionStatus = "pending" | "extracted" | "failed";

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

type DeclineCategory = "out-of-stock" | "pricing" | "capacity" | "other";

/* ------------------------------------------------------------------ */
/* Sender / Channel / Extraction badge maps                            */
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

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

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
/* Sub-components                                                      */
/* ------------------------------------------------------------------ */

function MessageBubble({ msg }: { msg: ThreadMessage }) {
  const isSystem = msg.sender_kind === "system";

  if (isSystem) {
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
            className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium capitalize ${SENDER_COLORS[msg.sender_kind]}`}
          >
            {msg.sender_kind}
          </span>
          <span
            className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${CHANNEL_COLORS[msg.channel]}`}
          >
            {msg.channel.replace("_", " ")}
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

function FileUploadZone({
  rfxId,
  uploads,
  onUploadComplete,
}: {
  rfxId: string;
  uploads: UploadedFile[];
  onUploadComplete: () => void;
}) {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setUploading(true);
      setUploadError(null);
      try {
        await api.upload<UploadedFile>(
          `/api/vendor/rfx/${rfxId}/upload`,
          file,
        );
        onUploadComplete();
      } catch (err: unknown) {
        const msg =
          err && typeof err === "object" && "message" in err
            ? String((err as { message: string }).message)
            : "Upload failed";
        setUploadError(msg);
      } finally {
        setUploading(false);
      }
    },
    [rfxId, onUploadComplete],
  );

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(true);
  };

  const onDragLeave = () => setDragActive(false);

  const onBrowse = () => fileInputRef.current?.click();

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = "";
  };

  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
        Attachments
      </p>

      <div
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={onBrowse}
        className={`cursor-pointer rounded-lg border-2 border-dashed px-4 py-6 text-center transition ${
          dragActive
            ? "border-indigo-500 bg-indigo-600/10"
            : "border-zinc-700 bg-zinc-800/30 hover:border-zinc-600"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPT_TYPES}
          className="hidden"
          onChange={onFileChange}
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-2">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-zinc-600 border-t-indigo-500" />
            <p className="text-xs text-zinc-400">Uploading...</p>
          </div>
        ) : (
          <>
            <svg
              className="mx-auto h-6 w-6 text-zinc-600"
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
            <p className="mt-2 text-xs text-zinc-400">
              Drop file here or <span className="text-indigo-400">browse</span>
            </p>
            <p className="mt-1 text-[10px] text-zinc-600">
              PDF, Word, Excel, CSV, or images
            </p>
          </>
        )}
      </div>

      {uploadError && (
        <p className="mt-2 text-xs text-red-400">{uploadError}</p>
      )}

      {uploads.length > 0 && (
        <div className="mt-3 space-y-1.5">
          {uploads.map((f) => (
            <div
              key={f.id}
              className="flex items-center justify-between rounded-md bg-zinc-800/60 px-3 py-2"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs text-zinc-300">{f.filename}</p>
                <p className="text-[10px] text-zinc-600">
                  {formatFileSize(f.size_bytes)}
                </p>
              </div>
              <span
                className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium capitalize ${EXTRACTION_COLORS[f.extraction_status]}`}
              >
                {f.extraction_status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

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

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="mx-4 w-full max-w-md rounded-xl border border-zinc-800 bg-zinc-900 p-6 shadow-2xl">
        <h3 className="text-lg font-semibold text-zinc-100">Decline this RFx</h3>
        <p className="mt-1 text-xs text-zinc-500">
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
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main page                                                           */
/* ------------------------------------------------------------------ */

export default function VendorRFxReply() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const bottomRef = useRef<HTMLDivElement>(null);

  const [replyText, setReplyText] = useState("");
  const [declineOpen, setDeclineOpen] = useState(false);

  /* ----- data fetching ----- */
  const threadQuery = useQuery<ThreadMessage[]>({
    queryKey: ["vendor", "rfx", id, "thread"],
    queryFn: () => api.get<ThreadMessage[]>(`/api/vendor/rfx/${id}/thread`),
    enabled: !!id,
  });

  const uploadsQuery = useQuery<UploadedFile[]>({
    queryKey: ["vendor", "rfx", id, "uploads"],
    queryFn: () => api.get<UploadedFile[]>(`/api/vendor/rfx/${id}/uploads`),
    enabled: !!id,
  });

  /* ----- mutations ----- */
  const replyMutation = useMutation({
    mutationFn: (body_text: string) =>
      api.post(`/api/vendor/rfx/${id}/reply`, { body_text }),
    onSuccess: () => {
      setReplyText("");
      queryClient.invalidateQueries({ queryKey: ["vendor", "rfx", id, "thread"] });
    },
  });

  const declineMutation = useMutation({
    mutationFn: (payload: { reason: string; category: DeclineCategory }) =>
      api.post(`/api/vendor/rfx/${id}/decline`, payload),
    onSuccess: () => {
      setDeclineOpen(false);
      queryClient.invalidateQueries({ queryKey: ["vendor", "rfx", id, "thread"] });
      queryClient.invalidateQueries({ queryKey: ["vendor", "inbox"] });
    },
  });

  /* ----- auto-scroll on new messages ----- */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [threadQuery.data]);

  /* ----- handlers ----- */
  const handleSendReply = (e: FormEvent) => {
    e.preventDefault();
    if (!replyText.trim() || replyMutation.isPending) return;
    replyMutation.mutate(replyText.trim());
  };

  const handleDecline = (reason: string, category: DeclineCategory) => {
    declineMutation.mutate({ reason, category });
  };

  const handleUploadComplete = () => {
    queryClient.invalidateQueries({ queryKey: ["vendor", "rfx", id, "uploads"] });
  };

  return (
    <div className="flex h-full flex-col lg:flex-row">
      {/* ---- Left column: Thread ---- */}
      <div className="flex flex-1 flex-col border-b border-zinc-800 lg:border-b-0 lg:border-r">
        {/* Header */}
        <div className="shrink-0 border-b border-zinc-800 px-6 py-4">
          <h1 className="text-lg font-semibold text-zinc-100">
            RFx Thread
          </h1>
          <p className="text-xs text-zinc-500">RFx #{id}</p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {threadQuery.isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="flex gap-1">
                <span className="h-2 w-2 rounded-full bg-zinc-500 animate-bounce [animation-delay:0ms]" />
                <span className="h-2 w-2 rounded-full bg-zinc-500 animate-bounce [animation-delay:150ms]" />
                <span className="h-2 w-2 rounded-full bg-zinc-500 animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          )}

          {threadQuery.error && (
            <div className="rounded-lg border border-red-800/50 bg-red-900/20 px-4 py-3">
              <p className="text-sm text-red-400">Failed to load thread.</p>
            </div>
          )}

          {threadQuery.data?.length === 0 && (
            <div className="flex items-center justify-center py-12">
              <p className="text-sm text-zinc-500">No messages yet.</p>
            </div>
          )}

          {threadQuery.data?.map((msg) => (
            <MessageBubble key={msg.id} msg={msg} />
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* ---- Right column: Reply & Upload ---- */}
      <div className="flex w-full shrink-0 flex-col lg:w-96 xl:w-[420px]">
        {/* Reply */}
        <div className="border-b border-zinc-800 p-5">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Reply
          </p>
          <form onSubmit={handleSendReply}>
            <textarea
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              rows={4}
              placeholder="Type your reply..."
              className="w-full resize-none rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
            <div className="mt-2 flex items-center justify-between">
              {replyMutation.isError && (
                <p className="text-xs text-red-400">Failed to send.</p>
              )}
              <div className="flex-1" />
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

        {/* Upload */}
        <div className="flex-1 overflow-y-auto border-b border-zinc-800 p-5">
          <FileUploadZone
            rfxId={id ?? ""}
            uploads={uploadsQuery.data ?? []}
            onUploadComplete={handleUploadComplete}
          />
        </div>

        {/* Decline */}
        <div className="shrink-0 p-5">
          <button
            onClick={() => setDeclineOpen(true)}
            className="w-full rounded-lg border border-red-800/50 bg-red-900/20 px-4 py-2.5 text-sm font-medium text-red-400 transition hover:bg-red-900/40"
          >
            Decline this RFx
          </button>
        </div>
      </div>

      {/* Decline Modal */}
      <DeclineModal
        open={declineOpen}
        onClose={() => setDeclineOpen(false)}
        onConfirm={handleDecline}
        loading={declineMutation.isPending}
      />
    </div>
  );
}
