export type RfxStatus =
  | "drafting"
  | "awaiting_approval"
  | "dispatched"
  | "collecting"
  | "comparing"
  | "awarded"
  | "closed"
  | "cancelled";

export type KycStatus = "approved" | "pending" | "rejected";

export type UserRole = "buyer" | "vendor" | "admin";

export type UserStatus = "active" | "inactive" | "suspended";

export interface RfxLineItem {
  sku_code: string;
  sku_name: string;
  qty: number;
  unit: string;
  target_price?: number;
}

export interface RfxSummary {
  id: number;
  title: string;
  status: RfxStatus;
  vendor_count: number;
  deadline: string;
  created_at: string;
  line_items?: RfxLineItem[];
}

export interface Vendor {
  id: number;
  name: string;
  email?: string;
  primary_email?: string;
  category_ids_csv?: string;
  categories?: string;
  performance_score: number;
  kyc_status: KycStatus;
  preferred_rank: number;
}

export interface UserRecord {
  id: number;
  display_name: string;
  email: string;
  role: UserRole;
  status: UserStatus;
  created_at: string;
}

export interface ActivityEntry {
  id: number;
  action: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface AuditEntry {
  id: number;
  action: string;
  actor_name: string;
  actor_role: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, unknown>;
  created_at: string;
}
