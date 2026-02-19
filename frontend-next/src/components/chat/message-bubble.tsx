"use client";

import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { MarkdownRenderer } from "./markdown-renderer";
import { CitationList } from "./citation-list";
import { User, Bot, Search, FileText, Brain, Network } from "lucide-react";

const TOOL_LABELS: Record<string, { label: string; icon: "search" | "file" | "brain" | "network" }> = {
  search_documents: { label: "Searching documents", icon: "search" },
  list_user_documents: { label: "Listing documents", icon: "file" },
  get_document_info: { label: "Reading document info", icon: "file" },
  get_document_summary: { label: "Reading summary", icon: "file" },
  get_document_entities: { label: "Finding entities", icon: "network" },
  get_cross_document_entities: { label: "Analyzing connections", icon: "network" },
  search_memories: { label: "Searching memories", icon: "brain" },
  get_entity_relationships: { label: "Exploring relationships", icon: "network" },
};

function ToolIcon({ type }: { type: string }) {
  switch (type) {
    case "search": return <Search className="h-3 w-3" />;
    case "file": return <FileText className="h-3 w-3" />;
    case "brain": return <Brain className="h-3 w-3" />;
    case "network": return <Network className="h-3 w-3" />;
    default: return <Search className="h-3 w-3" />;
  }
}

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  const confidenceColor =
    message.confidence_level === "high"
      ? "bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20"
      : message.confidence_level === "medium"
        ? "bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20"
        : "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20";

  return (
    <div
      className={cn(
        "flex gap-3",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-muted-foreground"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      <div
        className={cn(
          "flex-1 space-y-2 max-w-[80%]",
          isUser ? "text-right" : "text-left"
        )}
      >
        {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {message.toolCalls.map((tc, i) => {
              const info = TOOL_LABELS[tc.name] || { label: tc.name, icon: "search" };
              return (
                <Badge key={i} variant="secondary" className="text-xs gap-1 font-normal">
                  <ToolIcon type={info.icon} />
                  {info.label}
                </Badge>
              );
            })}
          </div>
        )}

        <div
          className={cn(
            "inline-block rounded-lg px-4 py-2 text-sm",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-muted"
          )}
        >
          {isUser ? (
            <p>{message.content}</p>
          ) : message.content ? (
            <MarkdownRenderer content={message.content} />
          ) : (
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-current animate-bounce" />
              <div className="h-2 w-2 rounded-full bg-current animate-bounce [animation-delay:0.1s]" />
              <div className="h-2 w-2 rounded-full bg-current animate-bounce [animation-delay:0.2s]" />
            </div>
          )}
        </div>

        {!isUser && message.confidence !== undefined && message.confidence > 0 && (
          <div className="flex items-center gap-2">
            <Badge className={cn("text-xs", confidenceColor)} variant="outline">
              {message.confidence_level} confidence ({Math.round(message.confidence * 100)}%)
            </Badge>
          </div>
        )}

        {!isUser && message.citations && message.citations.length > 0 && (
          <CitationList citations={message.citations} />
        )}
      </div>
    </div>
  );
}
