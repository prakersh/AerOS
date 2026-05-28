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
    <div className="group rounded-xl border border-zinc-800 bg-zinc-900 p-5 transition-all duration-200 hover:border-zinc-700 hover:bg-zinc-800/50 hover:shadow-lg hover:shadow-black/20">
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
          {label}
        </p>
        {icon && <div className="text-zinc-600 transition-colors group-hover:text-zinc-400">{icon}</div>}
      </div>
      <p className={`mt-3 text-3xl font-bold tabular-nums tracking-tight ${accent}`}>
        {value}
      </p>
    </div>
  );
}
