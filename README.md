# One Step

*Working name.* A cooking agent that learns the dishes you already cook and shows you the
ones you're **one step away from** — written as only what's different from your version.

**Try it:** https://one-step-six-brown.vercel.app (API on Railway + Postgres, web on Vercel)

> **Kabsa** — *your chicken leg with rice, but…*
> - Sear the chicken leg first instead of marinating it.
> - Cook the onion, garlic, tomato, ginger, kabsa spice and dried lime in the pot.
> - Simmer the chicken in stock, then add raisins.
>
> *Keep cooking the rice in stock, as you already do.*

Most recipe apps match by flavor. One Step connects dishes by **cooking method**, so
chicken with broth rice leads you to kabsa, maqluba, arroz con pollo, jambalaya and plov.

## How it works

```
"what I usually cook" ──► LLM parses YOUR version ──► dish graph (code) ──► LLM writes the diff
     free text               into structured parts       finds cousins           (headline in code)
```

- **Say it out loud** — tap the mic and describe your cooking; `gpt-4o-mini-transcribe`
  (with a hint for words like *jeera* and *tadka*) puts it in the box to check before
  sending. About $0.003 a minute, inside the same daily cap. Hidden where recording isn't supported.
- **Dish graph** — 150 home dishes from 10 regions, each broken into parts on a closed
  vocabulary (family, technique, equipment, flavor, allergens). Distance is plain code.
- **Tonight** — pick your time; get something familiar, one step away, and a stretch.
  "Not tonight" skips a pick; "I cooked this" adds a dish to your kitchen so new cousins
  grow from it (saved on your device — no accounts yet).
- **Diet as a hard filter** — vegetarian and 9 allergens, enforced in code. Each dish's
  tagged allergens are cross-checked against its ingredients, and a written diff that
  mentions an avoided allergen is replaced by a template.
- **Your map** — your dishes in the middle, their cousins around them (one step = solid,
  bigger step = dashed). Tap a dish to see it written from your kitchen; cook one and the
  map grows. No LLM call to draw it.
- **Share a kitchen** — a short `/k/<id>` link to a read-only snapshot anyone can start from.
- **Public eval page** — `/evals` shows the latest live eval results, including a code-only
  diet-safety sweep (every rule over 152 kitchens, across suggestions, tonight and the map).
- **LLM only for language** — parsing your description, and phrasing each difference.
  Cached, rate-limited, capped per day, with a template fallback ([ADR-0003](docs/adr/0003-code-decides-llm-writes.md)).
- **Evals** — 20 live cases / 99 checks on parsing, diff grounding and end-to-end
  relevance, plus the diet-safety sweep (`api/evals/`). Current: **109/109**, published at `/evals`.

## Run it locally

```bash
cp .env.example .env                       # add OPENAI_API_KEY

cd api && uv sync
uv run uvicorn app.main:app --reload       # http://localhost:8000
uv run pytest                              # 115 tests, no network
uv run python -m evals.run                 # live evals

cd ../web && npm install && npm run dev    # http://localhost:3000
```

## Repo

| Path | What |
|---|---|
| `api/` | FastAPI backend — graph, LLM gateway, services, tests, evals |
| `api/data/dishes.json` | The seed dish catalog (reviewed data) |
| `web/` | Next.js mobile-first PWA |
| `docs/` | [Concept](docs/concept.md) and [decision records](docs/adr/) |

## Roadmap

v0.1 cousins as diffs → v0.2 tonight's pick + diet filter + "I cooked this" → v0.3 the map +
share links + public eval page (this) → v0.4 substitutions → v1.0 real recipe dataset + fine-tuned parser.
