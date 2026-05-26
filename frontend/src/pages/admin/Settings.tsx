/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface ConfigSection {
  title: string;
  items: { label: string; value: string }[];
}

/* ------------------------------------------------------------------ */
/* Mock configuration data                                             */
/* ------------------------------------------------------------------ */

const CONFIG_SECTIONS: ConfigSection[] = [
  {
    title: "Application",
    items: [
      { label: "Name", value: "AEROS" },
      { label: "Version", value: "v0.1.0" },
      { label: "Environment", value: "Development" },
      { label: "Log Level", value: "DEBUG" },
    ],
  },
  {
    title: "Database",
    items: [
      { label: "Engine", value: "SQLite" },
      { label: "Journal Mode", value: "WAL" },
      { label: "Path", value: "data/aeros.db" },
      { label: "Busy Timeout", value: "5000 ms" },
    ],
  },
  {
    title: "Upload",
    items: [
      { label: "Max File Size", value: "25 MB" },
      { label: "Upload Directory", value: "data/uploads" },
      { label: "Allowed Types", value: "PDF, PNG, JPG, WEBP" },
      { label: "Voice Format", value: "WAV, WEBM, OGG" },
    ],
  },
  {
    title: "Security",
    items: [
      { label: "Auth Method", value: "JWT (HS256)" },
      { label: "Token Expiry", value: "24 hours" },
      { label: "HMAC Algorithm", value: "SHA256" },
      { label: "CORS", value: "localhost:5173" },
    ],
  },
];

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

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function AdminSettings() {
  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100">
          System Settings
        </h1>
        <p className="mt-1 text-sm text-zinc-500">
          Retention policies, rate limits, budgets, and system configuration.
        </p>
      </div>

      {/* Config Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {CONFIG_SECTIONS.map((section) => (
          <div
            key={section.title}
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
                    d={SECTION_ICONS[section.title]}
                  />
                </svg>
              </div>
              <h2 className="text-sm font-medium text-zinc-200">
                {section.title}
              </h2>
            </div>

            <div className="mt-4 space-y-2.5">
              {section.items.map((item) => (
                <div
                  key={item.label}
                  className="flex items-center justify-between"
                >
                  <span className="text-xs text-zinc-500">{item.label}</span>
                  <span className="rounded-md bg-zinc-950 px-2 py-0.5 font-mono text-xs text-zinc-300">
                    {item.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-zinc-600">
        Configuration is read-only. Changes require editing environment
        variables and restarting the server.
      </p>
    </div>
  );
}
