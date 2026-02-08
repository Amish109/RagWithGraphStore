"use client";

import { useState, useEffect, use } from "react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import type { Document } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, FileText } from "lucide-react";
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
  const [isLoading, setIsLoading] = useState(true);

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

  const loadSummary = async (format: string) => {
    if (summaries[format]) return;
    setLoadingSummary(format);
    try {
      const res = await apiFetch(
        `/api/v1/query/documents/${id}/summary?format=${format}`
      );
      if (res.ok) {
        const data = await res.json();
        setSummaries((prev) => ({ ...prev, [format]: data.summary }));
      } else {
        toast.error("Failed to load summary");
      }
    } catch {
      toast.error("Failed to load summary");
    } finally {
      setLoadingSummary(null);
    }
  };

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
                  <div className="space-y-2 py-4">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-4 w-1/2" />
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
