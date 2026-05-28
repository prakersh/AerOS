interface Step {
  key: string;
  label: string;
  description?: string;
}

interface LifecycleStepperProps {
  steps: Step[];
  currentStep: string;
  onStepClick?: (stepKey: string) => void;
}

const STEP_COLORS: Record<string, string> = {
  completed: "bg-green-600 text-white",
  current: "bg-indigo-600 text-white ring-4 ring-indigo-600/30",
  upcoming: "bg-zinc-800 text-zinc-500",
  skipped: "bg-zinc-700 text-zinc-400 line-through",
};

export default function LifecycleStepper({
  steps,
  currentStep,
  onStepClick,
}: LifecycleStepperProps) {
  const currentIdx = steps.findIndex((s) => s.key === currentStep);

  function getStepStatus(idx: number): "completed" | "current" | "upcoming" {
    if (idx < currentIdx) return "completed";
    if (idx === currentIdx) return "current";
    return "upcoming";
  }

  return (
    <div className="flex items-center gap-1 overflow-x-auto pb-2">
      {steps.map((step, idx) => {
        const status = getStepStatus(idx);
        const colorClass = STEP_COLORS[status];
        const isClickable = status === "completed" && onStepClick;

        return (
          <div key={step.key} className="flex items-center">
            {/* Step circle + label */}
            <button
              type="button"
              onClick={() => { if (isClickable && onStepClick) onStepClick(step.key); }}
              disabled={!isClickable}
              className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium transition ${colorClass} ${isClickable ? "cursor-pointer hover:opacity-80" : "cursor-default"}`}
            >
              {status === "completed" ? (
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-white/20 text-[10px] font-bold">
                  {idx + 1}
                </span>
              )}
              <span className="whitespace-nowrap">{step.label}</span>
            </button>

            {/* Connector line */}
            {idx < steps.length - 1 && (
              <div
                className={`mx-1 h-0.5 w-6 shrink-0 ${
                  idx < currentIdx ? "bg-green-600" : "bg-zinc-800"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
