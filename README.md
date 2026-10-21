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

- **"Here's what I heard"** — before searching, you see what was understood: what you
  said (solid chips) and what was guessed from vague phrases like "Indian spices" (dashed,
  tap to keep or ×). Then at most 3 quick tap questions, picked by code: each answer is
  simulated on the dish graph and only questions that would change your suggestions are asked.
- **Swaps from your kitchen** — every ingredient has a role (acid, fat, warm spice…) and
  stand-ins, generated once and reviewed (`api/data/substitutions.json`). A dish only offers
  a swap you can make from what you already have, and never one your diet rules out.
- **What I have** — tools (an oven unlocks oven dishes) and pantry items; one tap adds what
  your suggestions often need.
- **How-to cards** — every new skill in a suggestion opens a 4-step guide, the common
  mistake, and a video search.
- **Say it out loud** — tap the mic and describe your cooking; `gpt-4o-mini-transcribe`
  (with a hint for words like *jeera* and *tadka*) puts it in the box to check before
  sending. About $0.003 a minute, inside the same daily cap. Hidden where recording isn't supported.
- **Dish graph** — 718 home dishes from 150+ cuisines, each broken into parts on a closed
  vocabulary (family, technique, equipment, flavor, allergens). Distance is plain code.
- **Real recipes** — 584 dishes have a full recipe from the [Wikibooks Cookbook](https://en.wikibooks.org/wiki/Cookbook:Table_of_Contents)
  (CC BY-SA 4.0, credited on each page). An LLM only mapped each recipe onto the vocabulary;
  the recipe text is kept as written (`api/scripts/import_wikibooks.py`). Each dish has its own
  page, written from your kitchen when you have one saved.
- **Dish illustrations** — one AI-generated image per dish (`gpt-image-1-mini`, low quality,
  ~$0.002 each), labelled as illustrations, not photos of the recipe.
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
- **Evals** — 21 live cases / 121 checks on parsing, diff grounding and end-to-end
  relevance, plus the diet-safety sweep (`api/evals/`). Current: **131/131**, published at `/evals`.

## Run it locally

```bash
cp .env.example .env                       # add OPENAI_API_KEY

cd api && uv sync
uv run uvicorn app.main:app --reload       # http://localhost:8000
uv run pytest                              # 145 tests, no network
uv run python -m evals.run                 # live evals

cd ../web && npm install && npm run dev    # http://localhost:3000
```

## Repo

| Path | What |
|---|---|
| `api/` | FastAPI backend — graph, LLM gateway, services, tests, evals |
| `api/data/dishes.json` | The dish catalog (reviewed data) |
| `api/data/recipes.json` | Wikibooks recipes with attribution (CC BY-SA 4.0) |
| `web/` | Next.js mobile-first PWA |
| `docs/` | [Concept](docs/concept.md) and [decision records](docs/adr/) |

## Roadmap

v0.1 cousins as diffs → v0.2 tonight's pick + diet filter + "I cooked this" → v0.3 the map +
share links + public eval page → v0.4 voice input → v0.5 "what I heard" + smart questions
→ v0.6 swaps + what I have → v0.7 real recipes + photos (this) → v0.8 fine-tuned parser → v0.9 passkey sign-in → v1.0 launch.
