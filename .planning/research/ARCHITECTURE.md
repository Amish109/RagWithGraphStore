# Architecture Patterns: Next.js Production Frontend

**Domain:** Production frontend for RAG document Q&A system
**Researched:** 2026-02-08

## Recommended Architecture

### High-Level Overview

```
                    +-----------------------+
                    |   Browser (React 19)  |
                    |                       |
                    | Server Components     |  -- SSR data fetching
                    | Client Components     |  -- Interactive UI (chat, forms)
                    | zustand stores        |  -- Client state (auth, chat, UI)
                    +----------+------------+
                               |
              +----------------+----------------+
              |                                 |
    +---------v----------+           +----------v---------+
    | Next.js API Routes |           | Direct Browser     |
    | (Auth Proxy)       |           | Requests           |
    |                    |           |                    |
    | POST /api/auth/*   |           | POST /queries/*    |
    | Set httpOnly cookie|           | SSE streaming      |
    | Forward to FastAPI |           | File uploads       |
    +---------+----------+           +----------+---------+
              |                                 |
              +----------------+----------------+
                               |
                    +----------v-----------+
                    |  FastAPI Backend      |
                    |  localhost:8000       |
                    |                      |
                    |  JWT Auth            |
                    |  Document Processing |
                    |  RAG Q&A             |
                    |  Memory Management   |
                    +----------------------+
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| Root Layout (`layout.tsx`) | ThemeProvider, Toaster, global providers | All pages |
| Auth Layout (`(auth)/layout.tsx`) | Unauthenticated pages only (login, register) | Auth API routes |
| Dashboard Layout (`(dashboard)/layout.tsx`) | Sidebar, header, auth guard | All dashboard pages |
| Auth API Routes (`/api/auth/*`) | JWT proxy, httpOnly cookie management | FastAPI auth endpoints |
| Auth Store (zustand) | Auth state (isAuthenticated, user, role) | Auth API routes, middleware |
| Chat Store (zustand) | Messages, streaming state, active document | SSE stream, Chat UI |
| SSE Client (`lib/sse.ts`) | Parse POST-based SSE streams | FastAPI streaming endpoint |
| API Client (`lib/api.ts`) | Authenticated fetch wrapper | FastAPI endpoints, Auth Store |

### Data Flow

**Authentication Flow:**
```
1. User submits login form
2. Client component calls Next.js API route: POST /api/auth/login
3. API route forwards to FastAPI: POST /api/v1/auth/login
4. FastAPI returns { access_token, refresh_token }
5. API route sets httpOnly cookies (access_token, refresh_token)
6. API route returns { user } to client (no tokens exposed)
7. zustand auth store updates: isAuthenticated = true
8. Client redirects to dashboard
```

**Chat Streaming Flow:**
```
1. User types question in chat input
2. Client component dispatches to chat store
3. Chat store calls SSE client with fetch()
4. fetch() sends POST to FastAPI /api/v1/queries/stream
   - Authorization header from httpOnly cookie (read by middleware)
   - Body: { question, document_ids, session_id }
5. ReadableStream pipes through eventsource-parser
6. Each SSE event updates chat store message
7. react-markdown re-renders incrementally
8. Final event includes citations
9. Chat store marks message as complete
```

**Document Upload Flow:**
```
1. User drops file on upload zone
2. Client validates: file type (PDF/DOCX), size (< 50MB)
3. FormData created with file
4. fetch() POST to /api/v1/documents/upload with auth header
5. Backend returns { document_id, status: "processing" }
6. Frontend polls /api/v1/documents/{id}/status every 2 seconds
7. Status transitions: processing -> completed / failed
8. Document list refreshes on completion
```

## Patterns to Follow

### Pattern 1: Server Components for Data Fetching

**What:** Use React Server Components (default in App Router) for initial data loading. Only add `"use client"` when you need interactivity.

**When:** Document list page, memory list, admin views -- any page that loads data on render.

**Example:**
```typescript
// src/app/(dashboard)/documents/page.tsx
// This is a Server Component (no "use client" directive)

import { cookies } from 'next/headers';
import { DocumentList } from '@/components/documents/document-list';

export default async function DocumentsPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get('access_token')?.value;

  const res = await fetch(`${process.env.API_URL}/documents`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store', // Always fresh for user-specific data
  });

  const documents = await res.json();

  return <DocumentList initialDocuments={documents} />;
}
```

### Pattern 2: Client Components for Interactivity

**What:** Add `"use client"` only for components that use hooks, event handlers, or browser APIs.

**When:** Chat interface, form inputs, theme toggle, file upload dropzone.

**Example:**
```typescript
// src/components/chat/chat-input.tsx
"use client";

import { useState, useRef } from 'react';
import { useChatStore } from '@/stores/chat-store';

export function ChatInput() {
  const [input, setInput] = useState('');
  const sendMessage = useChatStore((s) => s.sendMessage);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      sendMessage(input);
      setInput('');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* ... */}
    </form>
  );
}
```

### Pattern 3: Zustand Store with No Provider

**What:** Create zustand stores as standalone modules. No React Context provider needed.

**When:** Auth state, chat state, UI state (sidebar open/closed).

**Example:**
```typescript
// src/stores/auth-store.ts
import { create } from 'zustand';

interface AuthState {
  isAuthenticated: boolean;
  user: { id: string; email: string; role: string } | null;
  setUser: (user: AuthState['user']) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  user: null,
  setUser: (user) => set({ isAuthenticated: !!user, user }),
  logout: () => set({ isAuthenticated: false, user: null }),
}));
```

### Pattern 4: API Route Proxy for httpOnly Cookies

**What:** Next.js API routes act as a translation layer between browser and FastAPI, managing JWT tokens in httpOnly cookies.

**When:** Login, logout, token refresh. NOT for data fetching (server components handle that).

**Example:**
```typescript
// src/app/api/auth/login/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const body = await request.json();

  const res = await fetch(`${process.env.API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      username: body.email,
      password: body.password,
    }),
  });

  if (!res.ok) {
    const error = await res.json();
    return NextResponse.json(error, { status: res.status });
  }

  const data = await res.json();

  const response = NextResponse.json({
    user: { /* extract user info */ }
  });

  response.cookies.set('access_token', data.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 30, // 30 minutes (matches backend)
    path: '/',
  });

  response.cookies.set('refresh_token', data.refresh_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 7, // 7 days (matches backend)
    path: '/api/auth/refresh',
  });

  return response;
}
```

### Pattern 5: SSE Stream Consumption with fetch

**What:** Use native fetch with ReadableStream + eventsource-parser for POST-based SSE.

**When:** Chat Q&A streaming from `/queries/stream`.

**Example:**
```typescript
// src/lib/sse.ts
import { createParser, type EventSourceMessage } from 'eventsource-parser';

export async function streamSSE(
  url: string,
  body: object,
  token: string,
  onEvent: (event: EventSourceMessage) => void,
  onError: (error: Error) => void,
) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok || !response.body) {
    throw new Error(`SSE error: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  const parser = createParser({
    onEvent,
  });

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      parser.feed(decoder.decode(value, { stream: true }));
    }
  } catch (error) {
    onError(error as Error);
  }
}
```

### Pattern 6: Route Groups for Layout Separation

**What:** Use Next.js route groups `(auth)` and `(dashboard)` to separate authenticated and unauthenticated layouts.

**When:** Always. Auth pages need minimal layout. Dashboard pages need sidebar + header.

**Example:**
```
src/app/
  (auth)/          # No sidebar, centered layout
    layout.tsx     # Minimal: logo + centered card
    login/
    register/
  (dashboard)/     # Full layout with sidebar
    layout.tsx     # Sidebar + header + auth guard
    documents/
    chat/
    admin/
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Using EventSource for POST Requests

**What:** Attempting to use the browser's native `EventSource` API to connect to POST-based SSE endpoints.
**Why bad:** EventSource only supports GET requests. It will fail silently or throw errors when pointed at a POST endpoint.
**Instead:** Use `fetch()` with `ReadableStream` and `eventsource-parser`.

### Anti-Pattern 2: Storing JWT in localStorage/sessionStorage

**What:** Saving access tokens in browser storage accessible to JavaScript.
**Why bad:** Any XSS vulnerability exposes the token. localStorage persists across tabs and sessions.
**Instead:** httpOnly cookies set by Next.js API routes. JavaScript cannot read httpOnly cookies.

### Anti-Pattern 3: Making All Components Client Components

**What:** Adding `"use client"` to every component "just in case."
**Why bad:** Loses the benefits of server components (smaller JS bundle, server-side data fetching, streaming SSR). Forces all data fetching through client-side effects.
**Instead:** Default to server components. Only add `"use client"` when you need hooks, event handlers, or browser APIs.

### Anti-Pattern 4: Using @tanstack/react-query with Server Components

**What:** Adding React Query alongside Next.js App Router's built-in fetch.
**Why bad:** Redundant. Next.js Server Components already handle data fetching, caching, and revalidation. Adding React Query creates two competing caching layers.
**Instead:** Server components + fetch for data loading. zustand for client-side state only.

### Anti-Pattern 5: Proxying SSE Through Next.js API Routes

**What:** Creating a Next.js API route that connects to FastAPI's SSE endpoint and re-streams to the browser.
**Why bad:** Adds latency, consumes server memory for the duration of the stream, and can cause timeout issues. Long-lived connections tie up Next.js serverless function slots.
**Instead:** Browser connects directly to FastAPI's SSE endpoint with Authorization header.

### Anti-Pattern 6: Global CSS with Tailwind v4

**What:** Writing traditional CSS alongside Tailwind utilities.
**Why bad:** Tailwind v4 handles all styling via utilities and CSS variables. Mixing approaches creates conflicts and makes dark mode inconsistent.
**Instead:** Use Tailwind utilities exclusively. Custom values go in `@theme {}` blocks in globals.css.

## Scalability Considerations

| Concern | MVP (< 100 users) | Growth (< 10K users) | Scale (< 1M users) |
|---------|-------------------|---------------------|---------------------|
| Rendering | All SSR + CSR on single Next.js instance | Same -- Next.js handles this well | Deploy to Vercel or containerize with multiple replicas |
| Auth | Single httpOnly cookie, 30-min expiry | Same pattern works | Consider session store if cookie size grows |
| SSE Streaming | Direct browser-to-FastAPI | Same -- SSE is lightweight | Backend needs horizontal scaling, not frontend |
| Static Assets | Default Next.js public/ | CDN (Vercel auto-handles) | CDN with edge caching |
| Bundle Size | Tree-shaking via Next.js + Turbopack | Same | Code splitting per route (automatic with App Router) |
| State | zustand in-memory | Same | Same -- client state doesn't scale with users |

## Sources

- [Next.js App Router Architecture](https://nextjs.org/docs/app) -- Server/Client component model
- [Next.js Route Handlers](https://nextjs.org/docs/app/building-your-application/routing/route-handlers) -- API route patterns
- [Next.js Middleware](https://nextjs.org/docs/app/building-your-application/routing/middleware) -- Auth guard patterns
- [zustand Documentation](https://zustand.docs.pmnd.rs/) -- Store patterns
- [shadcn/ui Forms](https://ui.shadcn.com/docs/forms/react-hook-form) -- Form component patterns
- [eventsource-parser GitHub](https://github.com/rexxars/eventsource-parser) -- SSE parsing API
- Backend CORS config verified in `/backend/app/main.py` lines 84-90
- Backend auth endpoints verified in `/backend/app/api/auth.py`
- Backend streaming endpoint verified in `/backend/app/api/queries.py` line 115
