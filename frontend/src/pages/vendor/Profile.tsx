import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useAuthStore } from "@/stores/auth";
import { Modal, PageHeader, Toast } from "@/components/ui";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface NotificationPrefs {
  email: boolean;
  telegram: boolean;
  in_app: boolean;
}

/* ------------------------------------------------------------------ */
/* Sub-components                                                      */
/* ------------------------------------------------------------------ */

function Toggle({
  label,
  description,
  enabled,
  onToggle,
}: {
  label: string;
  description: string;
  enabled: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex items-center justify-between py-3">
      <div>
        <p className="text-sm font-medium text-zinc-200">{label}</p>
        <p className="text-xs text-zinc-500">{description}</p>
      </div>
      <button
        onClick={onToggle}
        className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors ${
          enabled ? "bg-indigo-600" : "bg-zinc-700"
        }`}
        role="switch"
        aria-checked={enabled}
      >
        <span
          className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
            enabled ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className="text-sm text-zinc-300">{value}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main component                                                      */
/* ------------------------------------------------------------------ */

export default function VendorProfile() {
  const { user } = useAuthStore();

  const [prefs, setPrefs] = useState<NotificationPrefs>({
    email: true,
    telegram: false,
    in_app: true,
  });

  const [showTelegramModal, setShowTelegramModal] = useState(false);
  const [editProfileOpen, setEditProfileOpen] = useState(false);
  const [editForm, setEditForm] = useState({
    vendor_name: "",
    email: "",
    phone: "",
    address: "",
  });
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const togglePref = (key: keyof NotificationPrefs) => {
    setPrefs((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const token = user?.id ?? "unknown";
  const deepLink = `https://t.me/aeros_bot?start=${token}`;

  function openEditProfileModal() {
    setEditForm({
      vendor_name: user?.display_name ?? "",
      email: user?.email ?? "",
      phone: "",
      address: "",
    });
    setEditProfileOpen(true);
  }

  const profileMutation = useMutation({
    mutationFn: (data: { vendor_name: string; phone: string }) =>
      api.put("/api/vendor/profile", data),
    onSuccess: () => {
      setEditProfileOpen(false);
      setToastMessage("Profile updated successfully");
    },
    onError: () => setToastMessage("Failed to update profile"),
  });

  function handleProfileSave() {
    profileMutation.mutate({
      vendor_name: editForm.vendor_name,
      phone: editForm.phone,
    });
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between">
        <PageHeader
          title="Vendor Profile"
          subtitle="Business details, categories, and offered terms."
        />
        <button
          type="button"
          onClick={openEditProfileModal}
          className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 transition hover:bg-zinc-800"
        >
          Edit Profile
        </button>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        {/* ---- Profile info card ---- */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-zinc-500">
            Account Information
          </h2>

          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-indigo-600 text-lg font-bold text-white">
              {user?.display_name?.charAt(0).toUpperCase() ?? "V"}
            </div>
            <div>
              <p className="text-base font-medium text-zinc-100">
                {user?.display_name ?? "Vendor"}
              </p>
              <p className="text-sm text-zinc-500">{user?.email ?? "--"}</p>
            </div>
          </div>

          <div className="mt-6 space-y-3 border-t border-zinc-800 pt-4">
            <InfoRow label="User ID" value={user?.id ?? "--"} />
            <InfoRow label="Role" value={user?.role ?? "--"} />
            <InfoRow label="Email" value={user?.email ?? "--"} />
          </div>
        </div>

        {/* ---- Notification preferences card ---- */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-zinc-500">
            Notification Preferences
          </h2>

          <div className="divide-y divide-zinc-800 pointer-events-none opacity-60">
            <Toggle
              label="Email notifications"
              description="Receive RFx invitations and updates via email."
              enabled={prefs.email}
              onToggle={() => togglePref("email")}
            />
            <Toggle
              label="Telegram notifications"
              description="Get instant alerts in your Telegram chat."
              enabled={prefs.telegram}
              onToggle={() => togglePref("telegram")}
            />
            <Toggle
              label="In-app notifications"
              description="See notifications inside AEROS."
              enabled={prefs.in_app}
              onToggle={() => togglePref("in_app")}
            />
          </div>

          <p className="mt-3 text-[11px] text-zinc-600">
            Notification preferences are read-only in this release. Changes will
            be available once the notification service is fully enabled.
          </p>

          {/* Bind Telegram */}
          <div className="mt-6 border-t border-zinc-800 pt-4">
            <button
              type="button"
              onClick={() => setShowTelegramModal(true)}
              className="flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm font-medium text-zinc-300 transition hover:border-zinc-600 hover:text-zinc-100"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M11.994 2C6.47 2 2 6.478 2 12.004c0 5.525 4.47 10.002 9.994 10.002 5.525 0 10.006-4.477 10.006-10.002C22 6.478 17.52 2 11.994 2zm4.806 6.813l-1.65 7.776c-.124.558-.45.694-.912.432l-2.52-1.858-1.215 1.17c-.135.135-.248.248-.508.248l.18-2.563 4.66-4.21c.203-.18-.044-.28-.315-.1l-5.76 3.627-2.48-.775c-.54-.168-.55-.54.112-.8l9.692-3.735c.45-.163.843.11.696.788z" />
              </svg>
              Bind Telegram
            </button>
            <p className="mt-2 text-[11px] text-zinc-600">
              Connect your Telegram account to receive notifications directly.
            </p>
          </div>
        </div>
      </div>

      {/* Telegram modal */}
      <Modal
        open={showTelegramModal}
        onClose={() => setShowTelegramModal(false)}
        title="Bind Telegram Account"
        size="md"
      >
        <p className="text-sm text-zinc-400">
          Click the link below to open Telegram and connect your account to
          AEROS notifications.
        </p>

        <div className="mt-4 rounded-lg border border-zinc-700 bg-zinc-950 p-3">
          <p className="text-xs text-zinc-500 mb-1">Your personal bind link:</p>
          <a
            href={deepLink}
            target="_blank"
            rel="noopener noreferrer"
            className="break-all font-mono text-sm text-indigo-400 hover:underline"
          >
            {deepLink}
          </a>
        </div>

        <ol className="mt-4 space-y-2 text-sm text-zinc-400">
          <li className="flex gap-2">
            <span className="shrink-0 font-medium text-zinc-300">1.</span>
            Click the link above (or copy it to Telegram).
          </li>
          <li className="flex gap-2">
            <span className="shrink-0 font-medium text-zinc-300">2.</span>
            Press <span className="font-medium text-zinc-200">Start</span> in the
            Telegram bot chat.
          </li>
          <li className="flex gap-2">
            <span className="shrink-0 font-medium text-zinc-300">3.</span>
            You will receive a confirmation message once bound.
          </li>
        </ol>

        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={() => setShowTelegramModal(false)}
            className="rounded-lg bg-zinc-800 px-4 py-2 text-sm font-medium text-zinc-300 transition hover:bg-zinc-700"
          >
            Close
          </button>
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
            <label className="block text-xs font-medium text-zinc-500">Vendor Name</label>
            <input
              type="text"
              value={editForm.vendor_name}
              onChange={(e) => setEditForm((f) => ({ ...f, vendor_name: e.target.value }))}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-500">Email</label>
            <input
              type="email"
              value={editForm.email}
              onChange={(e) => setEditForm((f) => ({ ...f, email: e.target.value }))}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-500">Phone</label>
            <input
              type="tel"
              value={editForm.phone}
              onChange={(e) => setEditForm((f) => ({ ...f, phone: e.target.value }))}
              placeholder="+91 98765 43210"
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-500">Address</label>
            <textarea
              value={editForm.address}
              onChange={(e) => setEditForm((f) => ({ ...f, address: e.target.value }))}
              rows={3}
              placeholder="Business address..."
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
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
