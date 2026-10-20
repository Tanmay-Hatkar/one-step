# One Step

*Working name.* A cooking agent that learns the dishes you already cook and shows you the
ones you're **one step away from** — written as only what's different from your version.

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

- **Dish graph** — 150 home dishes from 10 regions, each broken into parts on a closed
  vocabulary (family, technique, equipment, flavor, allergens). Distance is plain code.
- **Tonight** — pick your time; get something familiar, one step away, and a stretch.
  "Not tonight" skips a pick; "I cooked this" adds a dish to your kitchen so new cousins
  grow from it (saved on your device — no accounts yet).
- **Diet as a hard filter** — vegetarian and 9 allergens, enforced in code. Each dish's
  tagged allergens are cross-checked against its ingredients, and a written diff that
  mentions an avoided allergen is replaced by a template.
- **LLM only for language** — parsing your description, and phrasing each difference.
  Cached, rate-limited, capped per day, with a template fallback ([ADR-0003](docs/adr/0003-code-decides-llm-writes.md)).
- **Evals** — 20 live cases / 99 checks on parsing, diff grounding and end-to-end
  relevance (`api/evals/`). Current: **99/99**.

## Run it locally

```bash
cp .env.example .env                       # add OPENAI_API_KEY

cd api && uv sync
uv run uvicorn app.main:app --reload       # http://localhost:8000
uv run pytest                              # 90 tests, no network
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

v0.1 cousins as diffs → v0.2 tonight's pick + diet filter + "I cooked this" (this) → v0.3 the map +
public eval page → v0.4 substitutions → v1.0 real recipe dataset + fine-tuned parser.
