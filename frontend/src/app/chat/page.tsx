"use client";

import { Suspense, useEffect, useRef, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import {
  createChatSession,
  getChatHistory,
  streamChatMessage,
  type ChatMessage,
  type RecallSource,
  type ChartSpec,
} from "@/lib/api";
import { RecallChart } from "@/components/RecallChart";
import { ChatMarkdown } from "@/components/ChatMarkdown";

const SUGGESTIONS = [
  "Are there any recalls for baby products or cribs?",
  "What products has Fisher-Price recalled recently?",
  "Are there recalls involving fire or burn hazards?",
  "What should I do if my product is recalled?",
  "Show me recalls involving children's toys from 2024",
];

function ChatPageInner() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sources, setSources] = useState<RecallSource[]>([]);
  const [input, setInput] = useState(initialQuery);
  const [sending, setSending] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [streamingChart, setStreamingChart] = useState<ChartSpec | undefined>();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const cancelStreamRef = useRef<(() => void) | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Initialize session
  useEffect(() => {
    (async () => {
      try {
        const token = await createChatSession();
        setSessionToken(token);

        // Add welcome message
        setMessages([
          {
            id: "welcome",
            role: "assistant",
            content:
              "Hello! I'm the **CPSC Recall Assistant**. I can help you find information about consumer product recalls from the U.S. Consumer Product Safety Commission.\n\nYou can ask me things like:\n\n- \"Is my [product name] recalled?\"\n- \"Are there recalls for [brand] products?\"\n- \"What should I do if I have a recalled product?\"\n\nHow can I help you today?",
            created_at: new Date().toISOString(),
          },
        ]);
      } catch {
        setMessages([
          {
            id: "error",
            role: "assistant",
            content: "Unable to connect to the recall assistant. Please try refreshing the page.",
            created_at: new Date().toISOString(),
          },
        ]);
      }
    })();
  }, []);

  // Auto-send if initial query from homepage
  useEffect(() => {
    if (initialQuery && sessionToken && messages.length === 1) {
      setInput(initialQuery);
      sendMessage(initialQuery);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionToken]);

  useEffect(() => { scrollToBottom(); }, [messages, streamingContent]);

  const sendMessage = useCallback(
    async (text?: string) => {
      const messageText = (text ?? input).trim();
      if (!messageText || !sessionToken || sending) return;

      setSending(true);
      setInput("");
      setStreamingContent("");
      setStreamingChart(undefined);
      setSources([]);

      // Add user message immediately
      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: messageText,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);

      // Stream assistant response
      let accumulated = "";

      cancelStreamRef.current = streamChatMessage(
        sessionToken,
        messageText,
        (token) => {
          accumulated += token;
          setStreamingContent(accumulated);
          scrollToBottom();
        },
        (responseSources, responseChart) => {
          // onDone
          const assistantMsg: ChatMessage = {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: accumulated,
            sources: responseSources,
            chart: responseChart,
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, assistantMsg]);
          setStreamingContent("");
          setStreamingChart(undefined);
          setSources(responseSources);
          setSending(false);
        },
        (err) => {
          // onError
          console.error("Stream error:", err);
          const errorMsg: ChatMessage = {
            id: `error-${Date.now()}`,
            role: "assistant",
            content: "I encountered an error processing your request. Please try again.",
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, errorMsg]);
          setStreamingContent("");
          setSending(false);
        },
        (chart) => {
          // onChart — show chart immediately while text is still streaming
          setStreamingChart(chart);
        }
      );
    },
    [input, sessionToken, sending]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleSuggestion = (suggestion: string) => {
    setInput(suggestion);
    sendMessage(suggestion);
  };

  return (
    <div className="grid-container">
      <div className="chat-layout">
        {/* Main chat window */}
        <div>
          <div style={{ marginBottom: "1rem" }}>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#1b1b1b", marginBottom: ".25rem" }}>
              CPSC Recall Assistant
            </h1>
            <p style={{ color: "#565c65", fontSize: ".9rem", margin: 0 }}>
              Ask me anything about consumer product recalls. I search the CPSC database to answer your questions.
            </p>
          </div>

          {/* Suggested questions — show only when no messages beyond welcome */}
          {messages.length <= 1 && (
            <div className="suggestions" role="list" aria-label="Suggested questions">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  className="suggestion-btn"
                  role="listitem"
                  onClick={() => handleSuggestion(s)}
                  disabled={sending}
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Chat window */}
          <div className="chat-window" role="log" aria-live="polite" aria-label="Chat conversation">
            <div className="chat-messages">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}

              {/* Streaming bubble */}
              {(streamingContent || streamingChart) && (
                <div className="chat-bubble chat-bubble--assistant">
                  {streamingChart && <RecallChart spec={streamingChart} />}
                  {streamingContent ? (
                    <>
                      <ChatMarkdown>{streamingContent}</ChatMarkdown>
                      <span aria-hidden="true" style={{ opacity: .5 }}>▌</span>
                    </>
                  ) : null}
                </div>
              )}

              {/* Typing indicator */}
              {sending && !streamingContent && (
                <div className="chat-bubble chat-bubble--assistant chat-bubble--typing" role="status" aria-label="Assistant is typing">
                  Searching recall database...
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input row */}
            <div className="chat-input-row">
              <label htmlFor="chat-input" className="usa-sr-only">
                Type your message
              </label>
              <textarea
                id="chat-input"
                ref={textareaRef}
                rows={2}
                placeholder="Ask about a product, brand, or hazard..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={sending}
                aria-label="Type your recall question"
              />
              <button
                className="chat-send-btn"
                onClick={() => sendMessage()}
                disabled={sending || !input.trim()}
                aria-label="Send message"
              >
                Send
              </button>
            </div>
          </div>

          <p style={{ fontSize: ".8rem", color: "#71767a", marginTop: ".5rem" }}>
            Press Enter to send · Shift+Enter for new line · Data sourced from{" "}
            <a href="https://www.saferproducts.gov" style={{ color: "#005288" }}>saferproducts.gov</a>
          </p>
        </div>

        {/* Sources / sidebar */}
        <aside aria-label="Recall sources cited">
          <div className="sources-panel">
            <h2>Sources</h2>
            {sources.length === 0 ? (
              <p style={{ fontSize: ".85rem", color: "#71767a" }}>
                Recall sources used by the assistant will appear here after you ask a question.
              </p>
            ) : (
              <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                {sources.map((s) => (
                  <li key={s.id} className="source-item">
                    <div style={{ fontWeight: 600, color: "#1b1b1b", fontSize: ".85rem", marginBottom: ".2rem" }}>
                      {s.title}
                    </div>
                    <div style={{ fontSize: ".78rem", color: "#565c65" }}>
                      {s.recall_date && new Date(s.recall_date).toLocaleDateString("en-US", { year: "numeric", month: "short" })}
                      {s.recall_date && " · "}
                      Match: {Math.round(s.similarity * 100)}%
                    </div>
                    {s.url && (
                      <a href={s.url} target="_blank" rel="noopener noreferrer" className="source-item" style={{ fontSize: ".78rem" }}>
                        View on CPSC.gov
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Safety tip */}
          <div className="sources-panel" style={{ marginTop: "1rem" }}>
            <h2>Safety Resources</h2>
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: ".5rem" }}>
              {[
                { label: "CPSC Recall List", href: "https://www.cpsc.gov/Recalls" },
                { label: "Report a Safety Problem", href: "https://www.saferproducts.gov" },
                { label: "Sign Up for Recall Alerts", href: "https://www.cpsc.gov/cpsc-recalls-signup" },
                { label: "CPSC Hotline: 800-638-2772", href: "tel:800-638-2772" },
              ].map((link) => (
                <li key={link.href}>
                  <a href={link.href} style={{ fontSize: ".85rem", color: "#005288" }}
                    target={link.href.startsWith("http") ? "_blank" : undefined}
                    rel={link.href.startsWith("http") ? "noopener noreferrer" : undefined}
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense>
      <ChatPageInner />
    </Suspense>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div
      className={`chat-bubble ${isUser ? "chat-bubble--user" : "chat-bubble--assistant"}`}
      role={isUser ? undefined : "article"}
      aria-label={isUser ? "Your message" : "Assistant response"}
    >
      {message.chart && <RecallChart spec={message.chart} />}
      {isUser ? (
        message.content
      ) : (
        <ChatMarkdown>{message.content}</ChatMarkdown>
      )}
    </div>
  );
}
