import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type InboxStatus = "invited" | "viewed" | "quoted" | "declined" | "expired";

interface InboxItem {
  rfx_id: string;
  title: string;
  status: InboxStatus;
  dispatched_at: string;
  deadline: string;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

const STATUS_COLORS: Record<InboxStatus, string> = {
  invited: "bg-blue-600/20 text-blue-400",
  viewed: "bg-zinc-700/40 text-zinc-400",
  quoted: "bg-green-600/20 text-green-400",
  declined: "bg-red-600/20 text-red-400",
  expired: "bg-zinc-600/20 text-zinc-600",
};

function formatDate(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatCountdown(deadline: string): { text: string; urgent: boolean } {
  if (!deadline) return { text: "No deadline", urgent: false };
  const diff = new Date(deadline).getTime() - Date.now();
  if (isNaN(diff) || diff <= 0) return { text: "Expired", urgent: true };

  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(hours / 24);
  const remainingHours = hours % 24;

  if (days > 0) {
    return {
      text: `${days}d ${remainingHours}h left`,
      urgent: days <= 1,
    };
  }
  return { text: `${hours}h left`, urgent: true };
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function VendorInbox() {
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery<InboxItem[]>({
    queryKey: ["vendor", "inbox"],
    queryFn: () => api.get<InboxItem[]>("/api/vendor/inbox"),
  });

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-zinc-100">Inbox</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Active RFx invitations and conversation threads.
        </p>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="flex gap-1">
            <span className="h-2 w-2 rounded-full bg-zinc-500 animate-bounce [animation-delay:0ms]" />
            <span className="h-2 w-2 rounded-full bg-zinc-500 animate-bounce [animation-delay:150ms]" />
            <span className="h-2 w-2 rounded-full bg-zinc-500 animate-bounce [animation-delay:300ms]" />
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-800/50 bg-red-900/20 px-4 py-3">
          <p className="text-sm text-red-400">
            Failed to load inbox.{" "}
            {error instanceof Error ? error.message : "Please try again."}
          </p>
        </div>
      )}

      {data && data.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-zinc-800">
            <svg className="h-6 w-6 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 9v.906a2.25 2.25 0 01-1.183 1.981l-6.478 3.488M2.25 9v.906a2.25 2.25 0 001.183 1.981l6.478 3.488m8.839 2.51l-4.66-2.51m0 0l-1.023-.55a2.25 2.25 0 00-2.134 0l-1.022.55m0 0l-4.661 2.51" />
            </svg>
          </div>
          <p className="text-sm text-zinc-400">No RFx invitations yet.</p>
          <p className="mt-1 text-xs text-zinc-600">
            When a buyer sends you an RFx, it will appear here.
          </p>
        </div>
      )}

      {data && data.length > 0 && (
        <div className="space-y-2">
          {data.map((item) => {
            const countdown = formatCountdown(item.deadline);
            return (
              <button
                key={item.rfx_id}
                onClick={() => navigate(`/vendor/rfx/${item.rfx_id}`)}
                className="flex w-full items-center gap-4 rounded-lg border border-zinc-800 bg-zinc-900 px-5 py-4 text-left transition hover:border-zinc-700 hover:bg-zinc-800/60"
              >
                {/* Title and meta */}
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-zinc-100">
                    {item.title}
                  </p>
                  <p className="mt-1 text-xs text-zinc-500">
                    Dispatched {formatDate(item.dispatched_at)}
                  </p>
                </div>

                {/* Status badge */}
                <span
                  className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${STATUS_COLORS[item.status]}`}
                >
                  {item.status}
                </span>

                {/* Deadline / countdown */}
                <div className="shrink-0 text-right">
                  <p className="text-xs text-zinc-500">
                    {formatDate(item.deadline)}
                  </p>
                  <p
                    className={`text-[11px] font-medium ${
                      countdown.urgent ? "text-amber-400" : "text-zinc-500"
                    }`}
                  >
                    {countdown.text}
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
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
