import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useAuthStore } from "@/stores/auth";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type UserRole = "buyer" | "vendor" | "admin";
type UserStatus = "active" | "inactive" | "suspended";

interface UserRecord {
  id: number;
  display_name: string;
  email: string;
  role: UserRole;
  status: UserStatus;
  created_at: string;
}

/* ------------------------------------------------------------------ */
/* Badge styles                                                        */
/* ------------------------------------------------------------------ */

const ROLE_STYLES: Record<UserRole, string> = {
  buyer: "bg-indigo-900/40 text-indigo-400",
  vendor: "bg-green-900/40 text-green-400",
  admin: "bg-amber-900/40 text-amber-400",
};

const STATUS_STYLES: Record<string, string> = {
  active: "bg-green-900/40 text-green-400",
  inactive: "bg-zinc-700/50 text-zinc-400",
  suspended: "bg-red-900/40 text-red-400",
};

function formatDate(iso: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function AdminUsers() {
  const queryClient = useQueryClient();
  const currentUser = useAuthStore((s) => s.user);

  const { data: users = [], isLoading, error } = useQuery<UserRecord[]>({
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

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100">
          User Management
        </h1>
        <p className="mt-1 text-sm text-zinc-500">
          List, create, suspend, and manage user roles.
        </p>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-indigo-500" />
          <span className="ml-3 text-sm text-zinc-500">Loading users...</span>
        </div>
      )}

      {error && !isLoading && (
        <div className="rounded-xl border border-red-800/50 bg-red-900/20 p-4">
          <p className="text-sm text-red-400">Failed to load users.</p>
        </div>
      )}

      {(suspendMutation.isError || reactivateMutation.isError) && (
        <div className="rounded-xl border border-red-800/50 bg-red-900/20 p-3">
          <p className="text-sm text-red-400">Action failed. Please try again.</p>
        </div>
      )}

      {!isLoading && !error && (
        <div className="overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-900">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-800">
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Name
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Email
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Role
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Status
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Created
                </th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              {users.map((user) => {
                const isCurrentUser = String(user.id) === currentUser?.id || user.email === currentUser?.email;
                const isSuspended = user.status === "suspended";
                const isActing =
                  (suspendMutation.isPending && suspendMutation.variables === user.id) ||
                  (reactivateMutation.isPending && reactivateMutation.variables === user.id);

                return (
                  <tr
                    key={user.id}
                    className="transition hover:bg-zinc-800/40"
                  >
                    <td className="whitespace-nowrap px-4 py-3 font-medium text-zinc-200">
                      {user.display_name}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-zinc-400">
                      {user.email}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${ROLE_STYLES[user.role] ?? "bg-zinc-700/50 text-zinc-400"}`}
                      >
                        {user.role}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${STATUS_STYLES[user.status] ?? "bg-zinc-700/50 text-zinc-400"}`}
                      >
                        {user.status}
                      </span>
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
                          onClick={() => reactivateMutation.mutate(user.id)}
                          className="rounded-lg border border-green-800/50 bg-green-900/20 px-3 py-1 text-xs font-medium text-green-400 transition hover:bg-green-900/40 disabled:opacity-50"
                        >
                          {isActing ? "Reactivating..." : "Reactivate"}
                        </button>
                      ) : (
                        <button
                          type="button"
                          disabled={isActing}
                          onClick={() => suspendMutation.mutate(user.id)}
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
      )}

      <p className="text-xs text-zinc-600">
        {users.length} users registered.
      </p>
    </div>
  );
}
