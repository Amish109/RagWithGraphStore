# Technology Stack: Next.js Production Frontend

**Project:** RAG with Graph Store - Next.js Production Frontend
**Researched:** 2026-02-08
**Confidence:** HIGH
**Replaces:** Streamlit test frontend at `frontend/`

## Critical Version Decision: Next.js 15 vs 16

The user question asks for Next.js 15. However, **Next.js 16 is now the current stable release** (16.1.6 as of Feb 2026). Next.js 15 has entered maintenance LTS.

**Recommendation: Use Next.js 15.x (latest 15.5.x)** for this project because:

1. **The question explicitly targets Next.js 15** -- honor the explicit requirement
2. **Next.js 16 has breaking changes** that add unnecessary risk for a first frontend build:
   - `middleware.ts` renamed to `proxy.ts` (affects JWT auth proxy pattern)
   - Synchronous API access fully removed (all params/searchParams/cookies must be awaited)
   - `next lint` removed (must configure ESLint separately)
   - React Compiler is opt-in but ecosystem tutorials mostly target 15 still
3. **Next.js 15 is production-proven** with extensive community resources
4. **Migration to 16 later is straightforward** -- Vercel provides codemods

If the team prefers to start on 16 directly, the stack below remains compatible -- just swap `next@15` for `next@16` and rename `middleware.ts` to `proxy.ts`.

---

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Next.js | ^15.5.0 | React framework with App Router | Latest 15.x stable. App Router is the standard. SSR, streaming, API routes, middleware for auth proxy. CORS already configured on backend for localhost:3000. |
| React | ^19.1.0 | UI library | Next.js 15.5 ships with React 19. Stable, well-tested with Next 15. |
| React DOM | ^19.1.0 | DOM rendering | Paired with React 19. |
| TypeScript | ^5.7.0 | Type safety | Default for new Next.js projects. TS 5.9 is latest but 5.7+ is what Next.js 15 targets. |

### Styling & UI Components

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Tailwind CSS | ^4.1.0 | Utility-first CSS | v4 is stable. CSS-first config (no `tailwind.config.js`). 5x faster builds. Automatic content detection. shadcn/ui fully supports v4. |
| @tailwindcss/postcss | ^4.1.0 | PostCSS integration | Required for Next.js (not Vite). Replaces the old `tailwindcss` PostCSS plugin. |
| shadcn/ui | CLI (npx shadcn@latest) | Component library | NOT an npm dependency -- it's a CLI that copies components into your project. Uses Radix UI primitives + Tailwind. Full React 19 + Tailwind v4 compatibility confirmed. |
| radix-ui | ^1.4.0 | Accessible UI primitives | Unified package (replaces individual `@radix-ui/react-*` packages). Tree-shakeable. shadcn/ui's foundation. |
| lucide-react | ^0.563.0 | Icons | shadcn/ui's default icon library. Tree-shakeable SVG icons. |
| class-variance-authority | ^0.7.1 | Component variant management | Used by shadcn/ui for variant props (size, color, etc.). Installed by `shadcn init`. |
| clsx | ^2.1.0 | Conditional class names | Tiny utility for conditional CSS classes. Installed by `shadcn init`. |
| tailwind-merge | ^3.4.0 | Merge Tailwind classes | Prevents class conflicts when composing Tailwind. v3.x supports Tailwind v4. Installed by `shadcn init`. |

### Theming

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| next-themes | ^0.4.6 | Dark/light mode toggle | De facto standard for Next.js theming. Works with App Router + `attribute="class"`. System preference detection. No flash on load. shadcn/ui recommends it. |

### State Management

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| zustand | ^5.0.0 | Client-side state | Lightweight (1.2KB), no providers needed, works with React 19. For auth state, UI toggles, chat state. Simpler than Redux, more capable than Context for shared state. |

### Forms & Validation

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| react-hook-form | ^7.71.0 | Form state management | Minimal re-renders, uncontrolled components, excellent DX. shadcn/ui has official form components built on it. |
| zod | ^3.24.0 | Schema validation | Use Zod v3 (NOT v4). v4 has had compatibility issues with @hookform/resolvers. v3.24+ is battle-tested. Shared validation between client/server. |
| @hookform/resolvers | ^5.2.0 | Bridge RHF + Zod | Connects react-hook-form to Zod schemas. v5.2+ supports both Zod 3 and 4 but Zod 3 is safer. |

### Streaming & SSE

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Native EventSource API | Browser built-in | SSE consumption | Backend uses SSE-Starlette. EventSource is the standard browser API. No npm package needed for basic SSE. |
| eventsource-parser | ^3.0.0 | SSE parsing for fetch-based streams | For POST-based SSE (the `/queries/stream` endpoint uses POST, which EventSource doesn't support). Parse SSE from fetch ReadableStream responses. |

**Important SSE architecture note:** The browser's native `EventSource` API only supports GET requests. The backend's `/api/v1/queries/stream` uses POST. You MUST use `fetch()` with `ReadableStream` + `eventsource-parser` to consume POST-based SSE streams. Do NOT try to use the native `EventSource` constructor.

### Markdown Rendering

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| react-markdown | ^10.1.0 | Render AI responses | Renders markdown safely as React components. CommonMark compliant. Plugin-extensible (remark/rehype). |
| react-shiki | ^0.8.0 | Code syntax highlighting | Modern Shiki-based highlighter for React. Better than react-syntax-highlighter (legacy Prism/Highlight.js). Lazy-loads languages. |
| remark-gfm | ^4.0.0 | GitHub Flavored Markdown | Tables, task lists, strikethrough support in react-markdown. |

### Animation

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| motion | ^12.33.0 | Animations & transitions | Formerly "framer-motion" -- renamed to "motion". Loading skeletons, page transitions, chat message animations. 18M+ monthly downloads. Spring physics, layout animations, gesture support. |

### Toast Notifications

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| sonner | ^2.0.0 | Toast notifications | shadcn/ui's official toast component. Used by Vercel, Cursor. Opinionated, beautiful defaults. |

### URL State

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| nuqs | ^2.8.0 | Type-safe URL query params | Like useState but in URL. Useful for document filters, search queries, pagination. No external deps. Tiny bundle. |

### Linting & Formatting

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| eslint | ^9.0.0 | Code linting | Default with create-next-app. ESLint 9 with flat config format. |
| eslint-config-next | ^15.5.0 | Next.js ESLint rules | Core Web Vitals rules, React best practices. Match Next.js version. |

---

## What NOT to Install

These are packages you might be tempted to add but should NOT:

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| axios | Unnecessary -- `fetch` is built into Next.js and React 19 | Native `fetch()` with Next.js caching integration |
| @tanstack/react-query | Overkill -- Next.js App Router has built-in data fetching with server components | Server components + `fetch()` for server state; zustand for client state |
| styled-components / emotion | Conflicts with Tailwind CSS approach; poor RSC support | Tailwind CSS + shadcn/ui |
| next-auth / auth.js | Backend already handles JWT auth. Adding next-auth creates duplicate auth logic | Custom auth with API route proxy for httpOnly cookies |
| redux / @reduxjs/toolkit | Massive overkill for this app's client state needs | zustand (1.2KB vs 40KB+) |
| react-query / swr | Server components handle server-state fetching natively | Built-in Next.js fetch + server components |
| tailwindcss-animate | shadcn/ui used to require it, but Tailwind v4 has native animation support | Tailwind v4 native `animate-*` utilities + motion library |
| framer-motion | Package renamed to `motion` | `npm install motion` |
| react-syntax-highlighter | Legacy library (Prism/Highlight.js based). Large bundle. | react-shiki (modern, lazy-loading, smaller) |
| react-icons | Inconsistent sizing/quality across icon sets | lucide-react (consistent, tree-shakeable, shadcn default) |
| zod v4.x | Compatibility issues with @hookform/resolvers documented in GitHub issues | zod v3.24+ (stable, proven compatibility) |
| moment / dayjs | Only needed if you have complex date formatting requirements | Native `Intl.DateTimeFormat` or `date-fns` if truly needed |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Framework | Next.js 15 | Next.js 16 | 16 is current stable but has breaking changes (middleware->proxy rename, async-only APIs). Start on 15, migrate when ready. |
| CSS | Tailwind v4 | Tailwind v3 | v4 is stable, faster, simpler config. No reason to use v3 for new projects. |
| Components | shadcn/ui + Radix | MUI / Chakra UI / Mantine | shadcn/ui gives you the source code (no vendor lock-in), plays perfectly with Tailwind, fully accessible via Radix primitives. |
| State | zustand | Jotai / Redux Toolkit | zustand is simpler API, no providers, works without React context. Jotai is good but atom-based model is overkill here. |
| Forms | react-hook-form + zod | Formik | RHF has better performance (uncontrolled components), smaller bundle, better TypeScript support. |
| Icons | lucide-react | heroicons / react-icons | lucide-react is shadcn/ui's default, tree-shakeable, consistent quality. |
| Animation | motion | CSS transitions only | CSS handles simple cases, but chat message animations, skeleton loading, and page transitions benefit from motion's spring physics and layout animations. |
| SSE parsing | eventsource-parser | @microsoft/fetch-event-source | eventsource-parser is smaller, maintained, pure parser. fetch-event-source bundles its own fetch wrapper. |
| Markdown | react-markdown + react-shiki | @mdx-js/react | MDX is for authoring; react-markdown is for rendering dynamic AI-generated content. |

---

## Installation

### Step 1: Create Next.js App

```bash
npx create-next-app@15 frontend-next --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
cd frontend-next
```

### Step 2: Initialize shadcn/ui

```bash
npx shadcn@latest init
# Select: New York style, Zinc base color, CSS variables: yes
```

This automatically installs: `radix-ui`, `lucide-react`, `class-variance-authority`, `clsx`, `tailwind-merge`

### Step 3: Add Production Dependencies

```bash
npm install zustand next-themes sonner motion react-markdown react-shiki remark-gfm nuqs eventsource-parser
```

### Step 4: Add Form Dependencies

```bash
npm install react-hook-form zod@3 @hookform/resolvers
```

### Step 5: Add shadcn/ui Components (as needed)

```bash
# Core components for RAG app
npx shadcn@latest add button card input textarea dialog dropdown-menu \
  avatar badge separator skeleton tabs toast sheet scroll-area \
  form label select switch tooltip popover command
```

### Step 6: PostCSS Configuration

```javascript
// postcss.config.mjs
export default {
  plugins: {
    '@tailwindcss/postcss': {},
  },
}
```

### Step 7: Global CSS

```css
/* src/app/globals.css */
@import 'tailwindcss';

/* CSS variables for shadcn/ui theming are auto-generated by shadcn init */
```

---

## Package.json (Expected)

```json
{
  "dependencies": {
    "next": "^15.5.0",
    "react": "^19.1.0",
    "react-dom": "^19.1.0",
    "radix-ui": "^1.4.0",
    "lucide-react": "^0.563.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.0",
    "tailwind-merge": "^3.4.0",
    "zustand": "^5.0.0",
    "next-themes": "^0.4.6",
    "sonner": "^2.0.0",
    "motion": "^12.33.0",
    "react-markdown": "^10.1.0",
    "react-shiki": "^0.8.0",
    "remark-gfm": "^4.0.0",
    "nuqs": "^2.8.0",
    "eventsource-parser": "^3.0.0",
    "react-hook-form": "^7.71.0",
    "zod": "^3.24.0",
    "@hookform/resolvers": "^5.2.0"
  },
  "devDependencies": {
    "typescript": "^5.7.0",
    "tailwindcss": "^4.1.0",
    "@tailwindcss/postcss": "^4.1.0",
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "eslint": "^9.0.0",
    "eslint-config-next": "^15.5.0"
  }
}
```

**Total production dependencies:** 19 packages
**Total dev dependencies:** 7 packages

---

## Integration Points with FastAPI Backend

### CORS (Already Configured)

Backend at `/backend/app/main.py` line 84-90:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Already set
    allow_credentials=True,                   # Already set (needed for cookies)
    allow_methods=["*"],
    allow_headers=["*"],
)
```

No backend changes needed for CORS.

### JWT Auth Pattern: API Route Proxy

**Architecture:** Next.js API routes act as a proxy to FastAPI, storing JWT in httpOnly cookies.

```
Browser --> Next.js API Route (/api/auth/login)
                |
                +--> fetch(FastAPI /api/v1/auth/login)
                |
                +--> Set httpOnly cookie with access_token
                |
                +--> Return success to browser

Browser --> Next.js API Route (/api/documents)
                |
                +--> Read httpOnly cookie
                |
                +--> Forward to FastAPI with Authorization header
                |
                +--> Return response to browser
```

This pattern ensures:
- JWT tokens never touch client-side JavaScript (XSS-safe)
- Same-origin requests (no CORS issues for cookies)
- Backend auth system unchanged

### SSE Streaming Pattern

```
Browser (client component) --> fetch(/api/v1/queries/stream, { POST })
                                    |
                                    +--> ReadableStream
                                    |
                                    +--> eventsource-parser
                                    |
                                    +--> Update React state per token
                                    |
                                    +--> react-markdown renders incrementally
```

Direct browser-to-FastAPI connection for SSE (not proxied through Next.js API routes) because:
- Streaming responses are long-lived
- Proxying SSE through Next.js adds latency and memory overhead
- Frontend sends Authorization header directly (read from zustand store)

### Backend Endpoints to Consume

| Backend Endpoint | Method | Frontend Usage |
|-----------------|--------|----------------|
| `/api/v1/auth/register` | POST | Registration form |
| `/api/v1/auth/login` | POST | Login (proxied via Next.js API route for httpOnly cookie) |
| `/api/v1/auth/refresh` | POST | Token refresh (proxied via Next.js API route) |
| `/api/v1/auth/logout` | POST | Logout (proxied via Next.js API route) |
| `/api/v1/documents/upload` | POST | File upload (PDF/DOCX) |
| `/api/v1/documents` | GET | Document list |
| `/api/v1/documents/{id}` | DELETE | Document deletion |
| `/api/v1/documents/{id}/status` | GET | Upload processing status |
| `/api/v1/queries/stream` | POST | SSE streaming Q&A (direct from browser) |
| `/api/v1/queries/enhanced` | POST | Enhanced query with citations |
| `/api/v1/comparisons` | POST | Document comparison |
| `/api/v1/comparisons/{id}/state` | GET | Comparison session state |
| `/api/v1/memory` | GET/POST/DELETE | Memory management |
| `/api/v1/admin/*` | Various | Admin features (role-gated) |

### Environment Variables (Frontend)

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
# No secrets in NEXT_PUBLIC_ vars -- they're exposed to the browser
```

```bash
# .env (server-side only, for API route proxy)
API_URL=http://localhost:8000/api/v1
JWT_COOKIE_NAME=rag_session
```

---

## Tailwind CSS v4 Configuration Notes

Tailwind v4 uses CSS-first configuration. No `tailwind.config.js` needed.

```css
/* src/app/globals.css */
@import 'tailwindcss';

/* Dark mode: shadcn/ui uses class-based dark mode via next-themes */
/* Tailwind v4 detects dark mode from the 'dark' class on <html> automatically */

/* Custom theme extensions done in CSS, not JS */
@theme {
  --color-brand: oklch(0.7 0.15 200);
  --font-sans: 'Inter', sans-serif;
}
```

---

## Directory Structure (Recommended)

```
frontend-next/
├── src/
│   ├── app/
│   │   ├── layout.tsx              # Root layout (ThemeProvider, Toaster)
│   │   ├── page.tsx                # Landing/redirect
│   │   ├── globals.css             # Tailwind imports + CSS vars
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   └── register/page.tsx
│   │   ├── (dashboard)/
│   │   │   ├── layout.tsx          # Authenticated layout with sidebar
│   │   │   ├── documents/page.tsx
│   │   │   ├── chat/page.tsx       # Q&A with SSE streaming
│   │   │   ├── compare/page.tsx
│   │   │   ├── memory/page.tsx
│   │   │   └── admin/page.tsx
│   │   └── api/
│   │       └── auth/
│   │           ├── login/route.ts   # Proxy: set httpOnly cookie
│   │           ├── refresh/route.ts # Proxy: refresh token
│   │           └── logout/route.ts  # Proxy: clear cookie
│   ├── components/
│   │   ├── ui/                     # shadcn/ui components (auto-generated)
│   │   ├── chat/                   # Chat-specific components
│   │   ├── documents/              # Document upload/list
│   │   └── layout/                 # Sidebar, header, theme toggle
│   ├── hooks/                      # Custom React hooks
│   ├── lib/
│   │   ├── utils.ts                # cn() helper (from shadcn init)
│   │   ├── api.ts                  # Fetch wrapper with auth
│   │   └── sse.ts                  # SSE stream consumption
│   ├── stores/
│   │   ├── auth-store.ts           # zustand: auth state
│   │   └── chat-store.ts           # zustand: chat messages, streaming state
│   └── types/
│       └── api.ts                  # TypeScript types matching backend schemas
├── public/
├── postcss.config.mjs
├── next.config.ts
├── tsconfig.json
├── eslint.config.mjs
├── components.json                  # shadcn/ui config
└── package.json
```

---

## Version Compatibility Matrix

| Frontend Package | Backend Dependency | Compatibility Notes |
|-----------------|-------------------|---------------------|
| Next.js 15.5 | FastAPI (any) | Backend is framework-agnostic REST API |
| React 19.1 | N/A | Client-side only |
| Tailwind v4 | N/A | Client-side only |
| eventsource-parser 3.x | SSE-Starlette 2.0+ | Both follow SSE spec (text/event-stream) |
| zod 3.24 | pydantic 2.7+ (backend) | Both validate -- no direct coupling, but schemas should mirror |
| fetch (built-in) | Uvicorn/ASGI | Standard HTTP/1.1 |

---

## Sources

**Official Documentation (HIGH confidence):**
- [Next.js Installation](https://nextjs.org/docs/app/getting-started/installation) -- create-next-app defaults, prompts
- [Next.js 16 Blog Post](https://nextjs.org/blog/next-16) -- confirmed 16 is current, validated 15 is still LTS
- [Next.js Upgrade Guide v16](https://nextjs.org/docs/app/guides/upgrading/version-16) -- breaking changes documented
- [Tailwind CSS v4 Blog](https://tailwindcss.com/blog/tailwindcss-v4) -- CSS-first config, PostCSS setup
- [Tailwind CSS PostCSS Setup](https://tailwindcss.com/docs/installation/using-postcss) -- @tailwindcss/postcss integration
- [shadcn/ui Next.js Installation](https://ui.shadcn.com/docs/installation/next) -- init process, dependencies
- [shadcn/ui Changelog](https://ui.shadcn.com/docs/changelog) -- unified radix-ui package, Tailwind v4 support
- [shadcn/ui Dark Mode](https://ui.shadcn.com/docs/dark-mode/next) -- next-themes integration

**NPM Registry (HIGH confidence) -- versions verified Feb 8, 2026:**
- [next](https://www.npmjs.com/package/next) -- 16.1.6 latest, 15.5.x LTS
- [react](https://www.npmjs.com/package/react) -- 19.2.4 latest
- [tailwindcss](https://www.npmjs.com/package/tailwindcss) -- 4.1.18 latest
- [radix-ui](https://www.npmjs.com/package/radix-ui) -- 1.4.3 latest
- [zustand](https://www.npmjs.com/package/zustand) -- 5.0.11 latest
- [motion](https://www.npmjs.com/package/motion) -- 12.33.0 latest
- [react-hook-form](https://www.npmjs.com/package/react-hook-form) -- 7.71.1 latest
- [zod](https://www.npmjs.com/package/zod) -- 4.3.6 latest (v4); 3.24.x latest v3
- [@hookform/resolvers](https://www.npmjs.com/package/@hookform/resolvers) -- 5.2.2 latest
- [next-themes](https://www.npmjs.com/package/next-themes) -- 0.4.6 latest
- [sonner](https://www.npmjs.com/package/sonner) -- 2.0.7 latest
- [lucide-react](https://www.npmjs.com/package/lucide-react) -- 0.563.0 latest
- [nuqs](https://www.npmjs.com/package/nuqs) -- 2.8.8 latest
- [react-markdown](https://www.npmjs.com/package/react-markdown) -- 10.1.0 latest
- [eventsource-parser](https://www.npmjs.com/package/eventsource-parser) -- published actively

**Community Research (MEDIUM confidence):**
- [Descope: Next.js 15 vs 16](https://www.descope.com/blog/post/nextjs15-vs-nextjs16) -- comparison analysis
- [Motion Upgrade Guide](https://motion.dev/docs/react-upgrade-guide) -- framer-motion to motion migration
- [Zod v4 hookform/resolvers issue](https://github.com/colinhacks/zod/issues/4992) -- compatibility problems documented
- [Next.js SSE Discussion](https://github.com/vercel/next.js/discussions/48427) -- SSE patterns in App Router
- [Auth0: Next.js 16 Auth](https://auth0.com/blog/whats-new-nextjs-16/) -- middleware to proxy rename impact on auth

---

*Stack research for: Next.js Production Frontend for RAG with Graph Store*
*Researched: 2026-02-08*
*Focus: Integration with existing FastAPI backend (JWT auth, SSE streaming, document upload)*
