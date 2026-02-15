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
import { ArrowLeft, FileText, Loader2, MessageSquare } from "lucide-react";
import Link from "next/link";

const SUMMARY_FORMATS = ["brief", "detailed", "executive", "bullet"] as const;

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
  const abortControllerRef = useRef<AbortController | null>(null);

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
        let dataLineCount = 0; // Track consecutive data lines for newline handling

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            const trimmedLine = line.replace(/\r$/, "");

            // Empty line = end of SSE event block
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
                setSummaryProgress(""); // Clear progress once tokens start
                // Per SSE spec, join multiple data lines with newlines
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

        // Stream ended without explicit done event
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

      <Card>
        <CardHeader>
          <CardTitle>Summaries</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="brief" onValueChange={loadSummary}>
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
                  <div className="prose prose-sm dark:prose-invert max-w-none py-4 whitespace-pre-wrap">
                    {summaries[format]}
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
