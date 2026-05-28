import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import {
  PageHeader,
  LoadingSpinner,
  ErrorState,
  ConfirmDialog,
  Toast,
} from "@/components/ui";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface SettingItem {
  key: string;
  value: string;
  type: string;
  description: string;
  source: string;
}

/* ------------------------------------------------------------------ */
/* Section icon                                                        */
/* ------------------------------------------------------------------ */

const SECTION_ICONS: Record<string, string> = {
  Application:
    "M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18.75h3",
  Database:
    "M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125",
  Upload:
    "M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5",
  Security:
    "M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z",
};

/** Derive a section name from a setting key for icon lookup. */
function sectionForKey(key: string): string {
  const lower = key.toLowerCase();
  if (lower.includes("db") || lower.includes("database")) return "Database";
  if (lower.includes("upload") || lower.includes("file")) return "Upload";
  if (lower.includes("auth") || lower.includes("jwt") || lower.includes("cors") || lower.includes("secret") || lower.includes("security"))
    return "Security";
  return "Application";
}

/* ------------------------------------------------------------------ */
/* Editable row                                                        */
/* ------------------------------------------------------------------ */

function SettingRow({
  setting,
  onInitSave,
  isSaving,
}: {
  setting: SettingItem;
  onInitSave: (key: string, value: string) => void;
  isSaving: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(setting.value);

  const handleSave = () => {
    onInitSave(setting.key, draft);
    setEditing(false);
  };

  const handleCancel = () => {
    setDraft(setting.value);
    setEditing(false);
  };

  return (
    <div className="flex items-center justify-between gap-3">
      <div className="min-w-0">
        <span className="text-xs text-zinc-500">{setting.key}</span>
        {setting.description && (
          <p className="text-[11px] text-zinc-600 truncate">{setting.description}</p>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {editing ? (
          <>
            <input
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="w-40 rounded-md border border-zinc-700 bg-zinc-800 px-2 py-0.5 font-mono text-xs text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSave();
                if (e.key === "Escape") handleCancel();
              }}
            />
            <button
              type="button"
              disabled={isSaving}
              onClick={handleSave}
              className="rounded px-2 py-0.5 text-[11px] font-medium text-green-400 transition hover:bg-green-900/20 disabled:opacity-50"
            >
              Save
            </button>
            <button
              type="button"
              onClick={handleCancel}
              className="rounded px-2 py-0.5 text-[11px] font-medium text-zinc-500 transition hover:bg-zinc-800"
            >
              Cancel
            </button>
          </>
        ) : (
          <>
            <span className="rounded-md bg-zinc-950 px-2 py-0.5 font-mono text-xs text-zinc-300">
              {setting.value}
            </span>
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="rounded px-2 py-0.5 text-[11px] font-medium text-indigo-400 transition hover:bg-indigo-900/20"
              title="Edit setting"
            >
              Edit
            </button>
          </>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function AdminSettings() {
  const queryClient = useQueryClient();

  const {
    data: settings = [],
    isLoading,
    error,
    refetch,
  } = useQuery<SettingItem[]>({
    queryKey: ["admin", "settings"],
    queryFn: () => api.get<SettingItem[]>("/api/admin/settings"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      api.put(`/api/admin/settings/${encodeURIComponent(key)}`, { value }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "settings"] });
    },
  });

  /* --- confirmation + toast state --- */
  const [confirmTarget, setConfirmTarget] = useState<{ key: string; value: string } | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const handleInitSave = useCallback((key: string, value: string) => {
    setConfirmTarget({ key, value });
  }, []);

  const handleConfirmSave = useCallback(() => {
    if (!confirmTarget) return;
    updateMutation.mutate(
      { key: confirmTarget.key, value: confirmTarget.value },
      {
        onSuccess: () => {
          setToast(`Setting "${confirmTarget.key}" updated successfully.`);
        },
        onError: () => {
          setToast(`Failed to update "${confirmTarget.key}".`);
        },
        onSettled: () => {
          setConfirmTarget(null);
        },
      },
    );
  }, [confirmTarget, updateMutation]);

  /** Group settings by inferred section. */
  const grouped = settings.reduce<Record<string, SettingItem[]>>(
    (acc, item) => {
      const section = sectionForKey(item.key);
      if (!acc[section]) acc[section] = [];
      acc[section].push(item);
      return acc;
    },
    {},
  );

  // Ensure stable ordering of sections
  const sectionOrder = ["Application", "Database", "Upload", "Security"];
  const orderedSections = sectionOrder.filter((s) => grouped[s]);
  Object.keys(grouped).forEach((s) => {
    if (!orderedSections.includes(s)) orderedSections.push(s);
  });

  if (isLoading) return <LoadingSpinner message="Loading settings..." />;
  if (error) return <ErrorState message="Failed to load settings." onRetry={refetch} />;

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="System Settings"
        subtitle="Retention policies, rate limits, budgets, and system configuration."
      />

      {/* Config Cards */}
      {settings.length === 0 ? (
        <p className="text-xs text-zinc-600">
          No settings found. Configuration may require editing environment
          variables and restarting the server.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {orderedSections.map((section) => (
            <div
              key={section}
              className="rounded-xl border border-zinc-800 bg-zinc-900 p-5"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-zinc-800">
                  <svg
                    className="h-4.5 w-4.5 text-zinc-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d={SECTION_ICONS[section] ?? SECTION_ICONS.Application}
                    />
                  </svg>
                </div>
                <h2 className="text-sm font-medium text-zinc-200">
                  {section}
                </h2>
              </div>

              <div className="mt-4 space-y-2.5">
                {grouped[section].map((item) => (
                  <SettingRow
                    key={item.key}
                    setting={item}
                    onInitSave={handleInitSave}
                    isSaving={updateMutation.isPending}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Save confirmation dialog */}
      <ConfirmDialog
        open={!!confirmTarget}
        onClose={() => setConfirmTarget(null)}
        onConfirm={handleConfirmSave}
        title="Update Setting"
        message={`Update ${confirmTarget?.key}? This will change the system setting.`}
        confirmLabel="Save"
        confirmVariant="primary"
        isPending={updateMutation.isPending}
      />

      {/* Success / error toast */}
      {toast && (
        <Toast
          message={toast}
          type={updateMutation.isError ? "error" : "success"}
          onClose={() => setToast(null)}
          duration={3000}
        />
      )}
    </div>
  );
}
