"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { apiFetch, apiUpload } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import type { MemoryEntry, Document } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { UploadDropzone } from "@/components/documents/upload-dropzone";
import { Shield, Plus, Trash2, FileText } from "lucide-react";

export default function SharedKnowledgePage() {
  const { user } = useAuthStore();
  const router = useRouter();
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [newFact, setNewFact] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isAdding, setIsAdding] = useState(false);

  useEffect(() => {
    if (user && user.role !== "admin") {
      router.push("/");
      return;
    }
    fetchAll();
  }, [user, router]);

  async function fetchAll() {
    await Promise.all([fetchSharedMemories(), fetchDocuments()]);
  }

  async function fetchSharedMemories() {
    try {
      const res = await apiFetch("/api/v1/admin/memory/shared");
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

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await apiFetch("/api/v1/admin/documents/");
      if (res.ok) {
        const data = await res.json();
        setDocuments(data || []);
      }
    } catch {
      // silently fail — documents section is secondary
    }
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFact.trim()) return;
    setIsAdding(true);
    try {
      const res = await apiFetch("/api/v1/admin/memory/shared", {
        method: "POST",
        body: JSON.stringify({ content: newFact.trim() }),
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
      const res = await apiFetch(`/api/v1/admin/memory/shared/${id}`, {
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

  const handleUpload = async (files: File[]) => {
    for (const file of files) {
      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await apiUpload("/api/v1/admin/documents/upload", formData);
        if (res.ok) {
          toast.success(`Uploaded: ${file.name}`);
          fetchDocuments();
        } else {
          const error = await res.json();
          toast.error(`Upload failed: ${error.detail || file.name}`);
        }
      } catch {
        toast.error(`Upload failed: ${file.name}`);
      }
    }
  };

  const handleDeleteDoc = async (id: string) => {
    try {
      const res = await apiFetch(`/api/v1/admin/documents/${id}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setDocuments((prev) => prev.filter((d) => d.id !== id));
        toast.success("Document deleted");
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
          <CardTitle>Upload Knowledge Document</CardTitle>
          <CardDescription>
            Upload PDF or DOCX files as shared knowledge. Documents are
            processed, chunked, and made available for Q&A by all users.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <UploadDropzone onUpload={handleUpload} />
        </CardContent>
      </Card>

      {documents.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Uploaded Documents ({documents.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center gap-3 rounded-lg border p-3"
                >
                  <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="text-sm flex-1 truncate">
                    {doc.filename}
                  </span>
                  <Badge
                    variant={
                      doc.status === "ready" ? "default" : "secondary"
                    }
                    className="text-xs"
                  >
                    {doc.status}
                  </Badge>
                  <span className="text-xs text-muted-foreground shrink-0">
                    {new Date(doc.created_at).toLocaleDateString()}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive shrink-0"
                    onClick={() => handleDeleteDoc(doc.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Add Shared Fact</CardTitle>
          <CardDescription>
            Add individual facts to shared memory. These are available to all
            users during Q&A.
          </CardDescription>
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
          <CardTitle>Shared Facts ({memories.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : memories.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No shared facts yet.
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
