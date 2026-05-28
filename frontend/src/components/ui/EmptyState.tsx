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
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-8 text-center">
      {icon && (
        <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-zinc-800 text-zinc-500">
          {icon}
        </div>
      )}
      <p className="text-sm font-medium text-zinc-300">{title}</p>
      {description && (
        <p className="mt-1 text-xs text-zinc-500">{description}</p>
      )}
      {action && "to" in action ? (
        <Link
          to={action.to}
          className="mt-3 inline-block text-sm text-indigo-400 hover:text-indigo-300"
        >
          {action.label}
        </Link>
      ) : action && "onClick" in action ? (
        <button
          type="button"
          onClick={action.onClick}
          className="mt-3 inline-block text-sm text-indigo-400 hover:text-indigo-300"
        >
          {action.label}
        </button>
      ) : null}
    </div>
  );
}
