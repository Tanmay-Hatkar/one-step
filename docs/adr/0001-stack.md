# ADR-0001: Stack — web-first PWA, FastAPI, Postgres, OpenAI without a framework

**Date:** 2026-10-20 · **Status:** Accepted

## Context

One Step is a portfolio project that must be **live and clickable**: a recruiter should
see it working in 30 seconds without installing anything. The author is strongest in
Python and has already shipped a React Native app (Overwatch), so mobile skills are
already on show.

## Decision

- **Web first, mobile-first PWA** (Next.js + TypeScript + Tailwind + shadcn/ui) on Vercel.
  No app stores: zero review delay, zero store fees, a link anyone can open.
- **FastAPI (Python 3.12, uv)** on Railway, where the ML, data pipeline and evals live.
- **Postgres in production, SQLite locally and in tests**, through SQLAlchemy. A graph
  database is overkill for hundreds to low thousands of dishes.
- **OpenAI via the official SDK** with structured outputs validated by Pydantic. No
  LangChain: calling the SDK directly keeps every prompt and parse visible.
  Runtime `gpt-5.4-mini`; one-time seed generation `gpt-5.5`.

## Consequences

- A native app later is a new frontend over the same API, not a rewrite.
- Swapping LLM providers means implementing one `LLMClient` protocol.
