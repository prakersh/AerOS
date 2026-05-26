import { useState } from "react";
import { useAuthStore } from "@/stores/auth";

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

  const togglePref = (key: keyof NotificationPrefs) => {
    setPrefs((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-zinc-100">Vendor Profile</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Business details, categories, and offered terms.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
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

          <div className="divide-y divide-zinc-800">
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

          {/* Bind Telegram */}
          <div className="mt-6 border-t border-zinc-800 pt-4">
            <button className="flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm font-medium text-zinc-300 transition hover:border-zinc-600 hover:text-zinc-100">
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
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Tiny helper                                                         */
/* ------------------------------------------------------------------ */

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className="text-sm text-zinc-300">{value}</span>
    </div>
  );
}
