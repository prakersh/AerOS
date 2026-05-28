import { useState, useRef, useEffect, useCallback, type FormEvent, type KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/api/client";
import { ConfirmDialog, VoiceInput, showToast } from "@/components/ui";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
  data?: Record<string, unknown>;
  timestamp: Date;
  attachment?: { name: string; url?: string };
  failed?: boolean;
  /** Original user text so we can re-send on retry */
  retryOf?: string;
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

/* ------------------------------------------------------------------ */
/* Persistence                                                          */
/* ------------------------------------------------------------------ */

const CHAT_STORAGE_KEY = "aeros-chat-messages";

function loadPersistedMessages(): ChatMsg[] {
  try {
    const raw = localStorage.getItem(CHAT_STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw).map((m: Record<string, unknown>) => ({
      ...m,
      timestamp: new Date(m.timestamp as string),
    }));
  } catch {
    return [];
  }
}

/* ------------------------------------------------------------------ */
/* Markdown renderer (lightweight, regex-based)                         */
/* ------------------------------------------------------------------ */

function renderMarkdown(text: string): string {
  let html = text
    // Escape HTML
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Code blocks (``` ... ```)
  html = html.replace(/```([\s\S]*?)```/g, '<pre class="my-1 rounded bg-zinc-900 p-2 text-xs overflow-x-auto"><code>$1</code></pre>');

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code class="rounded bg-zinc-900 px-1 py-0.5 text-xs text-indigo-300">$1</code>');

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Italic
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

  // Links [text](url)
  html = html.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-indigo-400 underline hover:text-indigo-300">$1</a>',
  );

  // Numbered lists
  html = html.replace(
    /(^|\n)(\d+)\.\s+(.*?)(?=\n\d+\.|\n\n|$)/g,
    (_match, prefix, _num, content) => `${prefix}<div class="ml-4">${_num}. ${content}</div>`,
  );

  // Unordered lists (- or *)
  html = html.replace(
    /(^|\n)[-*]\s+(.*?)(?=\n[-*]\s|\n\n|$)/g,
    (_match, prefix, content) => `${prefix}<div class="ml-4">&bull; ${content}</div>`,
  );

  // Paragraphs: double newline
  html = html.replace(/\n\n/g, "</p><p class=\"mt-2\">");

  // Single newlines
  html = html.replace(/\n/g, "<br/>");

  return html;
}

/** Render message content: plain text for user, markdown for assistant */
function MessageContent({ role, content }: { role: "user" | "assistant"; content: string }) {
  if (role === "user") {
    return <p className="text-sm whitespace-pre-wrap">{content}</p>;
  }
  return (
    <div
      className="text-sm [&_pre]:whitespace-pre-wrap [&_a]:break-all"
      dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
    />
  );
}

/* ------------------------------------------------------------------ */
/* Quick-action prompt chips                                            */
/* ------------------------------------------------------------------ */

const INITIAL_PROMPTS = [
  "I need 150kg tomatoes",
  "Create an RFx for office supplies",
  "Reorder from last week",
];

function getContextualPrompts(messages: ChatMsg[]): string[] {
  if (messages.length === 0) return INITIAL_PROMPTS;

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
  if (!lastAssistant) return [];

  // Contextual suggestions based on conversation state
  if (lastAssistant.data?.draft && !lastAssistant.data?.rfx_id) {
    return ["Confirm the draft", "Change quantities", "Add more items"];
  }
  if (lastAssistant.data?.rfx_id && lastAssistant.data?.status === "created") {
    return ["Show dispatch plan", "Add more vendors", "View RFx details"];
  }
  if (lastAssistant.data?.suggested_vendors) {
    return ["Confirm vendors", "Add another vendor", "Change delivery date"];
  }
  if (lastAssistant.data?.dispatch_plan) {
    return ["Confirm dispatch", "Modify dispatch plan"];
  }

  return [];
}

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function ChatCopilot() {
  const [messages, setMessages] = useState<ChatMsg[]>(loadPersistedMessages);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [createdRfxId, setCreatedRfxId] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const queueRef = useRef<string[]>([]);
  const processingRef = useRef(false);

  /* File attachment state */
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [pendingFilePreview, setPendingFilePreview] = useState<string | null>(null);

  /* Confirmation dialog state */
  const [confirmDraftOpen, setConfirmDraftOpen] = useState(false);
  const [pendingDraft, setPendingDraft] = useState<Record<string, unknown> | null>(null);
  const [confirmDispatchOpen, setConfirmDispatchOpen] = useState(false);
  const [pendingDispatch, setPendingDispatch] = useState<{
    rfxId: number;
    plan: Array<Record<string, unknown>>;
  } | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    try {
      localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
    } catch {
      // storage full — silently drop
    }
  }, [messages]);

  /* ---------------------------------------------------------------- */
  /* File upload helpers                                                */
  /* ---------------------------------------------------------------- */

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPendingFile(file);
    // Show preview for images, otherwise just the name
    if (file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = () => setPendingFilePreview(reader.result as string);
      reader.readAsDataURL(file);
    } else {
      setPendingFilePreview(null);
    }
    // Reset the input so the same file can be re-selected
    e.target.value = "";
  }, []);

  const clearPendingFile = useCallback(() => {
    setPendingFile(null);
    setPendingFilePreview(null);
  }, []);

  const uploadFile = useCallback(async (file: File): Promise<{ url: string; name: string } | null> => {
    try {
      const resp = await api.upload<{ url?: string; file_url?: string; name?: string }>("/api/chat/upload", file);
      return {
        url: resp.url ?? resp.file_url ?? "",
        name: resp.name ?? file.name,
      };
    } catch {
      showToast(`Failed to upload ${file.name}`, "error");
      return null;
    }
  }, []);

  /* ---------------------------------------------------------------- */
  /* Send / queue logic                                                 */
  /* ---------------------------------------------------------------- */

  const drainQueue = useCallback(async (currentMessages: ChatMsg[]) => {
    if (processingRef.current) return;
    if (queueRef.current.length === 0) {
      setLoading(false);
      return;
    }

    processingRef.current = true;
    const nextMsg = queueRef.current.shift()!;

    // Check if this is a retry (carries attachment info)
    const isRetry = nextMsg.startsWith("\x00RETRY\x00");
    const actualMsg = isRetry ? nextMsg.slice("\x00RETRY\x00".length) : nextMsg;

    // Determine if there's a pending file for this message
    const fileForMsg = !isRetry ? pendingFile : null;

    // Upload file first if present
    let attachment: ChatMsg["attachment"] | undefined;
    if (fileForMsg) {
      const uploaded = await uploadFile(fileForMsg);
      if (uploaded) {
        attachment = { name: uploaded.name, url: uploaded.url };
      }
      // Clear file state after upload attempt
      setPendingFile(null);
      setPendingFilePreview(null);
    }

    const userMsg: ChatMsg = {
      role: "user",
      content: actualMsg,
      timestamp: new Date(),
      attachment,
    };

    const updatedMessages = [...currentMessages, userMsg];
    setMessages(updatedMessages);

    try {
      const history = updatedMessages
        .filter((m) => !m.failed)
        .map((m) => ({
          role: m.role,
          content: m.content,
        }));

      const body: Record<string, unknown> = { message: actualMsg, history };
      if (attachment?.url) {
        body.attachment_url = attachment.url;
        body.attachment_name = attachment.name;
      }

      const resp = await api.post<{
        message: string;
        data: Record<string, unknown>;
        success: boolean;
      }>("/api/chat", body);

      const assistantMsg: ChatMsg = {
        role: "assistant",
        content: resp.message,
        data: resp.data,
        timestamp: new Date(),
      };
      const afterResponse = [...updatedMessages, assistantMsg];
      setMessages(afterResponse);

      processingRef.current = false;
      await drainQueue(afterResponse);
    } catch (err: unknown) {
      const errMsg =
        err && typeof err === "object" && "message" in err
          ? String((err as { message: string }).message)
          : "Failed to get response";
      const afterError = [
        ...updatedMessages,
        {
          role: "assistant" as const,
          content: `Error: ${errMsg}`,
          timestamp: new Date(),
          failed: true,
          retryOf: actualMsg,
        },
      ];
      setMessages(afterError);

      processingRef.current = false;
      await drainQueue(afterError);
    }
  }, [pendingFile, uploadFile]);

  const sendMessage = useCallback((text?: string) => {
    const msgText = text ?? input.trim();
    if (!msgText) return;

    queueRef.current.push(msgText);
    setInput("");
    setPendingFile(null);
    setPendingFilePreview(null);

    if (!processingRef.current) {
      setLoading(true);
      setMessages((prev) => {
        drainQueue(prev);
        return prev;
      });
    }
  }, [input, drainQueue]);

  const handleSubmit = useCallback((e: FormEvent) => {
    e.preventDefault();
    sendMessage();
  }, [sendMessage]);

  /* ---------------------------------------------------------------- */
  /* Ctrl+Enter / Cmd+Enter handler                                     */
  /* ---------------------------------------------------------------- */

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLInputElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  }, [sendMessage]);

  /* ---------------------------------------------------------------- */
  /* Retry a failed message                                             */
  /* ---------------------------------------------------------------- */

  const handleRetry = useCallback((failedMsg: ChatMsg) => {
    if (!failedMsg.retryOf) return;
    // Remove the failed assistant message and the preceding user message
    setMessages((prev) => {
      const idx = prev.indexOf(failedMsg);
      if (idx === -1) return prev;
      // Remove the failed message and its preceding user message
      const filtered = prev.filter((_, i) => i !== idx && i !== idx - 1);
      return filtered;
    });
    // Re-send with a marker so drainQueue knows this is a retry
    queueRef.current.push(`\x00RETRY\x00${failedMsg.retryOf}`);
    if (!processingRef.current) {
      setLoading(true);
      setMessages((prev) => {
        drainQueue(prev);
        return prev;
      });
    }
  }, [drainQueue]);

  /* ---------------------------------------------------------------- */
  /* Voice input                                                        */
  /* ---------------------------------------------------------------- */

  const handleVoiceResult = useCallback((text: string) => {
    setInput((prev) => (prev ? `${prev} ${text}` : text));
    inputRef.current?.focus();
  }, []);

  /* ---------------------------------------------------------------- */
  /* Quick-action chip click                                            */
  /* ---------------------------------------------------------------- */

  const handleChipClick = useCallback((text: string) => {
    // Some chips are contextual actions, not raw messages
    if (text === "View RFx details" && createdRfxId) {
      navigate(`/buyer/rfx/${createdRfxId}`);
      return;
    }
    setInput(text);
    inputRef.current?.focus();
  }, [createdRfxId, navigate]);

  /* ---------------------------------------------------------------- */
  /* Draft confirmation handlers                                        */
  /* ---------------------------------------------------------------- */

  function handleDraftConfirmClick(draft: Record<string, unknown>) {
    setPendingDraft(draft);
    setConfirmDraftOpen(true);
  }

  async function handleConfirmDraft() {
    if (!pendingDraft) return;
    setConfirmDraftOpen(false);
    setActionLoading(true);
    try {
      const resp = await api.post<{
        message: string;
        data: Record<string, unknown>;
        success: boolean;
      }>("/api/chat/create-rfx", { draft: pendingDraft });

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
        { role: "assistant", content: `Error: ${errMsg}`, timestamp: new Date(), failed: true },
      ]);
    } finally {
      setActionLoading(false);
      setPendingDraft(null);
    }
  }

  /* ---------------------------------------------------------------- */
  /* Dispatch confirmation handlers                                     */
  /* ---------------------------------------------------------------- */

  function handleDispatchConfirmClick(
    rfxId: number,
    plan: Array<Record<string, unknown>>,
  ) {
    setPendingDispatch({ rfxId, plan });
    setConfirmDispatchOpen(true);
  }

  async function handleConfirmDispatch() {
    if (!pendingDispatch) return;
    setConfirmDispatchOpen(false);
    setActionLoading(true);
    try {
      const resp = await api.post<{
        message: string;
        data: Record<string, unknown>;
        success: boolean;
      }>("/api/chat/dispatch", {
        rfx_id: pendingDispatch.rfxId,
        dispatch_plan: pendingDispatch.plan,
      });

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
        { role: "assistant", content: `Error: ${errMsg}`, timestamp: new Date(), failed: true },
      ]);
    } finally {
      setActionLoading(false);
      setPendingDispatch(null);
    }
  }

  /* ---------------------------------------------------------------- */
  /* Derived state                                                      */
  /* ---------------------------------------------------------------- */

  const isAgentBusy = loading || processingRef.current;
  const queueLen = queueRef.current.length;
  const contextualPrompts = getContextualPrompts(messages);
  const showPrompts = messages.length === 0 || contextualPrompts.length > 0;

  /* ---------------------------------------------------------------- */
  /* Render                                                             */
  /* ---------------------------------------------------------------- */

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="shrink-0 border-b border-zinc-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">Chat Co-pilot</h1>
          <p className="text-xs text-zinc-500">
            Tell me what you need — I&apos;ll draft the purchase request.
          </p>
        </div>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={() => { setMessages([]); localStorage.removeItem(CHAT_STORAGE_KEY); queueRef.current = []; setCreatedRfxId(null); }}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition"
          >
            Clear chat
          </button>
        )}
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {/* Empty state */}
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center animate-fade-in">
            <div className="text-center max-w-md">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600/10 ring-1 ring-indigo-600/20">
                <svg className="h-7 w-7 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                </svg>
              </div>
              <h3 className="text-base font-semibold text-zinc-200">
                What do you need to procure?
              </h3>
              <p className="text-zinc-500 text-xs mt-2 leading-relaxed">
                Tell me in plain language — I&apos;ll draft the purchase request, find vendors, and handle dispatch.
              </p>
              <p className="text-zinc-600 text-[11px] mt-3 italic">
                e.g. &quot;I need 150kg tomatoes, 80kg onions, and 500L milk by tomorrow 5 AM&quot;
              </p>
            </div>
          </div>
        )}

        {/* Quick-action prompt chips */}
        {showPrompts && contextualPrompts.length > 0 && (
          <div className="flex flex-wrap gap-2 justify-center">
            {contextualPrompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => handleChipClick(prompt)}
                className="rounded-full border border-zinc-700 bg-zinc-800/50 px-3 py-1.5 text-xs text-zinc-400 hover:border-indigo-500 hover:text-indigo-300 transition"
              >
                {prompt}
              </button>
            ))}
          </div>
        )}

        {/* Message bubbles */}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white"
                  : msg.failed
                    ? "bg-red-900/30 border border-red-800/50 text-zinc-200"
                    : "bg-zinc-800 text-zinc-200"
              }`}
            >
              {/* Attachment bubble */}
              {msg.attachment && (
                <div className="mb-2 flex items-center gap-2 rounded-lg bg-zinc-900/50 px-3 py-2">
                  {msg.attachment.url ? (
                    <a
                      href={msg.attachment.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-xs text-indigo-400 hover:text-indigo-300"
                    >
                      <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
                      </svg>
                      <span className="truncate max-w-[200px]">{msg.attachment.name}</span>
                    </a>
                  ) : (
                    <div className="flex items-center gap-2 text-xs text-zinc-400">
                      <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
                      </svg>
                      <span className="truncate max-w-[200px]">{msg.attachment.name}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Message content with markdown for assistant */}
              <MessageContent role={msg.role} content={msg.content} />

              {/* Data-driven sub-components */}
              {!!msg.data?.draft && (
                <DraftCard
                  draft={msg.data.draft as Record<string, unknown>}
                  onConfirm={handleDraftConfirmClick}
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
                  onConfirm={handleDispatchConfirmClick}
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

              {/* Retry button for failed messages */}
              {msg.failed && msg.retryOf && (
                <button
                  type="button"
                  onClick={() => handleRetry(msg)}
                  className="mt-2 flex items-center gap-1.5 text-xs text-red-400 hover:text-red-300 transition"
                >
                  <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
                  </svg>
                  Retry
                </button>
              )}

              <p className="text-[10px] mt-1 opacity-50">
                {msg.timestamp.toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-zinc-800 rounded-xl px-4 py-3">
              <div className="flex gap-1 items-center">
                <span className="h-2 w-2 rounded-full bg-zinc-500 animate-bounce [animation-delay:0ms]" />
                <span className="h-2 w-2 rounded-full bg-zinc-500 animate-bounce [animation-delay:150ms]" />
                <span className="h-2 w-2 rounded-full bg-zinc-500 animate-bounce [animation-delay:300ms]" />
                {queueLen > 0 && (
                  <span className="ml-2 text-[10px] text-zinc-500">
                    +{queueLen} queued
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Attachment preview bar */}
      {pendingFile && (
        <div className="shrink-0 border-t border-zinc-800 bg-zinc-900 px-6 py-2 flex items-center gap-3">
          {pendingFilePreview ? (
            <img src={pendingFilePreview} alt="" className="h-10 w-10 rounded object-cover" />
          ) : (
            <div className="flex h-10 w-10 items-center justify-center rounded bg-zinc-800">
              <svg className="h-5 w-5 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-xs text-zinc-300 truncate">{pendingFile.name}</p>
            <p className="text-[10px] text-zinc-500">{(pendingFile.size / 1024).toFixed(1)} KB</p>
          </div>
          <button
            type="button"
            onClick={clearPendingFile}
            className="rounded p-1 text-zinc-500 hover:text-zinc-300 transition"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Input area */}
      <form onSubmit={handleSubmit} className="shrink-0 border-t border-zinc-800 px-6 py-4">
        <div className="flex gap-2 items-end">
          {/* File upload button */}
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleFileSelect}
            accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.txt,.png,.jpg,.jpeg,.webp"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="shrink-0 rounded-lg p-2.5 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition"
            title="Attach file"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
            </svg>
          </button>

          {/* Text input */}
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isAgentBusy ? "Type to queue message..." : "Type your procurement request... (Ctrl+Enter to send)"}
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />

          {/* Voice input button */}
          <VoiceInput onResult={handleVoiceResult} className="shrink-0" />

          {/* Send button */}
          <button
            type="submit"
            disabled={!input.trim() && !pendingFile}
            className="shrink-0 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
          >
            Send
          </button>
        </div>
        <p className="mt-1.5 text-[10px] text-zinc-600">
          Press <kbd className="rounded border border-zinc-700 bg-zinc-800 px-1 py-0.5 text-[10px]">Enter</kbd> or click Send &middot; Attach files with the clip icon &middot; Voice input supported
        </p>
      </form>

      {/* Draft Confirmation Dialog */}
      <ConfirmDialog
        open={confirmDraftOpen}
        onClose={() => {
          setConfirmDraftOpen(false);
          setPendingDraft(null);
        }}
        onConfirm={handleConfirmDraft}
        title="Create RFx?"
        message="Create this RFx? This will create the RFx and make it available for dispatch."
        confirmLabel="Create RFx"
        confirmVariant="primary"
        isPending={actionLoading}
      />

      {/* Dispatch Confirmation Dialog */}
      <ConfirmDialog
        open={confirmDispatchOpen}
        onClose={() => {
          setConfirmDispatchOpen(false);
          setPendingDispatch(null);
        }}
        onConfirm={handleConfirmDispatch}
        title="Dispatch to Vendors?"
        message="Dispatch to vendors? This will send the RFx to all listed vendors."
        confirmLabel="Dispatch"
        confirmVariant="primary"
        isPending={actionLoading}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Sub-components                                                      */
/* ------------------------------------------------------------------ */

/** Normalize draft items from various agent response shapes into a uniform list. */
function normalizeDraftItems(draft: Record<string, unknown>): DraftLineItem[] {
  // Try line_items first (expected shape), then items (agent shape)
  const raw =
    (draft.line_items as Array<Record<string, unknown>>) ??
    (draft.items as Array<Record<string, unknown>>) ??
    [];
  return raw.map((item) => ({
    sku_name: String(item.sku_name ?? item.name ?? item.item_name ?? ""),
    qty: Number(item.qty ?? item.quantity ?? item.count ?? 0),
    unit: String(item.unit ?? item.unit_override ?? "pcs"),
    target_price:
      item.target_price != null ? Number(item.target_price) :
      item.est_unit_price != null ? Number(item.est_unit_price) :
      item.last_price != null ? Number(item.last_price) :
      item.price != null ? Number(item.price) :
      undefined,
  }));
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
  const items = normalizeDraftItems(draft);
  const totalItems = (draft.total_items as number) ?? items.length;
  const totalEst = draft.total_estimated as number | undefined;

  return (
    <div className="mt-3 rounded-lg border border-zinc-700 bg-zinc-900 p-3">
      <p className="text-xs font-semibold text-indigo-400 mb-2">
        Draft RFQ {totalItems > 0 ? `(${totalItems} items)` : ""}
      </p>
      {!!draft.title && <p className="text-xs text-zinc-300 mb-2">{String(draft.title)}</p>}
      {items.length > 0 ? (
        <table className="w-full text-xs">
          <thead>
            <tr className="text-zinc-500 border-b border-zinc-800">
              <th className="text-left py-1">Item</th>
              <th className="text-right py-1">Qty</th>
              <th className="text-right py-1">Unit</th>
              <th className="text-right py-1">Price</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, i) => (
              <tr key={i} className="border-b border-zinc-800/50">
                <td className="py-1 text-zinc-300">{item.sku_name}</td>
                <td className="py-1 text-right text-zinc-300">{item.qty}</td>
                <td className="py-1 text-right text-zinc-400">{item.unit}</td>
                <td className="py-1 text-right text-zinc-400">
                  {item.target_price != null ? `₹${item.target_price}` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="text-xs text-zinc-500 italic">No items in draft yet</p>
      )}
      {totalEst != null && totalEst > 0 && (
        <p className="text-xs text-zinc-400 mt-1 text-right">
          Est. Total: ₹{totalEst.toLocaleString()}
        </p>
      )}
      {!confirmed && (
        <button
          type="button"
          disabled={loading || items.length === 0}
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
