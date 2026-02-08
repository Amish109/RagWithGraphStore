"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import type { MemoryEntry } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Brain, Search, Trash2 } from "lucide-react";

export default function MemoryPage() {
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    fetchMemories();
  }, []);

  async function fetchMemories() {
    setIsLoading(true);
    try {
      const res = await apiFetch("/api/memory");
      if (res.ok) {
        const data = await res.json();
        setMemories(data.memories || []);
      }
    } catch {
      toast.error("Failed to load memories");
    } finally {
      setIsLoading(false);
    }
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      fetchMemories();
      return;
    }
    setIsSearching(true);
    try {
      const res = await apiFetch("/api/memory/search", {
        method: "POST",
        body: JSON.stringify({ query: searchQuery.trim(), limit: 20 }),
      });
      if (res.ok) {
        const data = await res.json();
        setMemories(data.memories || []);
      } else {
        toast.error("Search failed");
      }
    } catch {
      toast.error("Search failed");
    } finally {
      setIsSearching(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const res = await apiFetch(`/api/memory/${id}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setMemories((prev) => prev.filter((m) => m.id !== id));
        toast.success("Memory deleted");
      } else {
        toast.error("Delete failed");
      }
    } catch {
      toast.error("Delete failed");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Memory</h1>
        <p className="text-muted-foreground">
          Memories are automatically saved from your conversations. Here you can
          view and manage what the AI remembers about you.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Search Memories
          </CardTitle>
          <CardDescription>
            Search through your saved memories or leave empty to see all.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="flex gap-2">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search your memories..."
              disabled={isSearching}
              className="flex-1"
            />
            <Button type="submit" variant="outline" disabled={isSearching}>
              <Search className="h-4 w-4 mr-1" />
              {isSearching ? "Searching..." : "Search"}
            </Button>
            {searchQuery && (
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  setSearchQuery("");
                  fetchMemories();
                }}
              >
                Clear
              </Button>
            )}
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            Your Memories ({memories.length})
          </CardTitle>
          <CardDescription>
            These facts were automatically extracted from your conversations.
            Delete any you don&apos;t want the AI to remember.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : memories.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No memories yet. Start chatting and the AI will automatically
              remember important facts.
            </p>
          ) : (
            <div className="space-y-2">
              {memories.map((memory) => (
                <div
                  key={memory.id}
                  className="flex items-center gap-3 rounded-lg border p-3"
                >
                  <Brain className="h-4 w-4 text-muted-foreground shrink-0" />
                  <p className="text-sm flex-1">{memory.memory}</p>
                  <span className="text-xs text-muted-foreground shrink-0">
                    {new Date(memory.created_at).toLocaleDateString()}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive shrink-0"
                    onClick={() => handleDelete(memory.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
