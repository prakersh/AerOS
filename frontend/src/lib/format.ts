/** Relative timestamp: "Just now", "5m ago", "2h ago", or formatted date */
export function formatTimestamp(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  const diff = Date.now() - d.getTime();
  if (diff < 60_000) return "Just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** Absolute timestamp in Indian locale */
export function formatTimestampAbsolute(iso: string): string {
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

/** Currency formatter (default INR) */
export function formatCurrency(
  amount: number | null,
  currency = "INR",
): string {
  if (amount == null) return "--";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(amount);
}

/** Date-only formatter */
export function formatDate(iso: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** File size formatter */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1_048_576).toFixed(1)} MB`;
}

/** Time remaining until deadline */
export function formatTimeRemaining(deadline: string): string {
  if (!deadline) return "No deadline";
  const diff = new Date(deadline).getTime() - Date.now();
  if (isNaN(diff) || diff <= 0) return "Expired";
  const hours = Math.floor(diff / 3_600_000);
  const minutes = Math.floor((diff % 3_600_000) / 60_000);
  if (hours >= 24) {
    const days = Math.floor(hours / 24);
    return `${days}d ${hours % 24}h left`;
  }
  return `${hours}h ${minutes}m left`;
}

/** Cost formatter (USD with 4 decimal places) */
export function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`;
}

/** Percent formatter */
export function formatPercent(rate: number): string {
  return `${rate.toFixed(1)}%`;
}

/** Countdown formatter for vendor inbox */
export function formatCountdown(iso: string): string {
  if (!iso) return "";
  const diff = new Date(iso).getTime() - Date.now();
  if (isNaN(diff) || diff <= 0) return "Expired";
  const hours = Math.floor(diff / 3_600_000);
  if (hours >= 24) {
    const days = Math.floor(hours / 24);
    return `${days}d left`;
  }
  const minutes = Math.floor((diff % 3_600_000) / 60_000);
  return `${hours}h ${minutes}m left`;
}
