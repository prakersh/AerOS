import type { ReactNode } from "react";

interface KpiCardProps {
  label: string;
  value: string | number;
  accent?: string;
  icon?: ReactNode;
}

export default function KpiCard({
  label,
  value,
  accent = "text-zinc-100",
  icon,
}: KpiCardProps) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 transition hover:border-zinc-700 hover:bg-zinc-800/70">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
          {label}
        </p>
        {icon && <div className="text-zinc-600">{icon}</div>}
      </div>
      <p className={`mt-2 text-3xl font-semibold tabular-nums ${accent}`}>
        {value}
      </p>
    </div>
  );
}
