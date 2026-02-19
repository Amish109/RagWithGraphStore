"use client";

import { create } from "zustand";
import type { ChatMessage, ToolCallInfo } from "@/lib/types";

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  activeDocumentIds: string[];
  addMessage: (message: ChatMessage) => void;
  updateLastMessage: (content: string) => void;
  addToolCall: (toolCall: ToolCallInfo) => void;
  setStreaming: (isStreaming: boolean) => void;
  setActiveDocuments: (ids: string[]) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  activeDocumentIds: [],
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  updateLastMessage: (content) =>
    set((state) => {
      const messages = [...state.messages];
      const last = messages[messages.length - 1];
      if (last && last.role === "assistant") {
        messages[messages.length - 1] = { ...last, content };
      }
      return { messages };
    }),
  addToolCall: (toolCall) =>
    set((state) => {
      const messages = [...state.messages];
      const last = messages[messages.length - 1];
      if (last && last.role === "assistant") {
        messages[messages.length - 1] = {
          ...last,
          toolCalls: [...(last.toolCalls || []), toolCall],
        };
      }
      return { messages };
    }),
  setStreaming: (isStreaming) => set({ isStreaming }),
  setActiveDocuments: (ids) => set({ activeDocumentIds: ids }),
  clearMessages: () => set({ messages: [] }),
}));
