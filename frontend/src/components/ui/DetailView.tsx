import type { ReactNode } from "react";

interface DetailItem {
  label: string;
  value: ReactNode;
}

interface DetailViewProps {
  items: DetailItem[];
  columns?: 1 | 2 | 3;
}

export default function DetailView({ items, columns = 2 }: DetailViewProps) {
  const colClass =
    columns === 1
      ? "grid-cols-1"
      : columns === 3
        ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
        : "grid-cols-1 sm:grid-cols-2";

  return (
    <div className={`grid ${colClass} gap-4`}>
      {items.map((item) => (
        <div key={item.label}>
          <label className="block text-xs font-medium text-zinc-500">
            {item.label}
          </label>
          <p className="mt-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200">
            {item.value ?? "—"}
          </p>
        </div>
      ))}
    </div>
  );
}
