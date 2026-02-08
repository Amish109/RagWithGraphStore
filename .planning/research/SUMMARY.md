# Research Summary: Next.js Production Frontend

**Domain:** Production frontend for RAG document Q&A system
**Researched:** 2026-02-08
**Overall confidence:** HIGH

## Executive Summary

The Next.js production frontend replaces the existing Streamlit test frontend with a full-featured, responsive web application. The ecosystem is mature and well-documented in early 2026. Next.js 15 (with App Router) remains production-stable despite Next.js 16 being the current release, and is the safer choice for a new frontend build. The FastAPI backend requires zero changes -- CORS is already configured for localhost:3000 with credentials support.

The core stack is Next.js 15 + React 19 + Tailwind CSS v4 + shadcn/ui. This combination is the dominant pattern in the React ecosystem in 2026. shadcn/ui provides accessible, customizable components that integrate with Tailwind, and its CLI-based approach means components are copied into the project rather than installed as dependencies (no vendor lock-in). Tailwind v4 has moved to CSS-first configuration, eliminating the JavaScript config file entirely.

The most architecturally significant decisions are around auth and SSE streaming. JWT tokens should be stored in httpOnly cookies via Next.js API route proxies (not in localStorage or client-side state) for XSS protection. SSE streaming requires using fetch() with ReadableStream rather than the browser's EventSource API, because the backend's streaming endpoint uses POST requests (EventSource only supports GET). The `eventsource-parser` library handles SSE parsing from fetch streams.

State management is minimal -- zustand handles the small amount of client-side state (auth status, chat messages, UI toggles), while server components and fetch handle all server-state data fetching natively through Next.js's built-in mechanisms.

## Key Findings

**Stack:** Next.js 15.5 + React 19 + Tailwind v4 + shadcn/ui + zustand + motion. 19 production deps, 7 dev deps.
**Architecture:** App Router with route groups, API route proxy for auth, direct SSE for streaming, server components for data fetching.
**Critical pitfall:** Using native EventSource for POST-based SSE will fail silently. Must use fetch + eventsource-parser.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Project Scaffold and Auth** - Set up Next.js, shadcn/ui, theming, and JWT auth proxy
   - Addresses: Project structure, dark/light theme, login/register forms
   - Avoids: Auth architecture decisions compounding through later phases

2. **Document Management** - File upload, document list, status tracking
   - Addresses: PDF/DOCX upload, document list with pagination, deletion
   - Avoids: Building on incomplete auth (phase 1 must be solid first)

3. **Chat and SSE Streaming** - Q&A interface with real-time streaming
   - Addresses: SSE streaming, markdown rendering, chat history
   - Avoids: The most complex SSE integration built on unstable foundations

4. **Advanced Features** - Comparison view, memory management, admin panel
   - Addresses: Document comparison, memory CRUD, role-gated admin
   - Avoids: Scope creep in earlier phases

5. **Polish and Responsive** - Mobile layout, animations, loading states, error handling
   - Addresses: Responsive design, skeleton loading, page transitions, error boundaries
   - Avoids: Premature optimization before features are working

**Phase ordering rationale:**
- Auth MUST come first because every other feature depends on authenticated API calls
- Documents before chat because chat queries require uploaded documents
- Streaming is the most technically complex feature and benefits from stable auth + API patterns established in phases 1-2
- Polish last because responsive design and animations are meaningless without working features

**Research flags for phases:**
- Phase 1: Standard patterns, well-documented. LOW research risk.
- Phase 3: SSE streaming with POST + incremental markdown rendering needs careful implementation. MEDIUM research risk.
- Phase 4: Comparison view may need specific UI patterns for side-by-side document comparison. LOW-MEDIUM research risk.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified on npm. Well-documented ecosystem. |
| Features | HIGH | Feature set is standard for document Q&A applications. |
| Architecture | HIGH | App Router patterns are well-established. API proxy for auth is proven. |
| Pitfalls | HIGH | SSE + POST limitation is well-documented. Zod v4 issues confirmed via GitHub. |

## Gaps to Address

- **react-shiki version confirmation**: Recommended ^0.8.0 based on search results but this is a newer library. May need to verify exact API during implementation.
- **Tailwind v4 + shadcn/ui dark mode CSS variables**: The CSS-first configuration in Tailwind v4 changes how shadcn/ui theme CSS variables work. May need phase-specific research during scaffolding.
- **File upload size limits**: Backend caps at 50MB (`MAX_UPLOAD_SIZE_MB` in config.py). Frontend needs to enforce this client-side before upload.
- **Token refresh flow**: Backend has 30-minute access token expiry. Frontend needs proactive refresh before expiration -- exact pattern should be designed during phase 1 implementation.
