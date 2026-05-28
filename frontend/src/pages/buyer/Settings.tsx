import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { PageHeader, LoadingSpinner, ErrorState, Modal, Toast } from "@/components/ui";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface UserInfo {
  id: number;
  email: string;
  role: string;
  display_name: string;
  org_id: number;
}

interface BuyerDefaults {
  payment_terms: string;
  delivery_terms: string;
  quote_validity_days: number;
  currency: string;
  tax_treatment: string;
  delivery_window: string;
}

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function BuyerSettings() {
  const queryClient = useQueryClient();
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editForm, setEditForm] = useState<BuyerDefaults>({
    payment_terms: "",
    delivery_terms: "",
    quote_validity_days: 7,
    currency: "INR",
    tax_treatment: "exclusive",
    delivery_window: "next day",
  });

  const [editProfileOpen, setEditProfileOpen] = useState(false);
  const [profileForm, setProfileForm] = useState({ display_name: "" });
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const {
    data: user,
    isLoading,
    error,
  } = useQuery<UserInfo>({
    queryKey: ["auth", "me"],
    queryFn: () => api.get<UserInfo>("/api/auth/me"),
  });

  const { data: defaults } = useQuery<BuyerDefaults>({
    queryKey: ["buyer", "defaults"],
    queryFn: () => api.get<BuyerDefaults>("/api/buyer/defaults"),
  });

  const updateDefaultsMutation = useMutation({
    mutationFn: (data: BuyerDefaults) => api.put("/api/buyer/defaults", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["buyer", "defaults"] });
      setEditModalOpen(false);
      setToastMessage("Default terms updated");
    },
    onError: () => setToastMessage("Failed to update default terms"),
  });

  const updateProfileMutation = useMutation({
    mutationFn: (data: { display_name: string }) => api.put("/api/auth/profile", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      setEditProfileOpen(false);
      setToastMessage("Profile updated");
    },
    onError: () => setToastMessage("Failed to update profile"),
  });

  function openEditModal() {
    if (defaults) {
      setEditForm({ ...defaults });
    }
    setEditModalOpen(true);
  }

  function handleSave() {
    updateDefaultsMutation.mutate(editForm);
  }

  function openEditProfileModal() {
    if (user) {
      setProfileForm({ display_name: user.display_name });
    }
    setEditProfileOpen(true);
  }

  function handleProfileSave() {
    updateProfileMutation.mutate(profileForm);
  }

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Settings"
        subtitle="User profile, default terms, and preferences."
      />

      {/* Loading */}
      {isLoading && <LoadingSpinner message="Loading profile..." />}

      {/* Error */}
      {error && !isLoading && (
        <ErrorState message="Failed to load profile. Please try again." />
      )}

      {/* Profile Card */}
      {!isLoading && !error && user && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-500">
              Profile
            </h2>
            <button
              type="button"
              onClick={openEditProfileModal}
              className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:bg-zinc-800"
            >
              Edit Profile
            </button>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium text-zinc-500">
                Display Name
              </label>
              <p className="mt-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200">
                {user.display_name}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500">
                Email
              </label>
              <p className="mt-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200">
                {user.email}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500">
                Role
              </label>
              <p className="mt-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 capitalize">
                {user.role}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500">
                Organization ID
              </label>
              <p className="mt-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200">
                {user.org_id}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Default Terms */}
      {!isLoading && !error && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-500">
              Default Terms
            </h2>
            <button
              type="button"
              onClick={openEditModal}
              className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:bg-zinc-800"
            >
              Edit Terms
            </button>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { label: "Payment Terms", value: defaults?.payment_terms ?? "NET30" },
              { label: "Delivery Terms", value: defaults?.delivery_terms ?? "doorstep" },
              { label: "Currency", value: defaults?.currency ?? "INR" },
              { label: "Quote Validity", value: `${defaults?.quote_validity_days ?? 7} days` },
              { label: "Tax Treatment", value: defaults?.tax_treatment ?? "exclusive" },
              { label: "Delivery Window", value: defaults?.delivery_window ?? "next day" },
            ].map((term) => (
              <div key={term.label}>
                <label className="block text-xs font-medium text-zinc-500">
                  {term.label}
                </label>
                <p className="mt-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm font-medium text-zinc-200 capitalize">
                  {term.value}
                </p>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs text-zinc-600">
            These defaults are applied automatically to new RFx.
          </p>
        </div>
      )}

      {/* Edit Terms Modal */}
      <Modal
        open={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title="Edit Default Terms"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-zinc-500">Payment Terms</label>
            <input
              type="text"
              value={editForm.payment_terms}
              onChange={(e) => setEditForm((f) => ({ ...f, payment_terms: e.target.value }))}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-500">Delivery Terms</label>
            <input
              type="text"
              value={editForm.delivery_terms}
              onChange={(e) => setEditForm((f) => ({ ...f, delivery_terms: e.target.value }))}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-500">Currency</label>
            <input
              type="text"
              value={editForm.currency}
              onChange={(e) => setEditForm((f) => ({ ...f, currency: e.target.value }))}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-500">Quote Validity (days)</label>
            <input
              type="number"
              value={editForm.quote_validity_days}
              onChange={(e) => setEditForm((f) => ({ ...f, quote_validity_days: Number(e.target.value) }))}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-500">Tax Treatment</label>
            <input
              type="text"
              value={editForm.tax_treatment}
              onChange={(e) => setEditForm((f) => ({ ...f, tax_treatment: e.target.value }))}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-500">Delivery Window</label>
            <input
              type="text"
              value={editForm.delivery_window}
              onChange={(e) => setEditForm((f) => ({ ...f, delivery_window: e.target.value }))}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => setEditModalOpen(false)}
              className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 transition hover:bg-zinc-800"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
            >
              Save
            </button>
          </div>
        </div>
      </Modal>

      {/* Edit Profile Modal */}
      <Modal
        open={editProfileOpen}
        onClose={() => setEditProfileOpen(false)}
        title="Edit Profile"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-zinc-500">Display Name</label>
            <input
              type="text"
              value={profileForm.display_name}
              onChange={(e) => setProfileForm((f) => ({ ...f, display_name: e.target.value }))}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-500">Email</label>
            <p className="mt-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-400">
              {user?.email ?? "--"}
            </p>
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-500">Role</label>
            <p className="mt-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-400 capitalize">
              {user?.role ?? "--"}
            </p>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => setEditProfileOpen(false)}
              className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 transition hover:bg-zinc-800"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleProfileSave}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
            >
              Save
            </button>
          </div>
        </div>
      </Modal>

      {/* Toast */}
      {toastMessage && (
        <Toast message={toastMessage} onClose={() => setToastMessage(null)} />
      )}
    </div>
  );
}
