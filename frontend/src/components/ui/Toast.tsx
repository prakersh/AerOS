import { useEffect, useState, useCallback } from "react";

interface ToastItem {
  id: number;
  message: string;
  type: "success" | "error";
}

let toastId = 0;
let listeners: Array<(toasts: ToastItem[]) => void> = [];
let toasts: ToastItem[] = [];

function notify() {
  for (const l of listeners) l([...toasts]);
}

export function showToast(message: string, type: "success" | "error" = "success") {
  const id = ++toastId;
  toasts = [...toasts, { id, message, type }];
  notify();
  setTimeout(() => {
    toasts = toasts.filter((t) => t.id !== id);
    notify();
  }, 3000);
}

export function ToastContainer() {
  const [items, setItems] = useState<ToastItem[]>([]);

  useEffect(() => {
    listeners.push(setItems);
    return () => {
      listeners = listeners.filter((l) => l !== setItems);
    };
  }, []);

  if (items.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {items.map((t) => (
        <div
          key={t.id}
          className={`animate-slide-up flex items-center gap-2.5 rounded-lg border px-4 py-3 text-sm shadow-xl shadow-black/30 backdrop-blur-sm ${
            t.type === "success"
              ? "border-green-800/50 bg-green-900/90 text-green-300"
              : "border-red-800/50 bg-red-900/90 text-red-300"
          }`}
        >
          {t.type === "success" ? (
            <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ) : (
            <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
          )}
          {t.message}
        </div>
      ))}
    </div>
  );
}

// Re-export default Toast as a hook-based component
export default function Toast({
  message,
  type = "success",
  onClose,
  duration = 3000,
}: {
  message: string;
  type?: "success" | "error";
  onClose: () => void;
  duration?: number;
}) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(onClose, 300);
    }, duration);
    return () => clearTimeout(timer);
  }, [duration, onClose]);

  return (
    <div
      className={`fixed bottom-4 right-4 z-50 rounded-lg border px-4 py-3 text-sm shadow-lg transition-all duration-300 ${
        type === "success"
          ? "border-green-800/50 bg-green-900/80 text-green-300"
          : "border-red-800/50 bg-red-900/80 text-red-300"
      } ${visible ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0"}`}
    >
      {message}
    </div>
  );
}
