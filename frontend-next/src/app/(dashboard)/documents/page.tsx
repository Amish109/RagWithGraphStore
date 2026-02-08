"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { apiFetch, apiUpload } from "@/lib/api";
import type { Document } from "@/lib/types";
import { UploadDropzone } from "@/components/documents/upload-dropzone";
import { DocumentList } from "@/components/documents/document-list";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);

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
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleUpload = async (files: File[]) => {
    for (const file of files) {
      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await apiUpload("/api/v1/documents/upload", formData);
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
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Documents</h1>
        <p className="text-muted-foreground">
          Upload and manage your documents for intelligent Q&A.
        </p>
      </div>

      <UploadDropzone onUpload={handleUpload} />

      <DocumentList
        documents={documents}
        isLoading={isLoading}
        onDelete={handleDelete}
        onRefresh={fetchDocuments}
      />
    </div>
  );
}
