interface LoadingSpinnerProps {
  message?: string;
  size?: "sm" | "md";
}

export default function LoadingSpinner({
  message = "Loading...",
  size = "md",
}: LoadingSpinnerProps) {
  const spinnerSize = size === "sm" ? "h-4 w-4" : "h-6 w-6";
  return (
    <div className="flex items-center justify-center py-12">
      <div
        className={`${spinnerSize} animate-spin rounded-full border-2 border-zinc-600 border-t-indigo-500`}
      />
      <span className="ml-3 text-sm text-zinc-500">{message}</span>
    </div>
  );
}
