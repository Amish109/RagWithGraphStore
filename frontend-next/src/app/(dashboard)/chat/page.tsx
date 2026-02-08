"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useChatStore } from "@/stores/chat-store";
import { streamQuery } from "@/lib/sse";
import type { ChatMessage, Citation } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MessageBubble } from "@/components/chat/message-bubble";
import { Send, Trash2 } from "lucide-react";

export default function ChatPage() {
  const { messages, isStreaming, addMessage, updateLastMessage, setStreaming, clearMessages } =
    useChatStore();
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

    setStreaming(true);
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
          // Update last message with citations and confidence
          useChatStore.setState((state) => {
            const msgs = [...state.messages];
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
            return { messages: msgs, isStreaming: false };
          });
        },
        onError: (error) => {
          updateLastMessage(`Error: ${error}`);
          setStreaming(false);
        },
      },
      abortRef.current.signal
    );
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Chat</h1>
          <p className="text-muted-foreground text-sm">
            Ask questions about your uploaded documents.
          </p>
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

      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 && (
          <div className="text-center py-20 text-muted-foreground">
            <p className="text-lg">Ask a question about your documents</p>
            <p className="text-sm mt-1">
              Upload documents first, then ask questions to get AI-powered
              answers with citations.
            </p>
          </div>
        )}
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form
        onSubmit={handleSubmit}
        className="flex gap-2 border-t pt-4"
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
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
