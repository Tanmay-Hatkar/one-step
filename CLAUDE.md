# CLAUDE.md — Working agreement for Claude Code

Auto-loaded on every chat. Project context, working agreement, pointers.

---

## Project goal

**One Step** (working name) is a cooking agent. It learns the dishes you already
cook — in your own words — and shows you dishes you're *one step away from*,
written as only what's different from your version.

> "Kabsa: your usual rice, but… mix baharat, add a dried lime, cook the chicken
> in the rice pot."

Taste-profile apps match by flavor. One Step connects dishes by **cooking
method**, so your chicken-and-broth-rice leads to kabsa, plov, jollof and
Hainanese chicken rice.

Full concept: [`docs/concept.md`](docs/concept.md). Decisions: [`docs/adr/`](docs/adr/).

---

## Working agreement

This is a **fast-paced** project. The author wants to ship quickly.

- **One recommendation, with a default.** Don't survey options — recommend, and
  let the author override.
- **Build in vertical slices**, each live and usable: data → API → UI → tests → CI.
- **Larger chunks are fine.** Explain the plan briefly, then build.
- **Never deploy or spend money** (beyond small dev LLM calls) without asking.
- **Every version ships live.** If it isn't on a URL, it isn't done.

### Where logic lives (the core design rule)

| Place | Holds | Example |
|---|---|---|
| Data (build time) | Facts worked out ahead of time | `api/data/dishes.json` — each dish broken into parts |
| Code | Rules that must never be wrong | graph search, ranking, allergen filtering, units |
| LLM | Language and judgment | parsing "my chicken leg with Indian spices", writing the diff |
| Evals | Checks that the above is right | `api/evals/` |

**Never put a hard rule in a prompt.** Allergens, diet, counts and maths are code.
The LLM only ever sees a small, pre-filtered, relevant set.

### Code style

- Type hints on every function; docstrings on public ones (Args / Returns / Raises).
- try/except around every external call (LLM, DB, network).
- `logging` only — no `print()` in app code.
- No hardcoded values — constants in `api/app/config.py` or `.env`.
- Layered backend: `models` → `repositories` → `services` → `routes`. Routes never
  touch a repository directly.
- Small functions; one job each.

---

## Git conventions

- Conventional Commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:`.
- Short-lived branches off `main`, squash-merged via PR. Never push to `main`
  directly after the initial commit; never force-push `main`; never `--no-verify`.

---

## Tech stack

- **web/** — Next.js (App Router) + TypeScript + Tailwind + shadcn/ui, mobile-first PWA. Hosted on Vercel.
- **api/** — Python 3.12 + FastAPI, managed with uv. Hosted on Railway.
- **DB** — Postgres in production, SQLite locally/tests (SQLAlchemy).
- **LLM** — OpenAI via the official SDK, structured outputs validated by Pydantic.
  Runtime model `gpt-5.4-mini`; seed-data generation `gpt-5.5` (both in config).
- **Testing** — pytest (api), ESLint + typecheck + build (web), evals in `api/evals/`.
- **Linting** — ruff (Python), ESLint (web).

### Commands

```bash
# api
cd api && uv sync && uv run pytest && uv run ruff check . && uv run ruff format --check .
uv run uvicorn app.main:app --reload          # dev server on :8000
uv run python -m evals.run                    # live LLM evals (needs OPENAI_API_KEY)

# web
cd web && npm install && npm run dev          # :3000
npm run lint && npm run typecheck && npm run build
```
