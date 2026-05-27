import { useEffect } from "react";
import { Routes, Route, Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";
import ProtectedRoute from "@/components/ProtectedRoute";
import { SidebarLayout, type NavSection } from "@/components/layouts/Sidebar";
import { TopBar } from "@/components/layouts/TopBar";
import {
  DashboardIcon, ChatIcon, InventoryIcon, VendorsIcon, ActivityIcon,
  ObservabilityIcon, SettingsIcon, InboxIcon, ProfileIcon, UsersIcon,
  AIIcon, AuditIcon, NegotiationIcon, ContractIcon, InvoiceIcon, AnalyticsIcon,
} from "@/components/layouts/icons";

import Login from "@/pages/auth/Login";
import Register from "@/pages/auth/Register";
import BuyerDashboard from "@/pages/buyer/Dashboard";
import ChatCopilot from "@/pages/buyer/ChatCopilot";
import Inventory from "@/pages/buyer/Inventory";
import BuyerVendors from "@/pages/buyer/Vendors";
import RFxDetail from "@/pages/buyer/RFxDetail";
import BuyerSettings from "@/pages/buyer/Settings";
import BuyerActivity from "@/pages/buyer/Activity";
import BuyerObservability from "@/pages/buyer/Observability";
import VendorInbox from "@/pages/vendor/Inbox";
import VendorRFxReply from "@/pages/vendor/RFxReply";
import VendorProfile from "@/pages/vendor/Profile";
import AdminDashboard from "@/pages/admin/Dashboard";
import AdminUsers from "@/pages/admin/Users";
import AdminAIProviders from "@/pages/admin/AIProviders";
import AdminSettings from "@/pages/admin/Settings";
import AdminObservability from "@/pages/admin/Observability";
import AdminAudit from "@/pages/admin/Audit";

const buyerNav: NavSection[] = [
  {
    items: [
      { label: "Dashboard", to: "/buyer/dashboard", icon: <DashboardIcon /> },
      { label: "Chat Co-pilot", to: "/buyer/chat", icon: <ChatIcon /> },
      { label: "Inventory", to: "/buyer/inventory", icon: <InventoryIcon /> },
      { label: "Vendors", to: "/buyer/vendors", icon: <VendorsIcon /> },
      { label: "Activity", to: "/buyer/activity", icon: <ActivityIcon /> },
      { label: "Observability", to: "/buyer/observability", icon: <ObservabilityIcon /> },
      { label: "Settings", to: "/buyer/settings", icon: <SettingsIcon /> },
    ],
  },
  {
    title: "Coming Soon",
    items: [
      { label: "Negotiation", to: "#", icon: <NegotiationIcon />, disabled: true },
      { label: "Contract", to: "#", icon: <ContractIcon />, disabled: true },
      { label: "Invoice", to: "#", icon: <InvoiceIcon />, disabled: true },
      { label: "Analytics", to: "#", icon: <AnalyticsIcon />, disabled: true },
    ],
  },
];

const vendorNav: NavSection[] = [
  {
    items: [
      { label: "Inbox", to: "/vendor/inbox", icon: <InboxIcon /> },
      { label: "Profile", to: "/vendor/profile", icon: <ProfileIcon /> },
    ],
  },
];

const adminNav: NavSection[] = [
  {
    items: [
      { label: "Dashboard", to: "/admin/dashboard", icon: <DashboardIcon /> },
      { label: "Users", to: "/admin/users", icon: <UsersIcon /> },
      { label: "AI Providers", to: "/admin/ai/providers", icon: <AIIcon /> },
      { label: "Observability", to: "/admin/observability", icon: <ObservabilityIcon /> },
      { label: "Audit Log", to: "/admin/audit", icon: <AuditIcon /> },
      { label: "Settings", to: "/admin/settings", icon: <SettingsIcon /> },
    ],
  },
];

function BuyerShell() {
  return (
    <SidebarLayout
      sections={buyerNav}
      header={<span className="text-sm font-bold tracking-tight text-zinc-100">AEROS</span>}
      topBar={<TopBar title="Buyer Portal" />}
    >
      <Outlet />
    </SidebarLayout>
  );
}

function VendorShell() {
  return (
    <SidebarLayout
      sections={vendorNav}
      header={<span className="text-sm font-bold tracking-tight text-zinc-100">AEROS</span>}
      topBar={<TopBar title="Vendor Portal" />}
    >
      <Outlet />
    </SidebarLayout>
  );
}

function AdminShell() {
  return (
    <SidebarLayout
      sections={adminNav}
      header={<span className="text-sm font-bold tracking-tight text-zinc-100">AEROS Admin</span>}
      topBar={<TopBar title="Admin" />}
    >
      <Outlet />
    </SidebarLayout>
  );
}

function RootRedirect() {
  const { user, initialized, loading } = useAuthStore();

  if (!initialized || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950">
        <div className="text-sm text-zinc-500">Loading...</div>
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "vendor") return <Navigate to="/vendor/inbox" replace />;
  if (user.role === "admin") return <Navigate to="/admin/dashboard" replace />;
  return <Navigate to="/buyer/dashboard" replace />;
}

export function App() {
  const { fetchMe, initialized } = useAuthStore();

  useEffect(() => {
    if (!initialized) fetchMe();
  }, [fetchMe, initialized]);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<RootRedirect />} />

      <Route element={<ProtectedRoute allowedRoles={["buyer", "admin"]} />}>
        <Route element={<BuyerShell />}>
          <Route path="/buyer/dashboard" element={<BuyerDashboard />} />
          <Route path="/buyer/chat" element={<ChatCopilot />} />
          <Route path="/buyer/inventory" element={<Inventory />} />
          <Route path="/buyer/vendors" element={<BuyerVendors />} />
          <Route path="/buyer/rfx/:id" element={<RFxDetail />} />
          <Route path="/buyer/settings" element={<BuyerSettings />} />
          <Route path="/buyer/activity" element={<BuyerActivity />} />
          <Route path="/buyer/observability" element={<BuyerObservability />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={["vendor"]} />}>
        <Route element={<VendorShell />}>
          <Route path="/vendor/inbox" element={<VendorInbox />} />
          <Route path="/vendor/rfx/:id" element={<VendorRFxReply />} />
          <Route path="/vendor/profile" element={<VendorProfile />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={["admin"]} />}>
        <Route element={<AdminShell />}>
          <Route path="/admin/dashboard" element={<AdminDashboard />} />
          <Route path="/admin/users" element={<AdminUsers />} />
          <Route path="/admin/ai/providers" element={<AdminAIProviders />} />
          <Route path="/admin/settings" element={<AdminSettings />} />
          <Route path="/admin/observability" element={<AdminObservability />} />
          <Route path="/admin/audit" element={<AdminAudit />} />
        </Route>
      </Route>
    </Routes>
  );
}
