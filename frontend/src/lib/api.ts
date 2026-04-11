// NEXT_PUBLIC_API_URL is baked in at build time by Next.js.
// In Railway: set this to your backend service's public URL before deploying.
// e.g. https://recalls-backend.up.railway.app
const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" && (window as any).__NEXT_PUBLIC_API_URL__) ||
  "http://localhost:8000";

export interface Recall {
  id: string;
  agency_code: string;
  recall_number: string | null;
  title: string;
  description: string | null;
  hazard: string | null;
  remedy: string | null;
  recall_date: string | null;
  product_name: string | null;
  product_type: string | null;
  brand_name: string | null;
  manufacturer: string | null;
  units_affected: number | null;
  url: string | null;
  similarity?: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: RecallSource[];
  created_at: string;
}

export interface RecallSource {
  id: string;
  title: string;
  agency_code: string;
  recall_date: string | null;
  url: string | null;
  similarity: number;
}

export async function getLatestRecalls(limit = 20): Promise<Recall[]> {
  const res = await fetch(`${API_URL}/api/recalls/latest?limit=${limit}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch recalls");
  const data = await res.json();
  return data.recalls;
}

export async function searchRecalls(query: string, topK = 8): Promise<Recall[]> {
  const params = new URLSearchParams({ q: query, top_k: String(topK) });
  const res = await fetch(`${API_URL}/api/recalls/search?${params}`);
  if (!res.ok) throw new Error("Search failed");
  const data = await res.json();
  return data.results;
}

export async function createChatSession(): Promise<string> {
  const res = await fetch(`${API_URL}/api/chat/session`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to create session");
  const data = await res.json();
  return data.session_token;
}

export async function getChatHistory(sessionToken: string): Promise<ChatMessage[]> {
  const res = await fetch(`${API_URL}/api/chat/${sessionToken}/history`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.messages;
}

export function streamChatMessage(
  sessionToken: string,
  message: string,
  onToken: (token: string) => void,
  onDone: (sources: RecallSource[]) => void,
  onError: (err: Error) => void
): () => void {
  let aborted = false;

  (async () => {
    try {
      const res = await fetch(`${API_URL}/api/chat/${sessionToken}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, stream: true }),
      });

      if (!res.ok || !res.body) {
        throw new Error(`Chat request failed: ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (!aborted) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const token = line.slice(6);
            if (token) onToken(token);
          } else if (line.startsWith("event: done")) {
            onDone([]);
          }
        }
      }
    } catch (err) {
      if (!aborted) onError(err as Error);
    }
  })();

  return () => { aborted = true; };
}
