/**
 * Human-facing labels — turns internal enums and status codes into plain
 * business language. Mirrors src/aeros/ai/labels.py on the backend.
 *
 * A user who has never heard "RFx" should understand every string we show.
 */

/** snake_case / lowercase -> "Readable label". */
export function humanize(text: string): string {
  const t = (text ?? "").replace(/_/g, " ").trim();
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : t;
}

const RFX_STATUS_LABELS: Record<string, string> = {
  drafting: "Draft",
  awaiting_approval: "Awaiting approval",
  dispatched: "Sent to vendors",
  collecting: "Collecting quotes",
  comparing: "Comparing quotes",
  awarded: "Awarded",
  closed: "Closed",
  cancelled: "Cancelled",
};

const VENDOR_STATUS_LABELS: Record<string, string> = {
  invited: "Invited",
  viewed: "Viewed",
  quoted: "Quoted",
  declined: "Declined",
  expired: "Expired",
};

const CHANNEL_LABELS: Record<string, string> = {
  in_app: "Portal",
  email: "Email",
  telegram: "Chat",
};

const EXTRACTION_LABELS: Record<string, string> = {
  pending: "Processing",
  extracted: "Ready",
  failed: "Couldn't read",
};

const SENDER_LABELS: Record<string, string> = {
  buyer: "You",
  vendor: "Vendor",
  system: "System",
  agent: "Copilot",
};

export function rfxStatusLabel(status: string): string {
  return RFX_STATUS_LABELS[(status ?? "").toLowerCase()] ?? humanize(status);
}

export function channelLabel(channel: string): string {
  return CHANNEL_LABELS[(channel ?? "").toLowerCase()] ?? humanize(channel);
}

export function extractionLabel(status: string): string {
  return EXTRACTION_LABELS[(status ?? "").toLowerCase()] ?? humanize(status);
}

export function senderLabel(kind: string): string {
  return SENDER_LABELS[(kind ?? "").toLowerCase()] ?? humanize(kind);
}

/** Label for a StatusBadge, chosen by its variant. */
export function badgeLabel(status: string, variant: string): string {
  const key = (status ?? "").toLowerCase();
  if (variant === "rfx") return RFX_STATUS_LABELS[key] ?? humanize(status);
  if (variant === "lane") return VENDOR_STATUS_LABELS[key] ?? humanize(status);
  return humanize(status);
}
