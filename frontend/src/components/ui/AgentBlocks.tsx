/**
 * AgentBlocks — renders an agent's visual reply from a typed list of blocks.
 *
 * The backend (src/aeros/ai/ui_blocks.py) emits `data.blocks`; this renderer
 * maps each typed block to a trusted component. No raw HTML is ever rendered,
 * so agent output stays XSS-safe while still being fully "visual".
 */

import type { ReactNode } from "react";

export interface AgentAction {
  id: string;
  label: string;
  style?: "primary" | "secondary" | "danger";
  kind: "navigate" | "post";
  path?: string;
  endpoint?: string;
  payload?: Record<string, unknown>;
  confirm?: string;
}

type Cell = string | number | { value: string; highlight?: "good" | "bad" | "muted" | null; sub?: string };

export interface AgentBlock {
  type: "text" | "table" | "card" | "keyvalue" | "list" | "actions";
  [key: string]: unknown;
}

function renderInline(text: string): ReactNode {
  // Inline formatting: **bold**, *italic*, and `code`. Splitting on all three
  // at once keeps order intact; anything else renders as plain text.
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return parts.map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**")) {
      return (
        <strong key={i} className="text-zinc-100">
          {p.slice(2, -2)}
        </strong>
      );
    }
    if (p.startsWith("`") && p.endsWith("`")) {
      return (
        <code key={i} className="rounded bg-zinc-800 px-1 py-0.5 text-[11px] text-indigo-300">
          {p.slice(1, -1)}
        </code>
      );
    }
    if (p.startsWith("*") && p.endsWith("*") && p.length > 2) {
      return <em key={i}>{p.slice(1, -1)}</em>;
    }
    return <span key={i}>{p}</span>;
  });
}

function CellView({ cell }: { cell: Cell }) {
  if (cell === null || cell === undefined) return <span className="text-zinc-600">—</span>;
  if (typeof cell === "string" || typeof cell === "number") return <span>{cell}</span>;
  const color =
    cell.highlight === "good"
      ? "text-green-400 font-semibold"
      : cell.highlight === "bad"
        ? "text-red-400"
        : cell.highlight === "muted"
          ? "text-zinc-600"
          : "text-zinc-300";
  return (
    <span className={color}>
      {cell.value}
      {cell.sub && <span className="ml-1 text-[10px] text-zinc-500">{cell.sub}</span>}
    </span>
  );
}

const ACCENTS: Record<string, string> = {
  indigo: "border-indigo-700/60 bg-indigo-950/20",
  green: "border-green-800/50 bg-green-950/15",
  amber: "border-amber-800/50 bg-amber-950/15",
};

function TableBlock({ block }: { block: AgentBlock }) {
  const title = block.title as string | undefined;
  const columns = (block.columns as { key: string; label: string; align?: string }[]) ?? [];
  const rows = (block.rows as Record<string, Cell>[]) ?? [];
  const note = block.note as string | undefined;
  return (
    <div className="mt-3 overflow-x-auto rounded-lg border border-zinc-700 bg-zinc-900 p-3">
      {title && <p className="mb-2 text-xs font-semibold text-indigo-400">{title}</p>}
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-zinc-800 text-zinc-500">
            {columns.map((c) => (
              <th key={c.key} className={`py-1 ${c.align === "right" ? "text-right" : "text-left"}`}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-zinc-800/50">
              {columns.map((c) => (
                <td key={c.key} className={`py-1.5 ${c.align === "right" ? "text-right" : "text-left text-zinc-300"}`}>
                  <CellView cell={row[c.key]} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {note && <p className="mt-2 text-[10px] text-zinc-500">{note}</p>}
    </div>
  );
}

function CardBlock({ block }: { block: AgentBlock }) {
  const accent = ACCENTS[(block.accent as string) ?? "indigo"] ?? ACCENTS.indigo;
  const fields = (block.fields as { label: string; value: string; emphasis?: boolean }[]) ?? [];
  return (
    <div className={`mt-3 rounded-lg border p-3 ${accent}`}>
      <p className="text-sm font-semibold text-zinc-100">{block.title as string}</p>
      {!!block.subtitle && <p className="mt-0.5 text-xs text-zinc-400">{block.subtitle as string}</p>}
      <div className="mt-2 grid gap-1 text-xs">
        {fields.map((f, i) => (
          <div key={i} className="flex justify-between gap-4">
            <span className="text-zinc-500">{f.label}</span>
            <span className={f.emphasis ? "font-medium text-zinc-100" : "text-zinc-300"}>{f.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function KeyValueBlock({ block }: { block: AgentBlock }) {
  const items = (block.items as { label: string; value: string }[]) ?? [];
  return (
    <div className="mt-3 rounded-lg border border-zinc-700 bg-zinc-900 p-3">
      {!!block.title && <p className="mb-2 text-xs font-semibold text-indigo-400">{block.title as string}</p>}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        {items.map((it, i) => (
          <div key={i} className="flex justify-between">
            <span className="text-zinc-500">{it.label}</span>
            <span className="text-zinc-200">{it.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ListBlock({ block }: { block: AgentBlock }) {
  const items = (block.items as string[]) ?? [];
  const ordered = !!block.ordered;
  const Tag = ordered ? "ol" : "ul";
  return (
    <div className="mt-3 rounded-lg border border-zinc-700 bg-zinc-900 p-3">
      {!!block.title && <p className="mb-2 text-xs font-semibold text-indigo-400">{block.title as string}</p>}
      <Tag className={`text-xs text-zinc-300 ${ordered ? "list-decimal" : "list-disc"} pl-4`}>
        {items.map((it, i) => (
          <li key={i} className="py-0.5">
            {renderInline(it)}
          </li>
        ))}
      </Tag>
    </div>
  );
}

const BTN_STYLES: Record<string, string> = {
  primary: "bg-indigo-600 text-white hover:bg-indigo-500",
  secondary: "border border-zinc-700 text-zinc-300 hover:bg-zinc-800",
  danger: "border border-red-800/50 bg-red-900/20 text-red-400 hover:bg-red-900/40",
};

function ActionsBlock({
  block,
  onAction,
  disabled,
}: {
  block: AgentBlock;
  onAction?: (a: AgentAction) => void;
  disabled?: boolean;
}) {
  const actions = (block.actions as AgentAction[]) ?? [];
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {actions.map((a) => (
        <button
          key={a.id}
          type="button"
          disabled={disabled}
          onClick={() => onAction?.(a)}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium transition disabled:opacity-50 ${
            BTN_STYLES[a.style ?? "secondary"]
          }`}
        >
          {a.label}
        </button>
      ))}
    </div>
  );
}

export function AgentBlocks({
  blocks,
  onAction,
  actionsDisabled,
}: {
  blocks: AgentBlock[];
  onAction?: (a: AgentAction) => void;
  actionsDisabled?: boolean;
}) {
  if (!blocks || blocks.length === 0) return null;
  return (
    <div>
      {blocks.map((block, i) => {
        switch (block.type) {
          case "text":
            return (
              <p key={i} className="mt-2 whitespace-pre-wrap text-xs text-zinc-300">
                {renderInline((block.markdown as string) ?? "")}
              </p>
            );
          case "table":
            return <TableBlock key={i} block={block} />;
          case "card":
            return <CardBlock key={i} block={block} />;
          case "keyvalue":
            return <KeyValueBlock key={i} block={block} />;
          case "list":
            return <ListBlock key={i} block={block} />;
          case "actions":
            return <ActionsBlock key={i} block={block} onAction={onAction} disabled={actionsDisabled} />;
          default:
            return null;
        }
      })}
    </div>
  );
}
