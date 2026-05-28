interface LoadingSpinnerProps {
  message?: string;
  size?: "sm" | "md";
}

export default function LoadingSpinner({
  message = "Loading...",
  size = "md",
}: LoadingSpinnerProps) {
  const spinnerSize = size === "sm" ? "h-4 w-4" : "h-5 w-5";
  return (
    <div className="flex flex-col items-center justify-center py-16 animate-fade-in">
      <div className="relative">
        <div
          className={`${spinnerSize} animate-spin rounded-full border-2 border-zinc-700 border-t-indigo-500`}
        />
      </div>
      <span className="mt-3 text-xs font-medium text-zinc-500">{message}</span>
    </div>
  );
}
