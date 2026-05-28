interface FilterChipsProps {
  options: { label: string; value: string }[];
  active: string;
  onChange: (value: string) => void;
}

export default function FilterChips({
  options,
  active,
  onChange,
}: FilterChipsProps) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all duration-150 ${
            active === opt.value
              ? "bg-indigo-600 text-white shadow-sm shadow-indigo-600/25"
              : "bg-zinc-800/80 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
