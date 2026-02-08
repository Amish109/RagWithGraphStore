"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import type { MemoryEntry } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Shield, Plus, Trash2 } from "lucide-react";

export default function SharedKnowledgePage() {
  const { user } = useAuthStore();
  const router = useRouter();
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [newFact, setNewFact] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isAdding, setIsAdding] = useState(false);

  useEffect(() => {
    if (user && user.role !== "admin") {
      router.push("/");
      return;
    }
    fetchSharedMemories();
  }, [user, router]);

  async function fetchSharedMemories() {
    try {
      const res = await apiFetch("/api/admin/shared-memory/list");
      if (res.ok) {
        const data = await res.json();
        setMemories(data.memories || data);
      }
    } catch {
      toast.error("Failed to load shared knowledge");
    } finally {
      setIsLoading(false);
    }
  }

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFact.trim()) return;
    setIsAdding(true);
    try {
      const res = await apiFetch("/api/admin/shared-memory/add", {
        method: "POST",
        body: JSON.stringify({ text: newFact.trim() }),
      });
      if (res.ok) {
        toast.success("Shared knowledge added");
        setNewFact("");
        fetchSharedMemories();
      } else {
        toast.error("Failed to add");
      }
    } catch {
      toast.error("Failed to add");
    } finally {
      setIsAdding(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const res = await apiFetch(`/api/admin/shared-memory/${id}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setMemories((prev) => prev.filter((m) => m.id !== id));
        toast.success("Deleted");
      } else {
        toast.error("Delete failed");
      }
    } catch {
      toast.error("Delete failed");
    }
  };

  if (user?.role !== "admin") return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Shield className="h-6 w-6" />
          Shared Knowledge
        </h1>
        <p className="text-muted-foreground">
          Manage company-wide knowledge accessible to all authenticated users.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Add Shared Fact</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleAdd} className="flex gap-2">
            <Input
              value={newFact}
              onChange={(e) => setNewFact(e.target.value)}
              placeholder="Enter a shared knowledge fact..."
              disabled={isAdding}
              className="flex-1"
            />
            <Button type="submit" disabled={isAdding || !newFact.trim()}>
              <Plus className="h-4 w-4 mr-1" />
              Add
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Shared Knowledge ({memories.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : memories.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No shared knowledge yet.
            </p>
          ) : (
            <div className="space-y-2">
              {memories.map((memory) => (
                <div
                  key={memory.id}
                  className="flex items-center gap-3 rounded-lg border p-3"
                >
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
