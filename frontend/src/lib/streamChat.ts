/**
 * Streams the copilot's reply from POST /api/chat/stream.
 *
 * The endpoint sends Server-Sent Events: progress frames carry a friendly
 * label ("Finding vendors"); the final frame carries the full reply. We read
 * the response body directly because the API client only handles plain JSON.
 */

export interface ChatResult {
  message: string;
  data: Record<string, unknown>;
  success: boolean;
}

function getCsrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)aeros_csrf=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

/**
 * Send a message and stream progress. Calls `onStep` for each progress update
 * and resolves with the final reply. Throws on transport/HTTP failure so the
 * caller can fall back to the non-streaming endpoint.
 */
export async function streamChat(
  body: Record<string, unknown>,
  onStep: (label: string) => void,
): Promise<ChatResult> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const csrf = getCsrfToken();
  if (csrf) headers["x-csrf-token"] = csrf;

  const res = await fetch("/api/chat/stream", {
    method: "POST",
    headers,
    credentials: "include",
    body: JSON.stringify(body),
  });

  if (!res.ok || !res.body) {
    throw new Error(`stream failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: ChatResult | null = null;

  const handleFrame = (frame: string) => {
    const line = frame.trim();
    if (!line.startsWith("data:")) return;
    const payload = line.slice(5).trim();
    if (!payload) return;
    let event: { type?: string; label?: string } & Partial<ChatResult>;
    try {
      event = JSON.parse(payload);
    } catch {
      return;
    }
    if (event.type === "step" && event.label) {
      onStep(event.label);
    } else if (event.type === "result") {
      result = {
        message: event.message ?? "",
        data: event.data ?? {},
        success: event.success ?? true,
      };
    }
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      handleFrame(buffer.slice(0, sep));
      buffer = buffer.slice(sep + 2);
    }
  }
  if (buffer.trim()) handleFrame(buffer);

  if (!result) throw new Error("stream ended without a result");
  return result;
}
