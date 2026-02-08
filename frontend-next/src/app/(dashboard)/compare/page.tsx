"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import type { Document, ComparisonResult } from "@/lib/types";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import { FileText, GitCompareArrows, Loader2 } from "lucide-react";

export default function ComparePage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [isComparing, setIsComparing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchDocs() {
      try {
        const res = await apiFetch("/api/documents");
        if (res.ok) {
          const data = await res.json();
          setDocuments(
            (data.documents || data).filter(
              (d: Document) => d.status === "ready"
            )
          );
        }
      } catch {
        toast.error("Failed to load documents");
      } finally {
        setIsLoading(false);
      }
    }
    fetchDocs();
  }, []);

  const toggleSelect = (id: string) => {
    setSelected((prev) =>
      prev.includes(id)
        ? prev.filter((d) => d !== id)
        : prev.length < 5
          ? [...prev, id]
          : prev
    );
  };

  const handleCompare = async () => {
    if (selected.length < 2) {
      toast.error("Select at least 2 documents");
      return;
    }
    setIsComparing(true);
    setResult(null);
    try {
      const res = await apiFetch("/api/comparisons/compare", {
        method: "POST",
        body: JSON.stringify({ document_ids: selected }),
      });
      if (res.ok) {
        const data = await res.json();
        setResult(data);
        toast.success("Comparison complete");
      } else {
        toast.error("Comparison failed");
      }
    } catch {
      toast.error("Comparison failed");
    } finally {
      setIsComparing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Compare Documents
        </h1>
        <p className="text-muted-foreground">
          Select 2-5 documents to compare for similarities and differences.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Select Documents</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">Loading documents...</p>
          ) : documents.length === 0 ? (
            <p className="text-muted-foreground">
              No documents available. Upload some first.
            </p>
          ) : (
            <div className="space-y-2">
              {documents.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => toggleSelect(doc.id)}
                  className={`flex items-center gap-3 w-full rounded-lg border p-3 text-left transition-colors ${
                    selected.includes(doc.id)
                      ? "border-primary bg-primary/5"
                      : "hover:bg-muted"
                  }`}
                >
                  <div
                    className={`h-4 w-4 rounded border flex items-center justify-center ${
                      selected.includes(doc.id)
                        ? "bg-primary border-primary text-primary-foreground"
                        : "border-muted-foreground"
                    }`}
                  >
                    {selected.includes(doc.id) && (
                      <span className="text-xs">✓</span>
                    )}
                  </div>
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm flex-1 truncate">
                    {doc.filename}
                  </span>
                  <Badge variant="secondary" className="text-xs">
                    {doc.chunk_count} chunks
                  </Badge>
                </button>
              ))}
            </div>
          )}

          <Button
            onClick={handleCompare}
            disabled={selected.length < 2 || isComparing}
            className="mt-4 w-full"
          >
            {isComparing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Comparing...
              </>
            ) : (
              <>
                <GitCompareArrows className="h-4 w-4 mr-2" />
                Compare {selected.length} Documents
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {result && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg text-green-600 dark:text-green-400">
                Similarities
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {result.similarities.map((s, i) => (
                  <li key={i} className="text-sm">
                    <MarkdownRenderer content={s} />
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg text-red-600 dark:text-red-400">
                Differences
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {result.differences.map((d, i) => (
                  <li key={i} className="text-sm">
                    <MarkdownRenderer content={d} />
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg text-blue-600 dark:text-blue-400">
                Insights
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {result.insights.map((ins, i) => (
                  <li key={i} className="text-sm">
                    <MarkdownRenderer content={ins} />
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
