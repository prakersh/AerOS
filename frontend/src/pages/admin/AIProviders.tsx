import { useState, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/api/client";
import {
  StatusBadge,
  PageHeader,
  LoadingSpinner,
  ErrorState,
  Modal,
  DetailView,
  FilterChips,
  Toast,
} from "@/components/ui";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type ProviderStatus = "active" | "inactive" | "error" | "disabled";

interface AIProvider {
  id: number;
  provider_name: string;
  display_name: string;
  capability: string;
  model_id: string | null;
  status: ProviderStatus;
  is_default?: boolean;
}

interface TestResult {
  ok: boolean;
  error?: string;
}

/* ------------------------------------------------------------------ */
/* Filter options                                                      */
/* ------------------------------------------------------------------ */

const STATUS_FILTER_OPTIONS = [
  { label: "All", value: "all" },
  { label: "Active", value: "active" },
  { label: "Inactive", value: "inactive" },
  { label: "Error", value: "error" },
  { label: "Disabled", value: "disabled" },
];

/* ------------------------------------------------------------------ */
/* Provider icon                                                       */
/* ------------------------------------------------------------------ */

function ProviderIcon() {
  return (
    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-900/30">
      <svg
        className="h-5 w-5 text-indigo-400"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={1.5}
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z"
        />
      </svg>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function AdminAIProviders() {
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedProvider, setSelectedProvider] = useState<AIProvider | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editForm, setEditForm] = useState({
    api_key: "",
    base_url: "",
    model_name: "",
    max_tokens: 4096,
    temperature: 0.7,
  });
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const {
    data: providers = [],
    isLoading,
    error,
    refetch,
  } = useQuery<AIProvider[]>({
    queryKey: ["admin", "ai-providers"],
    queryFn: () => api.get<AIProvider[]>("/api/admin/ai/providers"),
  });

  const testMutation = useMutation({
    mutationFn: (providerName: string) =>
      api.post<TestResult>("/api/admin/ai/providers/test", {
        provider_name: providerName,
      }),
    onSuccess: (data, providerName) => {
      setTestResults((prev) => ({ ...prev, [providerName]: data }));
    },
    onError: (_err, providerName) => {
      setTestResults((prev) => ({
        ...prev,
        [providerName]: { ok: false, error: "Connection test failed" },
      }));
    },
  });

  const filtered = useMemo(() => {
    if (statusFilter === "all") return providers;
    return providers.filter((p) => p.status === statusFilter);
  }, [providers, statusFilter]);

  function openEditModal() {
    if (selectedProvider) {
      setEditForm({
        api_key: "",
        base_url: "",
        model_name: selectedProvider.model_id ?? "",
        max_tokens: 4096,
        temperature: 0.7,
      });
    }
    setEditModalOpen(true);
  }

  function handleEditSave() {
    setEditModalOpen(false);
    setSelectedProvider(null);
    setToastMessage("Provider settings saved");
  }

  if (isLoading) return <LoadingSpinner message="Loading providers..." />;
  if (error) return <ErrorState message="Failed to load AI providers." onRetry={refetch} />;

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="AI Providers"
        subtitle="Configure AI models, toggle providers, set token caps and failover priority."
      />

      <FilterChips
        options={STATUS_FILTER_OPTIONS}
        active={statusFilter}
        onChange={setStatusFilter}
      />

      {/* Provider Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {filtered.length === 0 && (
          <p className="col-span-full text-sm text-zinc-600">
            No providers match the selected filter.
          </p>
        )}
        {filtered.map((provider) => {
          const result = testResults[provider.provider_name];
          const isTesting =
            testMutation.isPending &&
            testMutation.variables === provider.provider_name;

          return (
            <div
              key={provider.id}
              className="cursor-pointer rounded-xl border border-zinc-800 bg-zinc-900 p-5 transition hover:border-zinc-700"
              onClick={() => setSelectedProvider(provider)}
            >
              <div className="flex items-start gap-4">
                <ProviderIcon />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-medium text-zinc-200">
                      {provider.display_name}
                    </h3>
                    <StatusBadge status={provider.status} variant="provider" />
                  </div>
                  <p className="mt-1 text-xs text-zinc-500">
                    {provider.capability}
                  </p>
                  {provider.model_id && (
                    <p className="mt-2 rounded-md bg-zinc-950 px-2.5 py-1.5 font-mono text-xs text-zinc-400">
                      {provider.model_id}
                    </p>
                  )}
                </div>
              </div>

              <div className="mt-4 flex items-center justify-between">
                <div className="text-xs">
                  {result?.ok === true && (
                    <span className="text-green-400">Connection OK</span>
                  )}
                  {result?.ok === false && (
                    <span className="text-red-400">
                      {result.error ?? "Failed"}
                    </span>
                  )}
                </div>

                <button
                  type="button"
                  disabled={isTesting}
                  onClick={(e) => {
                    e.stopPropagation();
                    testMutation.mutate(provider.provider_name);
                  }}
                  className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-400 transition hover:border-zinc-600 hover:text-zinc-300 disabled:opacity-50"
                >
                  {isTesting ? "Testing..." : "Test Connection"}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <p className="text-xs text-zinc-600">
        Provider management and failover configuration will be available in a
        future release.
      </p>

      {/* Detail modal */}
      <Modal
        open={!!selectedProvider && !editModalOpen}
        onClose={() => setSelectedProvider(null)}
        title="Provider Details"
      >
        {selectedProvider && (
          <>
            <DetailView
              items={[
                { label: "Display Name", value: selectedProvider.display_name },
                { label: "Provider Name", value: selectedProvider.provider_name },
                { label: "Capability", value: selectedProvider.capability },
                { label: "Model ID", value: selectedProvider.model_id ?? "---" },
                { label: "Status", value: <StatusBadge status={selectedProvider.status} variant="provider" /> },
                { label: "Default", value: selectedProvider.is_default ? "Yes" : "No" },
              ]}
            />
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={openEditModal}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
              >
                Edit Provider
              </button>
            </div>
          </>
        )}
      </Modal>

      {/* Edit Provider Modal */}
      <Modal
        open={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title="Edit Provider"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-zinc-500">API Key</label>
            <input
              type="password"
              value={editForm.api_key}
              onChange={(e) => setEditForm((f) => ({ ...f, api_key: e.target.value }))}
              placeholder="sk-..."
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-500">Base URL</label>
            <input
              type="text"
              value={editForm.base_url}
              onChange={(e) => setEditForm((f) => ({ ...f, base_url: e.target.value }))}
              placeholder="https://api.openai.com/v1"
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-500">Model Name</label>
            <input
              type="text"
              value={editForm.model_name}
              onChange={(e) => setEditForm((f) => ({ ...f, model_name: e.target.value }))}
              placeholder="gpt-4o"
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-zinc-500">Max Tokens</label>
              <input
                type="number"
                value={editForm.max_tokens}
                onChange={(e) => setEditForm((f) => ({ ...f, max_tokens: Number(e.target.value) }))}
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500">Temperature</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={editForm.temperature}
                onChange={(e) => setEditForm((f) => ({ ...f, temperature: Number(e.target.value) }))}
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>
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
              onClick={handleEditSave}
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
