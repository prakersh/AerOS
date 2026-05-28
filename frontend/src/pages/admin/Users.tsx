import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useAuthStore } from "@/stores/auth";
import {
  StatusBadge,
  PageHeader,
  LoadingSpinner,
  ErrorState,
  Modal,
  DetailView,
  ConfirmDialog,
  FilterChips,
  Toast,
} from "@/components/ui";
import { formatDate } from "@/lib/format";
import type { UserRecord, UserRole } from "@/types";

/* ------------------------------------------------------------------ */
/* Filter options                                                      */
/* ------------------------------------------------------------------ */

const ROLE_FILTER_OPTIONS = [
  { label: "All", value: "all" },
  { label: "Buyer", value: "buyer" },
  { label: "Vendor", value: "vendor" },
  { label: "Admin", value: "admin" },
];

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function AdminUsers() {
  const queryClient = useQueryClient();
  const currentUser = useAuthStore((s) => s.user);

  const { data: users = [], isLoading, error, refetch } = useQuery<UserRecord[]>({
    queryKey: ["admin", "users"],
    queryFn: () => api.get<UserRecord[]>("/api/admin/users"),
  });

  const suspendMutation = useMutation({
    mutationFn: (userId: number) =>
      api.post(`/api/admin/users/${userId}/suspend`, { reason: "" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });

  const reactivateMutation = useMutation({
    mutationFn: (userId: number) =>
      api.post(`/api/admin/users/${userId}/reactivate`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });

  /* --- local state --- */
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [selectedUser, setSelectedUser] = useState<UserRecord | null>(null);
  const [suspendTarget, setSuspendTarget] = useState<UserRecord | null>(null);
  const [reactivateTarget, setReactivateTarget] = useState<UserRecord | null>(null);
  const [editRoleOpen, setEditRoleOpen] = useState(false);
  const [editRoleValue, setEditRoleValue] = useState<UserRole>("buyer");
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  /* --- filtered list --- */
  const filtered = useMemo(() => {
    let list = users;
    if (roleFilter !== "all") {
      list = list.filter((u) => u.role === roleFilter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (u) =>
          u.display_name.toLowerCase().includes(q) ||
          u.email.toLowerCase().includes(q),
      );
    }
    return list;
  }, [users, roleFilter, search]);

  function openEditRoleModal() {
    if (selectedUser) {
      setEditRoleValue(selectedUser.role);
    }
    setEditRoleOpen(true);
  }

  function handleRoleSave() {
    setEditRoleOpen(false);
    setSelectedUser(null);
    setToastMessage("Role update requested");
  }

  if (isLoading) return <LoadingSpinner message="Loading users..." />;
  if (error) return <ErrorState message="Failed to load users." onRetry={refetch} />;

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="User Management"
        subtitle="List, create, suspend, and manage user roles."
      />

      {/* Search + filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <input
          type="text"
          placeholder="Search by name or email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full sm:w-72 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        />
        <FilterChips
          options={ROLE_FILTER_OPTIONS}
          active={roleFilter}
          onChange={setRoleFilter}
        />
      </div>

      {/* Mutation error */}
      {(suspendMutation.isError || reactivateMutation.isError) && (
        <ErrorState message="Action failed. Please try again." />
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-900">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-zinc-800">
              <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">Name</th>
              <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">Email</th>
              <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">Role</th>
              <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">Status</th>
              <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">Created</th>
              <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/60">
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-zinc-600">
                  No users match your filters.
                </td>
              </tr>
            )}
            {filtered.map((user) => {
              const isCurrentUser =
                String(user.id) === currentUser?.id ||
                user.email === currentUser?.email;
              const isSuspended = user.status === "suspended";
              const isActing =
                (suspendMutation.isPending && suspendMutation.variables === user.id) ||
                (reactivateMutation.isPending && reactivateMutation.variables === user.id);

              return (
                <tr
                  key={user.id}
                  className="cursor-pointer transition hover:bg-zinc-800/40"
                  onClick={() => setSelectedUser(user)}
                >
                  <td className="whitespace-nowrap px-4 py-3 font-medium text-zinc-200">
                    {user.display_name}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-zinc-400">
                    {user.email}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <StatusBadge status={user.role} variant="user-role" />
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <StatusBadge status={user.status} variant="user-status" />
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums text-zinc-500">
                    {formatDate(user.created_at)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    {isCurrentUser ? (
                      <span className="text-[11px] text-zinc-600">You</span>
                    ) : isSuspended ? (
                      <button
                        type="button"
                        disabled={isActing}
                        onClick={(e) => {
                          e.stopPropagation();
                          setReactivateTarget(user);
                        }}
                        className="rounded-lg border border-green-800/50 bg-green-900/20 px-3 py-1 text-xs font-medium text-green-400 transition hover:bg-green-900/40 disabled:opacity-50"
                      >
                        {isActing ? "Reactivating..." : "Reactivate"}
                      </button>
                    ) : (
                      <button
                        type="button"
                        disabled={isActing}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSuspendTarget(user);
                        }}
                        className="rounded-lg border border-red-800/50 bg-red-900/20 px-3 py-1 text-xs font-medium text-red-400 transition hover:bg-red-900/40 disabled:opacity-50"
                      >
                        {isActing ? "Suspending..." : "Suspend"}
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-zinc-600">
        {filtered.length} of {users.length} users shown.
      </p>

      {/* Detail modal */}
      <Modal
        open={!!selectedUser && !editRoleOpen}
        onClose={() => setSelectedUser(null)}
        title="User Details"
      >
        {selectedUser && (
          <>
            <DetailView
              items={[
                { label: "Name", value: selectedUser.display_name },
                { label: "Email", value: selectedUser.email },
                { label: "Role", value: <StatusBadge status={selectedUser.role} variant="user-role" /> },
                { label: "Status", value: <StatusBadge status={selectedUser.status} variant="user-status" /> },
                { label: "Created", value: formatDate(selectedUser.created_at) },
              ]}
            />
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={openEditRoleModal}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
              >
                Edit Role
              </button>
            </div>
          </>
        )}
      </Modal>

      {/* Edit Role Modal */}
      <Modal
        open={editRoleOpen}
        onClose={() => setEditRoleOpen(false)}
        title="Edit Role"
        size="sm"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-zinc-500">User</label>
            <p className="mt-1 text-sm text-zinc-200">
              {selectedUser?.display_name} ({selectedUser?.email})
            </p>
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-500">Role</label>
            <select
              value={editRoleValue}
              onChange={(e) => setEditRoleValue(e.target.value as UserRole)}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            >
              <option value="buyer">Buyer</option>
              <option value="vendor">Vendor</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => setEditRoleOpen(false)}
              className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 transition hover:bg-zinc-800"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleRoleSave}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
            >
              Save
            </button>
          </div>
        </div>
      </Modal>

      {/* Suspend confirmation */}
      <ConfirmDialog
        open={!!suspendTarget}
        onClose={() => setSuspendTarget(null)}
        onConfirm={() => {
          if (suspendTarget) {
            suspendMutation.mutate(suspendTarget.id, {
              onSettled: () => setSuspendTarget(null),
            });
          }
        }}
        title="Suspend User"
        message={`Are you sure you want to suspend ${suspendTarget?.display_name}? They will lose access immediately.`}
        confirmLabel="Suspend"
        confirmVariant="danger"
        isPending={suspendMutation.isPending}
      />

      {/* Reactivate confirmation */}
      <ConfirmDialog
        open={!!reactivateTarget}
        onClose={() => setReactivateTarget(null)}
        onConfirm={() => {
          if (reactivateTarget) {
            reactivateMutation.mutate(reactivateTarget.id, {
              onSettled: () => setReactivateTarget(null),
            });
          }
        }}
        title="Reactivate User"
        message={`Reactivate ${reactivateTarget?.display_name}? They will regain access to the platform.`}
        confirmLabel="Reactivate"
        confirmVariant="primary"
        isPending={reactivateMutation.isPending}
      />

      {/* Toast */}
      {toastMessage && (
        <Toast message={toastMessage} onClose={() => setToastMessage(null)} />
      )}
    </div>
  );
}
