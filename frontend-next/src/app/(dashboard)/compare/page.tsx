"use client";

import { useState, useEffect, useRef } from "react";
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
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [isComparing, setIsComparing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isComparing) {
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [isComparing]);

  useEffect(() => {
    async function fetchDocs() {
      try {
        const res = await apiFetch("/api/v1/documents/");
        if (res.ok) {
          const data = await res.json();
          setDocuments(
            (data.documents || data).filter(
              (d: Document) => !d.status || d.status === "ready"
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
    if (query.trim().length < 10) {
      toast.error("Query must be at least 10 characters");
      return;
    }
    setIsComparing(true);
    setResult(null);
    try {
      const res = await apiFetch("/api/v1/compare/", {
        method: "POST",
        body: JSON.stringify({ document_ids: selected, query: query.trim() }),
      });
      if (res.ok) {
        const data = await res.json();
        setResult({
          similarities: data.similarities || [],
          differences: data.differences || [],
          insights: data.cross_document_insights || data.insights || [],
          citations: data.citations || [],
        });
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

          <div className="mt-4">
            <label htmlFor="compare-query" className="text-sm font-medium mb-1.5 block">
              What would you like to compare?
            </label>
            <input
              id="compare-query"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Compare the database architectures and highlight key differences"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>

          <Button
            onClick={handleCompare}
            disabled={selected.length < 2 || query.trim().length < 10 || isComparing}
            className="mt-3 w-full"
          >
            {isComparing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Comparing... {elapsed > 0 && `(${elapsed}s)`}
              </>
            ) : (
              <>
                <GitCompareArrows className="h-4 w-4 mr-2" />
                Compare {selected.length} Documents
              </>
            )}
          </Button>
          {isComparing && (
            <p className="mt-2 text-xs text-muted-foreground text-center">
              Analysis may take 1-2 minutes depending on document size.
            </p>
          )}
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
