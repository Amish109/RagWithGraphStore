"use client";

import type { Citation } from "@/lib/types";
import { FileText } from "lucide-react";

interface CitationListProps {
  citations: Citation[];
}

export function CitationList({ citations }: CitationListProps) {
  if (!citations.length) return null;

  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground">Sources:</p>
      <div className="flex flex-wrap gap-1">
        {citations.map((citation, index) => (
          <div
            key={`${citation.document_name}-${index}`}
            className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1 text-xs"
            title={citation.text}
          >
            <FileText className="h-3 w-3" />
            <span className="truncate max-w-[150px]">
              {citation.document_name}
            </span>
            <span className="text-muted-foreground">
              ({Math.round(citation.score * 100)}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
