const BADGE_VARIANTS = {
  rfx: {
    drafting: "bg-zinc-700/50 text-zinc-300",
    dispatched: "bg-blue-900/40 text-blue-400",
    collecting: "bg-amber-900/40 text-amber-400",
    comparing: "bg-indigo-900/40 text-indigo-400",
    awarded: "bg-green-900/40 text-green-400",
    cancelled: "bg-red-900/40 text-red-400",
  } as Record<string, string>,
  kyc: {
    approved: "bg-green-900/40 text-green-400",
    pending: "bg-amber-900/40 text-amber-400",
    rejected: "bg-red-900/40 text-red-400",
  } as Record<string, string>,
  "user-role": {
    buyer: "bg-indigo-900/40 text-indigo-400",
    vendor: "bg-green-900/40 text-green-400",
    admin: "bg-amber-900/40 text-amber-400",
  } as Record<string, string>,
  "user-status": {
    active: "bg-green-900/40 text-green-400",
    inactive: "bg-zinc-700/50 text-zinc-400",
    suspended: "bg-red-900/40 text-red-400",
  } as Record<string, string>,
  provider: {
    active: "bg-green-900/40 text-green-400",
    inactive: "bg-zinc-700/50 text-zinc-400",
    error: "bg-red-900/40 text-red-400",
    disabled: "bg-zinc-700/50 text-zinc-400",
  } as Record<string, string>,
  lane: {
    invited: "bg-blue-900/40 text-blue-400",
    viewed: "bg-zinc-700/50 text-zinc-300",
    quoted: "bg-green-900/40 text-green-400",
    declined: "bg-red-900/40 text-red-400",
    expired: "bg-zinc-700/50 text-zinc-500",
  } as Record<string, string>,
  health: {
    healthy: "bg-green-900/40 text-green-400",
    degraded: "bg-amber-900/40 text-amber-400",
    down: "bg-red-900/40 text-red-400",
  } as Record<string, string>,
};

interface StatusBadgeProps {
  status: string;
  variant?: keyof typeof BADGE_VARIANTS;
  className?: string;
}

export default function StatusBadge({
  status,
  variant = "rfx",
  className = "",
}: StatusBadgeProps) {
  const styles =
    BADGE_VARIANTS[variant]?.[status.toLowerCase()] ??
    "bg-zinc-700/50 text-zinc-300";

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${styles} ${className}`}
    >
      {status}
    </span>
  );
}
