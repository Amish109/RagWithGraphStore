import { EventSourceParserStream } from "eventsource-parser/stream";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onCitations: (citations: unknown[]) => void;
  onConfidence: (confidence: number, level: string) => void;
  onDone: () => void;
  onError: (error: string) => void;
}

export async function streamQuery(
  question: string,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
  documentIds?: string[]
) {
  const body: Record<string, unknown> = { query: question };
  if (documentIds && documentIds.length > 0) {
    body.document_ids = documentIds;
  }

  const res = await fetch(`${API_URL}/api/v1/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "include",
    signal,
  });

  if (!res.ok) {
    callbacks.onError(`Query failed: ${res.status}`);
    return;
  }

  if (!res.body) {
    callbacks.onError("No response body");
    return;
  }

  const stream = res.body
    .pipeThrough(new TextDecoderStream())
    .pipeThrough(new EventSourceParserStream());

  const reader = stream.getReader();

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const event = value;
      if (!event.data) continue;

      try {
        const data = JSON.parse(event.data);

        switch (event.event || data.type) {
          case "token":
            callbacks.onToken(data.token || data.content || "");
            break;
          case "citations":
            callbacks.onCitations(data.citations || []);
            break;
          case "confidence":
            callbacks.onConfidence(data.score || 0, data.level || "low");
            break;
          case "done":
            callbacks.onDone();
            break;
          case "error":
            callbacks.onError(data.message || "Stream error");
            break;
        }
      } catch {
        if (event.data && event.data !== "[DONE]") {
          callbacks.onToken(event.data);
        }
      }
    }
  } catch (err) {
    if (signal?.aborted) return;
    callbacks.onError(err instanceof Error ? err.message : "Stream failed");
  } finally {
    reader.releaseLock();
    callbacks.onDone();
  }
}
