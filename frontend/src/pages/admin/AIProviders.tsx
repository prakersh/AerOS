/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type ProviderStatus = "active" | "inactive" | "error";

interface AIProvider {
  id: number;
  name: string;
  capability: string;
  model: string | null;
  status: ProviderStatus;
}

/* ------------------------------------------------------------------ */
/* Mock data                                                           */
/* ------------------------------------------------------------------ */

const MOCK_PROVIDERS: AIProvider[] = [
  {
    id: 1,
    name: "NVIDIA NIM (Chat)",
    capability: "Text Generation / Chat Completion",
    model: "deepseek-ai/deepseek-v4-flash",
    status: "active",
  },
  {
    id: 2,
    name: "NVIDIA NIM (Vision)",
    capability: "Document & Image Understanding",
    model: "meta/llama-3.2-90b-vision-instruct",
    status: "active",
  },
  {
    id: 3,
    name: "NVIDIA NIM (Embeddings)",
    capability: "Vector Embeddings",
    model: "nvidia/nv-embed-v1",
    status: "active",
  },
  {
    id: 4,
    name: "Groq (ASR / Whisper)",
    capability: "Automatic Speech Recognition",
    model: null,
    status: "active",
  },
];

/* ------------------------------------------------------------------ */
/* Status badge                                                        */
/* ------------------------------------------------------------------ */

const STATUS_STYLES: Record<ProviderStatus, string> = {
  active: "bg-green-900/40 text-green-400",
  inactive: "bg-zinc-700/50 text-zinc-400",
  error: "bg-red-900/40 text-red-400",
};

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
  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100">AI Providers</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Configure AI models, toggle providers, set token caps and failover
          priority.
        </p>
      </div>

      {/* Provider Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {MOCK_PROVIDERS.map((provider) => (
          <div
            key={provider.id}
            className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 transition hover:border-zinc-700"
          >
            <div className="flex items-start gap-4">
              <ProviderIcon />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-zinc-200">
                    {provider.name}
                  </h3>
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${STATUS_STYLES[provider.status]}`}
                  >
                    {provider.status}
                  </span>
                </div>
                <p className="mt-1 text-xs text-zinc-500">
                  {provider.capability}
                </p>
                {provider.model && (
                  <p className="mt-2 rounded-md bg-zinc-950 px-2.5 py-1.5 font-mono text-xs text-zinc-400">
                    {provider.model}
                  </p>
                )}
              </div>
            </div>

            <div className="mt-4 flex justify-end">
              <button
                type="button"
                className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-400 transition hover:border-zinc-600 hover:text-zinc-300"
              >
                Test Connection
              </button>
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-zinc-600">
        Provider management and failover configuration will be available in a
        future release.
      </p>
    </div>
  );
}
