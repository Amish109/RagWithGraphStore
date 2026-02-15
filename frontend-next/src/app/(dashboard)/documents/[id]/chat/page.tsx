"use client";

import { useState, useRef, useEffect, useCallback, use } from "react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { streamQuery } from "@/lib/sse";
import type { ChatMessage, Citation, Document } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { MessageBubble } from "@/components/chat/message-bubble";
import { Send, Trash2, ArrowLeft, FileText } from "lucide-react";
import Link from "next/link";

export default function DocumentChatPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [document, setDocument] = useState<Document | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [input, setInput] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // Fetch document info
  useEffect(() => {
    async function fetchDoc() {
      try {
        const res = await apiFetch("/api/v1/documents/");
        if (res.ok) {
          const data = await res.json();
          const docs: Document[] = data.documents || data;
          const doc = docs.find((d: Document) => d.id === id);
          if (doc) setDocument(doc);
        }
      } catch {
        toast.error("Failed to load document");
      }
    }
    fetchDoc();
  }, [id]);

  const addMessage = (message: ChatMessage) => {
    setMessages((prev) => [...prev, message]);
  };

  const updateLastMessage = (content: string) => {
    setMessages((prev) => {
      const msgs = [...prev];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content };
      }
      return msgs;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    const question = input.trim();
    setInput("");

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
      timestamp: new Date(),
    };
    addMessage(userMessage);

    const assistantMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      timestamp: new Date(),
    };
    addMessage(assistantMessage);

    setIsStreaming(true);
    abortRef.current = new AbortController();

    let accumulated = "";
    let finalCitations: Citation[] = [];
    let finalConfidence = 0;
    let finalLevel = "low";

    await streamQuery(
      question,
      {
        onToken: (token) => {
          accumulated += token;
          updateLastMessage(accumulated);
        },
        onCitations: (citations) => {
          finalCitations = citations as Citation[];
        },
        onConfidence: (confidence, level) => {
          finalConfidence = confidence;
          finalLevel = level;
        },
        onDone: () => {
          setMessages((prev) => {
            const msgs = [...prev];
            const last = msgs[msgs.length - 1];
            if (last && last.role === "assistant") {
              msgs[msgs.length - 1] = {
                ...last,
                content: accumulated || last.content,
                citations: finalCitations,
                confidence: finalConfidence,
                confidence_level: finalLevel as "high" | "medium" | "low",
              };
            }
            return msgs;
          });
          setIsStreaming(false);
        },
        onError: (error) => {
          updateLastMessage(`Error: ${error}`);
          setIsStreaming(false);
        },
      },
      abortRef.current.signal,
      [id]
    );
  };

  const clearMessages = () => {
    setMessages([]);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3 min-w-0">
          <Button asChild variant="ghost" size="icon">
            <Link href={`/documents/${id}`}>
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary shrink-0" />
              <h1 className="text-lg font-bold tracking-tight truncate">
                {document?.filename || "Document"}
              </h1>
            </div>
            <p className="text-muted-foreground text-xs">
              Chat with this document only
            </p>
          </div>
        </div>
        {messages.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={clearMessages}
            disabled={isStreaming}
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Clear
          </Button>
        )}
      </div>

      {document && (
        <div className="flex items-center gap-2 mb-3 px-2">
          <Badge variant="secondary" className="text-xs">
            {document.file_type?.toUpperCase()}
          </Badge>
          {document.chunk_count != null && (
            <Badge variant="outline" className="text-xs">
              {document.chunk_count} chunks
            </Badge>
          )}
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 && (
          <div className="text-center py-20 text-muted-foreground">
            <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg">
              Ask anything about{" "}
              <span className="font-medium text-foreground">
                {document?.filename || "this document"}
              </span>
            </p>
            <p className="text-sm mt-1">
              Responses will use only this document as context.
            </p>
          </div>
        )}
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 border-t pt-4">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={`Ask about ${document?.filename || "this document"}...`}
          disabled={isStreaming}
          className="flex-1"
        />
        <Button type="submit" disabled={isStreaming || !input.trim()}>
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  );
}
