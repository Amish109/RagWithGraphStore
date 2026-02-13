export interface User {
  id: string;
  email: string;
  role: "user" | "admin";
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Document {
  id: string;
  filename: string;
  file_type?: string;
  file_size?: number;
  chunk_count?: number;
  status?: "processing" | "ready" | "error";
  created_at?: string;
  summary?: string;
}

export interface DocumentStatus {
  id: string;
  status: "processing" | "ready" | "error";
  stage?: string;
  progress?: number;
  error?: string;
}

export interface Citation {
  document_name: string;
  chunk_id: string;
  text: string;
  score: number;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  confidence: number;
  confidence_level: "high" | "medium" | "low";
}

export interface SSEEvent {
  event: string;
  data: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  confidence?: number;
  confidence_level?: "high" | "medium" | "low";
  timestamp: Date;
}

export interface ComparisonResult {
  similarities: string[];
  differences: string[];
  insights: string[];
  citations: Citation[];
}

export interface MemoryEntry {
  id: string;
  memory: string;
  created_at: string;
  user_id: string;
}

export interface Summary {
  summary: string;
  format: "brief" | "detailed" | "executive" | "bullet";
}

export interface MigrationResult {
  documents_migrated: number;
  memories_migrated: number;
  success: boolean;
}
