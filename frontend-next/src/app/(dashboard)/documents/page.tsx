"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { toast } from "sonner";
import { apiFetch, apiUpload } from "@/lib/api";
import type { Document } from "@/lib/types";
import { UploadDropzone } from "@/components/documents/upload-dropzone";
import { DocumentList } from "@/components/documents/document-list";
import { Button } from "@/components/ui/button";
import { RefreshCw, Loader2, XCircle, Upload } from "lucide-react";

interface ProcessingDoc {
  id: string;
  filename: string;
  status: string;
  progress: number;
  message: string;
  error?: string;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [processingDocs, setProcessingDocs] = useState<ProcessingDoc[]>([]);
  const pollingRefs = useRef<Set<string>>(new Set());

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await apiFetch("/api/v1/documents/");
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.documents || data);
      }
    } catch {
      toast.error("Failed to load documents");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  // Poll a single document's status until completed or failed
  const pollDocumentStatus = useCallback(
    async (documentId: string, filename: string) => {
      // Prevent duplicate polling for same document
      if (pollingRefs.current.has(documentId)) return;
      pollingRefs.current.add(documentId);

      // Add to processing list if not already there
      setProcessingDocs((prev) => {
        if (prev.some((d) => d.id === documentId)) return prev;
        return [
          ...prev,
          { id: documentId, filename, status: "pending", progress: 0, message: "Starting..." },
        ];
      });

      const maxAttempts = 300;
      for (let i = 0; i < maxAttempts; i++) {
        await new Promise((r) => setTimeout(r, 2000));
        try {
          const res = await apiFetch(
            `/api/v1/documents/${documentId}/status`
          );
          if (!res.ok) continue;
          const data = await res.json();

          setProcessingDocs((prev) =>
            prev.map((d) =>
              d.id === documentId
                ? { ...d, status: data.status, progress: data.progress, message: data.message, error: data.error }
                : d
            )
          );

          if (data.status === "completed") {
            toast.success(`Processed: ${filename}`);
            setProcessingDocs((prev) => prev.filter((d) => d.id !== documentId));
            pollingRefs.current.delete(documentId);
            fetchDocuments();
            return;
          }
          if (data.status === "failed") {
            pollingRefs.current.delete(documentId);
            return;
          }
        } catch {
          // keep polling
        }
      }
      toast.error(`Processing timed out: ${filename}`);
      setProcessingDocs((prev) => prev.filter((d) => d.id !== documentId));
      pollingRefs.current.delete(documentId);
    },
    [fetchDocuments]
  );

  // On page load: fetch documents AND restore any in-progress tasks from Redis
  useEffect(() => {
    fetchDocuments();

    // Check for in-progress tasks (survives page refresh)
    const restoreProcessingTasks = async () => {
      try {
        const res = await apiFetch("/api/v1/documents/processing");
        if (res.ok) {
          const tasks = await res.json();
          for (const task of tasks) {
            // Resume polling for each in-progress task
            pollDocumentStatus(task.document_id, task.filename || task.message || "Document");
          }
        }
      } catch {
        // Not critical — just won't restore processing state
      }
    };
    restoreProcessingTasks();
  }, [fetchDocuments, pollDocumentStatus]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchDocuments();
  };

  const dismissProcessing = (id: string) => {
    setProcessingDocs((prev) => prev.filter((d) => d.id !== id));
  };

  const handleUpload = async (files: File[]) => {
    for (const file of files) {
      // Show "Uploading..." immediately so user sees feedback
      const tempId = `uploading-${Date.now()}-${file.name}`;
      setProcessingDocs((prev) => [
        ...prev,
        { id: tempId, filename: file.name, status: "uploading", progress: 0, message: "Uploading file..." },
      ]);

      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await apiUpload("/api/v1/documents/upload", formData);
        // Remove temp uploading entry
        setProcessingDocs((prev) => prev.filter((d) => d.id !== tempId));

        if (res.ok) {
          const data = await res.json();
          pollDocumentStatus(data.document_id, file.name);
        } else {
          const error = await res.json();
          toast.error(`Upload failed: ${error.detail || file.name}`);
        }
      } catch {
        setProcessingDocs((prev) => prev.filter((d) => d.id !== tempId));
        toast.error(`Upload failed: ${file.name}`);
      }
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const res = await apiFetch(`/api/v1/documents/${id}`, {
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Documents</h1>
          <p className="text-muted-foreground">
            Upload and manage your documents for intelligent Q&A.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <UploadDropzone onUpload={handleUpload} />

      {processingDocs.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-muted-foreground">Processing</h2>
          {processingDocs.map((doc) => {
            const failed = doc.status === "failed";
            const uploading = doc.status === "uploading";
            return (
              <div
                key={doc.id}
                className={`flex items-center gap-3 rounded-lg border p-3 ${failed ? "border-destructive/50 bg-destructive/5" : "bg-muted/30"}`}
              >
                {failed ? (
                  <XCircle className="h-4 w-4 shrink-0 text-destructive" />
                ) : uploading ? (
                  <Upload className="h-4 w-4 shrink-0 animate-pulse text-primary" />
                ) : (
                  <Loader2 className="h-4 w-4 shrink-0 animate-spin text-primary" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{doc.filename}</p>
                  <p className={`text-xs ${failed ? "text-destructive" : "text-muted-foreground"}`}>
                    {failed ? doc.error || "Processing failed" : doc.message}
                  </p>
                </div>
                {failed ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => dismissProcessing(doc.id)}
                    className="text-xs text-muted-foreground"
                  >
                    Dismiss
                  </Button>
                ) : (
                  <div className="flex items-center gap-2 shrink-0">
                    <div className="w-24 h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary transition-all duration-500"
                        style={{ width: `${doc.progress}%` }}
                      />
                    </div>
                    <span className="text-xs text-muted-foreground w-8 text-right">
                      {doc.progress}%
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <DocumentList
        documents={documents}
        isLoading={isLoading}
        onDelete={handleDelete}
        onRefresh={fetchDocuments}
      />
    </div>
  );
}
