import { Link } from "react-router-dom";
import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?:
    | { label: string; onClick: () => void }
    | { label: string; to: string };
}

export default function EmptyState({
  icon,
  title,
  description,
  action,
}: EmptyStateProps) {
  const defaultIcon = (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5m8.25 3v6.75m0 0l-3-3m3 3l3-3M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
    </svg>
  );

  return (
    <div className="rounded-xl border border-dashed border-zinc-800 bg-zinc-900/50 p-10 text-center">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-zinc-800/80 text-zinc-500">
        {icon ?? defaultIcon}
      </div>
      <p className="text-sm font-medium text-zinc-300">{title}</p>
      {description && (
        <p className="mx-auto mt-1.5 max-w-xs text-xs text-zinc-500">{description}</p>
      )}
      {action && "to" in action ? (
        <Link
          to={action.to}
          className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-indigo-600/10 px-4 py-2 text-sm font-medium text-indigo-400 transition hover:bg-indigo-600/20"
        >
          {action.label}
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>
        </Link>
      ) : action && "onClick" in action ? (
        <button
          type="button"
          onClick={action.onClick}
          className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-indigo-600/10 px-4 py-2 text-sm font-medium text-indigo-400 transition hover:bg-indigo-600/20"
        >
          {action.label}
        </button>
      ) : null}
    </div>
  );
}
