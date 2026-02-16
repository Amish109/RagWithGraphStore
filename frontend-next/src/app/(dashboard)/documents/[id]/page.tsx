"use client";

import { useState, useEffect, useRef, useCallback, use } from "react";
import { toast } from "sonner";
import { apiFetch, API_URL } from "@/lib/api";
import type { Document } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, Download, FileText, Loader2, MessageSquare, RefreshCw, Network } from "lucide-react";
import Link from "next/link";

const SUMMARY_FORMATS = ["brief", "detailed", "executive", "bullet"] as const;

interface EntityStatus {
  status: string;
  progress: number;
  message: string;
  total_chunks?: number;
  completed_chunks?: number;
  total_entities?: number;
}

export default function DocumentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [document, setDocument] = useState<Document | null>(null);
  const [summaries, setSummaries] = useState<Record<string, string>>({});
  const [loadingSummary, setLoadingSummary] = useState<string | null>(null);
  const [streamingText, setStreamingText] = useState<string>("");
  const [summaryStage, setSummaryStage] = useState<string>("");
  const [summaryProgress, setSummaryProgress] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [entityStatus, setEntityStatus] = useState<EntityStatus | null>(null);
  const [regenerating, setRegenerating] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [activeTab, setActiveTab] = useState<string>("brief");

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    async function fetchDoc() {
      try {
        const res = await apiFetch(`/api/v1/documents/`);
        if (res.ok) {
          const data = await res.json();
          const docs: Document[] = data.documents || data;
          const doc = docs.find((d: Document) => d.id === id);
          if (doc) setDocument(doc);
        }
      } catch {
        toast.error("Failed to load document");
      } finally {
        setIsLoading(false);
      }
    }
    fetchDoc();
  }, [id]);

  // Poll entity extraction status
  useEffect(() => {
    if (!document) return;

    let cancelled = false;

    async function pollEntityStatus() {
      try {
        const res = await apiFetch(`/api/v1/documents/${id}/entity-status`);
        if (res.ok && !cancelled) {
          const data = await res.json();
          setEntityStatus(data);
          return data.status;
        }
      } catch {
        // ignore
      }
      return null;
    }

    // Initial fetch
    pollEntityStatus().then((status) => {
      if (status === "extracting" || status === "not_started") {
        // Start polling
        const interval = setInterval(async () => {
          const s = await pollEntityStatus();
          if (cancelled || (s !== "extracting" && s !== "not_started")) {
            clearInterval(interval);
          }
        }, 3000);
        return () => {
          cancelled = true;
          clearInterval(interval);
        };
      }
    });

    return () => {
      cancelled = true;
    };
  }, [document, id]);

  const loadSummary = useCallback(
    async (format: string) => {
      if (summaries[format]) return;

      // Abort any previous stream
      abortControllerRef.current?.abort();
      const controller = new AbortController();
      abortControllerRef.current = controller;

      setLoadingSummary(format);
      setStreamingText("");
      setSummaryStage("");
      setSummaryProgress("");

      try {
        const res = await fetch(
          `${API_URL}/api/v1/query/documents/${id}/summary/stream?format=${format}`,
          {
            credentials: "include",
            headers: { Accept: "text/event-stream" },
            signal: controller.signal,
          }
        );

        if (!res.ok || !res.body) {
          toast.error("Failed to load summary");
          setLoadingSummary(null);
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let accumulated = "";
        let buffer = "";
        let currentEvent = "";
        let dataLineCount = 0;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            const trimmedLine = line.replace(/\r$/, "");

            if (trimmedLine === "") {
              dataLineCount = 0;
              continue;
            }

            if (trimmedLine.startsWith("event: ")) {
              currentEvent = trimmedLine.slice(7).trim();
              dataLineCount = 0;
              if (currentEvent === "done") {
                if (accumulated) {
                  setSummaries((prev) => ({ ...prev, [format]: accumulated }));
                }
                setStreamingText("");
                setLoadingSummary(null);
                setSummaryStage("");
                setSummaryProgress("");
                return;
              }
              if (currentEvent === "error") {
                toast.error("Failed to generate summary");
                setStreamingText("");
                setLoadingSummary(null);
                setSummaryStage("");
                setSummaryProgress("");
                return;
              }
            }
            if (trimmedLine.startsWith("data: ") || trimmedLine === "data:") {
              const data = trimmedLine.startsWith("data: ")
                ? trimmedLine.slice(6)
                : "";
              if (currentEvent === "status") {
                setSummaryStage("generating");
              } else if (currentEvent === "progress") {
                try {
                  const progress = JSON.parse(data);
                  setSummaryProgress(
                    `Analyzing section ${progress.current}/${progress.total}`
                  );
                } catch {
                  // ignore parse errors
                }
              } else if (currentEvent === "token") {
                setSummaryProgress("");
                if (dataLineCount > 0) {
                  accumulated += "\n";
                }
                accumulated += data;
                setStreamingText(accumulated);
              }
              dataLineCount++;
            }
          }
        }

        if (accumulated) {
          setSummaries((prev) => ({ ...prev, [format]: accumulated }));
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        toast.error("Failed to load summary");
      } finally {
        setStreamingText("");
        setLoadingSummary(null);
      }
    },
    [id, summaries]
  );

  const handleRegenerate = async (format: string) => {
    setRegenerating(format);
    try {
      const res = await apiFetch(
        `/api/v1/query/documents/${id}/summary/regenerate?format=${format}`,
        { method: "POST" }
      );
      if (res.ok) {
        // Clear local cached summary so loadSummary will re-fetch
        setSummaries((prev) => {
          const next = { ...prev };
          delete next[format];
          return next;
        });
        // Trigger re-stream
        loadSummary(format);
      } else {
        toast.error("Failed to regenerate summary");
      }
    } catch {
      toast.error("Failed to regenerate summary");
    } finally {
      setRegenerating(null);
    }
  };

  const downloadSummaryPdf = useCallback(
    async (format: "current" | "all" = "current") => {
      const { jsPDF } = await import("jspdf");
      const doc = new jsPDF({ unit: "mm", format: "a4" });
      const pageWidth = doc.internal.pageSize.getWidth();
      const margin = 20;
      const maxWidth = pageWidth - margin * 2;
      let y = margin;

      const addText = (text: string, size: number, bold: boolean = false) => {
        doc.setFontSize(size);
        doc.setFont("helvetica", bold ? "bold" : "normal");
        const lines = doc.splitTextToSize(text, maxWidth);
        for (const line of lines) {
          if (y + size * 0.4 > doc.internal.pageSize.getHeight() - margin) {
            doc.addPage();
            y = margin;
          }
          doc.text(line, margin, y);
          y += size * 0.45;
        }
      };

      // Title
      addText(document!.filename, 18, true);
      y += 4;
      addText(`Generated on ${new Date().toLocaleDateString()}`, 9);
      y += 8;

      const formatsToExport =
        format === "all"
          ? SUMMARY_FORMATS.filter((f) => summaries[f])
          : [activeTab];

      for (const fmt of formatsToExport) {
        const text = summaries[fmt];
        if (!text) continue;

        if (format === "all" && fmt !== formatsToExport[0]) {
          y += 6;
        }
        addText(`${fmt.charAt(0).toUpperCase() + fmt.slice(1)} Summary`, 14, true);
        y += 3;

        // Draw separator line
        doc.setDrawColor(200);
        doc.line(margin, y, pageWidth - margin, y);
        y += 5;

        addText(text, 10);
        y += 4;
      }

      const suffix = format === "all" ? "all-summaries" : `${activeTab}-summary`;
      doc.save(`${document!.filename.replace(/\.[^.]+$/, "")}-${suffix}.pdf`);
    },
    [document, summaries, activeTab]
  );

  // Auto-load brief summary when document is ready
  useEffect(() => {
    if (document && !summaries["brief"]) {
      loadSummary("brief");
    }
  }, [document, summaries, loadSummary]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (!document) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Document not found.</p>
        <Button asChild variant="link" className="mt-2">
          <Link href="/documents">Back to documents</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button asChild variant="ghost" size="icon">
          <Link href="/documents">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <FileText className="h-5 w-5 text-primary" />
          <h1 className="text-2xl font-bold tracking-tight truncate">
            {document.filename}
          </h1>
          <Badge>{document.status}</Badge>
        </div>
        <Button asChild variant="default" size="sm">
          <Link href={`/documents/${id}/chat`}>
            <MessageSquare className="h-4 w-4 mr-2" />
            Chat
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Type</p>
            <p className="font-medium">
              {document.file_type?.toUpperCase()}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground">Uploaded</p>
            <p className="font-medium">
              {new Date(document.created_at).toLocaleDateString()}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground">Chunks</p>
            <p className="font-medium">{document.chunk_count}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Size</p>
            <p className="font-medium">
              {(document.file_size / 1024 / 1024).toFixed(1)} MB
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Entity extraction status */}
      {entityStatus && entityStatus.status !== "not_started" && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Network className="h-4 w-4" />
              Knowledge Graph
            </CardTitle>
          </CardHeader>
          <CardContent>
            {entityStatus.status === "extracting" ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>{entityStatus.message}</span>
                </div>
                <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-500"
                    style={{ width: `${entityStatus.progress}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground/60">
                  {entityStatus.total_entities || 0} entities found so far
                </p>
              </div>
            ) : entityStatus.status === "completed" ? (
              <div className="flex items-center gap-2 text-sm">
                <Badge variant="secondary">
                  {entityStatus.total_entities || 0} entities
                </Badge>
                <span className="text-muted-foreground">
                  {entityStatus.message}
                </span>
              </div>
            ) : entityStatus.status === "failed" ? (
              <p className="text-sm text-destructive">
                Entity extraction failed: {entityStatus.message}
              </p>
            ) : null}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Summaries</CardTitle>
          {Object.keys(summaries).length > 1 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => downloadSummaryPdf("all")}
            >
              <Download className="h-3 w-3 mr-2" />
              Download All as PDF
            </Button>
          )}
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="brief" onValueChange={(v) => { setActiveTab(v); loadSummary(v); }}>
            <TabsList>
              {SUMMARY_FORMATS.map((format) => (
                <TabsTrigger key={format} value={format} className="capitalize">
                  {format}
                </TabsTrigger>
              ))}
            </TabsList>
            {SUMMARY_FORMATS.map((format) => (
              <TabsContent key={format} value={format}>
                {loadingSummary === format ? (
                  <div className="py-4">
                    {streamingText ? (
                      <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
                        {streamingText}
                        <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-0.5" />
                      </div>
                    ) : (
                      <div className="flex flex-col gap-2 text-muted-foreground">
                        <div className="flex items-center gap-2">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span className="text-sm">
                            {summaryProgress
                              ? summaryProgress
                              : summaryStage === "generating"
                                ? "Generating summary with LLM..."
                                : "Loading summary..."}
                          </span>
                        </div>
                        {summaryStage === "generating" && (
                          <p className="text-xs text-muted-foreground/60 ml-6">
                            Large documents are analyzed section by section. This may take a minute.
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                ) : summaries[format] ? (
                  <div className="py-4">
                    <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
                      {summaries[format]}
                    </div>
                    <div className="mt-4 pt-3 border-t flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRegenerate(format)}
                        disabled={regenerating === format}
                      >
                        {regenerating === format ? (
                          <Loader2 className="h-3 w-3 mr-2 animate-spin" />
                        ) : (
                          <RefreshCw className="h-3 w-3 mr-2" />
                        )}
                        Regenerate
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => downloadSummaryPdf("current")}
                      >
                        <Download className="h-3 w-3 mr-2" />
                        Download PDF
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Button
                      variant="outline"
                      onClick={() => loadSummary(format)}
                    >
                      Load {format} summary
                    </Button>
                  </div>
                )}
              </TabsContent>
            ))}
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
