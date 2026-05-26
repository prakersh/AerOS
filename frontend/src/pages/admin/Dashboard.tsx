import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface AdminStats {
  total_users: number;
  total_rfx: number;
  total_vendors: number;
  total_offers: number;
  total_extractions: number;
}

interface AuditEntry {
  id: number;
  action: string;
  actor_name: string;
  actor_role: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, unknown>;
  created_at: string;
}

interface SystemService {
  name: string;
  status: "healthy" | "degraded" | "down";
  detail: string;
}

/* ------------------------------------------------------------------ */
/* Sub-components                                                      */
/* ------------------------------------------------------------------ */

function KpiCard({
  label,
  value,
  accent = "text-zinc-100",
}: {
  label: string;
  value: number;
  accent?: string;
}) {
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

const HEALTH_STYLES: Record<SystemService["status"], string> = {
  healthy: "bg-green-900/40 text-green-400",
  degraded: "bg-amber-900/40 text-amber-400",
  down: "bg-red-900/40 text-red-400",
};

const SERVICES: SystemService[] = [
  { name: "API", status: "healthy", detail: "All endpoints responding" },
  { name: "AI Provider", status: "healthy", detail: "NVIDIA NIM" },
  { name: "Database", status: "healthy", detail: "SQLite (WAL mode)" },
];

function formatTimestamp(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function actionLabel(entry: AuditEntry): string {
  const details = entry.details;
  switch (entry.action) {
    case "create_rfx":
      return `Created RFx "${details.title ?? entry.entity_id}"`;
    case "dispatch_rfx":
      return `Dispatched RFx #${entry.entity_id} to ${details.vendor_count ?? "?"} vendors`;
    case "cancel_rfx":
      return `Cancelled RFx #${entry.entity_id}`;
    case "award_rfx":
      return `Awarded RFx #${entry.entity_id}`;
    case "override_offer_field":
      return `Override on Offer #${entry.entity_id}`;
    default:
      return `${entry.action} on ${entry.entity_type} #${entry.entity_id}`;
  }
}

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function AdminDashboard() {
  const { data: stats } = useQuery<AdminStats>({
    queryKey: ["admin", "stats"],
    queryFn: () => api.get<AdminStats>("/api/admin/stats"),
  });

  const { data: audit = [] } = useQuery<AuditEntry[]>({
    queryKey: ["admin", "audit"],
    queryFn: () => api.get<AuditEntry[]>("/api/admin/audit"),
  });

  const recentAudit = audit.slice(0, 5);

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100">
          Admin Dashboard
        </h1>
        <p className="mt-1 text-sm text-zinc-500">
          System-wide metrics, user activity, and AI usage.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Total Users" value={stats?.total_users ?? 0} accent="text-indigo-400" />
        <KpiCard label="Total RFx" value={stats?.total_rfx ?? 0} accent="text-blue-400" />
        <KpiCard label="Active Vendors" value={stats?.total_vendors ?? 0} accent="text-green-400" />
        <KpiCard label="AI Extractions" value={stats?.total_extractions ?? 0} accent="text-amber-400" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 rounded-xl border border-zinc-800 bg-zinc-900 p-5">
          <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-500">
            Recent Activity
          </h2>
          <div className="mt-4 space-y-3">
            {recentAudit.length === 0 && (
              <p className="text-sm text-zinc-600">No activity yet.</p>
            )}
            {recentAudit.map((entry) => (
              <div
                key={entry.id}
                className="flex items-start justify-between gap-4 border-b border-zinc-800/60 pb-3 last:border-b-0 last:pb-0"
              >
                <div className="min-w-0">
                  <p className="text-sm text-zinc-200">{actionLabel(entry)}</p>
                  <p className="mt-0.5 text-xs text-zinc-500">{entry.actor_name}</p>
                </div>
                <span className="shrink-0 text-[11px] tabular-nums text-zinc-600">
                  {formatTimestamp(entry.created_at)}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
          <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-500">
            System Health
          </h2>
          <div className="mt-4 space-y-3">
            {SERVICES.map((svc) => (
              <div
                key={svc.name}
                className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-950 p-3"
              >
                <div>
                  <p className="text-sm font-medium text-zinc-200">{svc.name}</p>
                  <p className="mt-0.5 text-xs text-zinc-500">{svc.detail}</p>
                </div>
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${HEALTH_STYLES[svc.status]}`}
                >
                  {svc.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
