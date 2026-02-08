# Domain Pitfalls: Next.js Production Frontend

**Domain:** Production frontend for RAG document Q&A system
**Researched:** 2026-02-08

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: EventSource Cannot POST

**What goes wrong:** Using the browser's native `EventSource` API to connect to the backend's `/api/v1/queries/stream` endpoint, which requires POST with a JSON body.
**Why it happens:** EventSource is the "standard" SSE API, and many tutorials show it for SSE. But it only supports GET requests with no request body.
**Consequences:** Streaming chat completely fails. EventSource constructor silently retries the GET request in a loop, never sending the query payload.
**Prevention:** Use `fetch()` with `ReadableStream` + `eventsource-parser` library. Never use `new EventSource()` for POST-based SSE.
**Detection:** Chat input submits but no response appears. Network tab shows repeated GET requests to the SSE endpoint.

### Pitfall 2: JWT Tokens in Client-Side JavaScript

**What goes wrong:** Storing access/refresh tokens in localStorage, sessionStorage, or React state, making them accessible to JavaScript.
**Why it happens:** Many JWT tutorials show `localStorage.setItem('token', ...)`. It's the simplest approach.
**Consequences:** Any XSS vulnerability (including from third-party scripts or markdown rendering) can steal the token. Token theft = full account compromise.
**Prevention:** Store JWT in httpOnly cookies via Next.js API route proxy. The browser sends cookies automatically but JavaScript cannot read httpOnly cookies.
**Detection:** Open browser DevTools > Application > Storage. If you see JWT tokens, they're exposed.

### Pitfall 3: Zod v4 + @hookform/resolvers Incompatibility

**What goes wrong:** Installing `zod@latest` (which resolves to v4.3.x) and finding that form validation breaks with cryptic type errors or `ZodError` thrown instead of being captured by the resolver.
**Why it happens:** Zod v4 changed its type signatures. Earlier versions of @hookform/resolvers (< 5.0.1) don't handle the new types. Even with v5.2+, there are documented edge cases.
**Consequences:** Forms throw unhandled errors instead of displaying validation messages. Build may compile but runtime behavior breaks.
**Prevention:** Pin to `zod@3` explicitly: `npm install zod@3`. Zod 3.24+ is battle-tested with the resolvers ecosystem.
**Detection:** Type errors mentioning `Resolver<output<T>>` vs `Resolver<input<T>>`. Runtime `ZodError` not caught by zodResolver.

### Pitfall 4: "use client" Everywhere Destroys SSR Benefits

**What goes wrong:** Adding `"use client"` to every component because it's "easier" or to avoid thinking about the server/client boundary.
**Why it happens:** Server Component restrictions (no hooks, no event handlers, no browser APIs) feel limiting. Adding `"use client"` removes all restrictions.
**Consequences:** Entire app becomes client-rendered. Loses SSR benefits: larger JavaScript bundle, no server-side data fetching, slower initial page load, worse SEO (if applicable), no streaming SSR.
**Prevention:** Default to server components. Only add `"use client"` to the specific leaf components that need interactivity. Extract interactive parts into small client components, keep data-fetching wrappers as server components.
**Detection:** Check bundle analyzer. If the entire app is in the client bundle, too many components are client components.

## Moderate Pitfalls

### Pitfall 5: SSE Memory Leaks from Unclosed Streams

**What goes wrong:** User navigates away from chat page while SSE stream is active. The fetch ReadableStream continues consuming data in the background.
**Prevention:** Use AbortController with fetch. Cancel the controller in a React useEffect cleanup function. Always call `reader.cancel()` on unmount.

```typescript
useEffect(() => {
  const controller = new AbortController();
  startStream({ signal: controller.signal });
  return () => controller.abort();
}, []);
```

### Pitfall 6: Dark Mode Flash on Page Load

**What goes wrong:** Page briefly renders in light mode before switching to dark mode, creating a visible flash (FOUC -- Flash of Unstyled Content).
**Prevention:** next-themes handles this with a script injected into `<head>` that sets the theme class before React hydrates. Ensure ThemeProvider is in the root layout with `attribute="class"` and `enableSystem`. Do NOT conditionally render ThemeProvider.

### Pitfall 7: File Upload Without Client-Side Validation

**What goes wrong:** Users upload a 200MB file or a .exe file, and the request fails after waiting minutes for the upload to complete.
**Prevention:** Validate file type (PDF, DOCX only) and size (< 50MB, matching backend's `MAX_UPLOAD_SIZE_MB`) before initiating the upload. Show clear error messages. Use the shadcn/ui form validation pattern.

### Pitfall 8: Tailwind v4 Config File Confusion

**What goes wrong:** Creating a `tailwind.config.js` or `tailwind.config.ts` file alongside Tailwind v4's CSS-first configuration. Both systems try to configure Tailwind simultaneously.
**Prevention:** Tailwind v4 uses ONLY CSS configuration via `@import 'tailwindcss'` and `@theme {}` blocks in `globals.css`. Do NOT create a `tailwind.config.*` file. If you see old tutorial code referencing `tailwind.config`, it's for Tailwind v3.

### Pitfall 9: Middleware vs Proxy Confusion (Next.js 15 vs 16)

**What goes wrong:** Reading Next.js 16 documentation while building on Next.js 15. In Next.js 16, `middleware.ts` is renamed to `proxy.ts`. Using the wrong filename on the wrong version causes silent failures (the file is never executed).
**Prevention:** On Next.js 15, use `middleware.ts`. On Next.js 16, use `proxy.ts`. Check which Next.js version is installed before writing middleware/proxy logic.

### Pitfall 10: Token Refresh Race Condition

**What goes wrong:** Multiple simultaneous API calls detect an expired token and all try to refresh simultaneously, causing the refresh token to be used multiple times (backend may invalidate it after first use).
**Prevention:** Implement a token refresh mutex in the API client. When the first request detects 401, lock the refresh, complete it, then retry all queued requests with the new token.

## Minor Pitfalls

### Pitfall 11: Missing `cache: 'no-store'` on User-Specific Fetches

**What goes wrong:** Next.js caches server component fetch() calls by default. User A's document list gets cached and served to User B.
**Prevention:** Always add `cache: 'no-store'` to fetch calls that return user-specific data. Or use `cookies()` in the server component (accessing cookies automatically opts out of caching).

### Pitfall 12: react-markdown XSS from Unsanitized HTML

**What goes wrong:** If AI responses contain HTML, react-markdown could render script tags or malicious HTML.
**Prevention:** react-markdown sanitizes by default (no `dangerouslySetInnerHTML`). Do NOT pass `rehype-raw` plugin unless you explicitly need HTML rendering. Keep the default safe behavior.

### Pitfall 13: Sonner Toast z-index Conflicts

**What goes wrong:** Toast notifications appear behind modals or dialogs.
**Prevention:** Place `<Toaster />` at the root layout level, after all other providers. sonner uses z-50 by default; shadcn/ui Dialog uses z-50 too. If conflicts occur, add a custom className with higher z-index to Toaster.

### Pitfall 14: motion Bundle Size

**What goes wrong:** Importing everything from `motion` adds ~30KB to the client bundle.
**Prevention:** Import specific features: `import { motion, AnimatePresence } from 'motion/react'`. Avoid importing the entire library. Use CSS transitions for simple hover/focus states instead of motion.

### Pitfall 15: Backend OAuth2PasswordRequestForm Expects Form Data

**What goes wrong:** Sending JSON to `/api/v1/auth/login` when the backend expects `application/x-www-form-urlencoded` (OAuth2PasswordRequestForm format).
**Prevention:** Use `URLSearchParams` in the API route proxy when forwarding login requests to FastAPI. The body should be `username=email&password=pass`, not `{"email": "...", "password": "..."}`.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Project Scaffold | Tailwind v4 config confusion (Pitfall 8) | No tailwind.config file. CSS-first only. |
| Auth Implementation | JWT in client state (Pitfall 2), OAuth2 form data (Pitfall 15) | httpOnly cookies, URLSearchParams for login |
| SSE Streaming | EventSource for POST (Pitfall 1), memory leaks (Pitfall 5) | fetch + eventsource-parser, AbortController cleanup |
| Dark Mode | Flash on load (Pitfall 6) | next-themes in root layout with suppressHydrationWarning |
| Document Upload | No client validation (Pitfall 7) | Validate type + size before upload |
| Form Validation | Zod v4 incompatibility (Pitfall 3) | Pin zod@3 |
| Data Fetching | Cached user data (Pitfall 11) | cache: 'no-store' or cookies() access |
| Token Management | Refresh race condition (Pitfall 10) | Refresh mutex in API client |

## Sources

- [Zod v4 hookform/resolvers issue #4992](https://github.com/colinhacks/zod/issues/4992) -- Confirmed incompatibility
- [Zod v4 hookform/resolvers issue #799](https://github.com/react-hook-form/resolvers/issues/799) -- Resolution details
- [Next.js SSE Discussion #48427](https://github.com/vercel/next.js/discussions/48427) -- SSE patterns, memory leak reports
- [Next.js 16 Middleware to Proxy](https://nextjs.org/docs/messages/middleware-to-proxy) -- Rename documentation
- [next-themes GitHub](https://github.com/pacocoursey/next-themes) -- Flash prevention mechanism
- [react-markdown Security](https://github.com/remarkjs/react-markdown#security) -- Default sanitization behavior
- Backend auth format verified in `/backend/app/api/auth.py` (OAuth2PasswordRequestForm)
- Backend upload limit verified in `/backend/app/config.py` (MAX_UPLOAD_SIZE_MB = 50)
