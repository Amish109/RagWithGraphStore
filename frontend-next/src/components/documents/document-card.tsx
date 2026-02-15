"use client";

import type { Document } from "@/lib/types";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileText, Trash2, MessageSquare } from "lucide-react";
import Link from "next/link";

interface DocumentCardProps {
  document: Document;
  onDelete: () => void;
}

export function DocumentCard({ document, onDelete }: DocumentCardProps) {
  const status = document.status || "ready";
  const statusColor =
    status === "ready"
      ? "default"
      : status === "processing"
        ? "secondary"
        : "destructive";

  return (
    <Card className="hover:bg-accent/30 transition-colors">
      <CardHeader className="flex flex-row items-start justify-between pb-2">
        <Link
          href={`/documents/${document.id}`}
          className="flex items-center gap-2 flex-1 min-w-0"
        >
          <FileText className="h-4 w-4 text-primary shrink-0" />
          <CardTitle className="text-sm truncate">
            {document.filename}
          </CardTitle>
        </Link>
        <Badge variant={statusColor} className="shrink-0 ml-2">
          {status}
        </Badge>
      </CardHeader>
      <CardContent className="flex items-center justify-between">
        <div className="text-xs text-muted-foreground space-y-1">
          {document.file_type && <p>{document.file_type.toUpperCase()}</p>}
          {document.created_at && <p>{new Date(document.created_at).toLocaleDateString()}</p>}
          {document.chunk_count != null && document.chunk_count > 0 && <p>{document.chunk_count} chunks</p>}
        </div>
        <div className="flex items-center gap-1">
          <Link
            href={`/documents/${document.id}/chat`}
            onClick={(e) => e.stopPropagation()}
          >
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-muted-foreground hover:text-primary"
            >
              <MessageSquare className="h-4 w-4" />
            </Button>
          </Link>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-destructive"
            onClick={(e) => {
              e.preventDefault();
              onDelete();
            }}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
