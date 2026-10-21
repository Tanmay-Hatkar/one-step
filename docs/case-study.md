# One Step — case study

**Live:** https://one-step-six-brown.vercel.app · **Evals:** [/evals](https://one-step-six-brown.vercel.app/evals) · **Code:** this repo

One Step is a cooking app built around one idea: *you can already cook dishes you've never
heard of.* You describe what you usually make, in your own words or out loud. It shows you
dishes from around the world that are one step away, written as only what's different from
your version:

> **Kabsa** — your chicken leg with rice, but… toast a kabsa spice mix, add a dried lime,
> and cook the chicken in the rice pot.

This page is about how it's built and why, for anyone reviewing it as an engineering project.

---

## The problem

Most home cooks know a handful of dishes well and don't branch out. The reason isn't a
lack of recipes. An unfamiliar 14-step recipe feels like a project, so the usual dish wins.
Recipe apps match by flavor ("you liked X, try Y"), and chat assistants forget your
kitchen and write every recipe from scratch.

One Step connects dishes by **cooking method**. If you already make chicken with
broth-cooked rice, then kabsa, plov, jollof and Hainanese chicken rice are each a small
step away. It shows only the step.

## Architecture

```
"what I usually cook" ─► LLM: read YOUR version ─► dish graph (code) ─► LLM: write the difference
  text or voice            into structured parts     finds the cousins      (headline in code)
```

| Layer | Holds | Example |
|---|---|---|
| Data (built once) | Facts worked out ahead of time | 718 dishes split into family, techniques, equipment, flavor and allergens; 931 ingredient substitutions by role |
| Code | Rules that must never be wrong | graph distance, "one step" rules, diet and allergen filtering, ranking |
| LLM | Language and judgment | reading "my chicken leg with Indian spices"; writing 2–5 bullets of difference |
| Evals | Proof the above holds | 131 live checks, a diet-safety sweep, a model bake-off |

**Stack:** FastAPI (Python 3.12, uv), SQLAlchemy (Postgres on Railway, SQLite locally),
Next.js 16 App Router with Tailwind and shadcn/ui (Vercel), OpenAI structured outputs
validated by Pydantic. The backend is layered models → repositories → services → routes.

## Decisions worth explaining

**1. Code decides, the LLM only writes** ([ADR-0003](adr/0003-code-decides-llm-writes.md)).
The model never decides what's safe to eat or what counts as "one step". Diet rules,
allergens and ranking are plain code over the dish graph. The LLM sees a small,
pre-filtered set and only writes language. If a written difference mentions an allergen
you avoid, it's thrown away and replaced by a template. That's what lets the
diet-safety sweep say **0 violations** with a straight face.

**2. "Here's what I heard" instead of a chat.** Free text is vague: "Indian spices" could
mean five things. The app doesn't open a conversation. It shows what you *said* (solid
chips) apart from what it *guessed* (dashed, tap to keep or ×). Then it asks **at most
three** tap questions, chosen by code: each candidate answer is applied to your kitchen
and the graph is run again. A question is only asked if its answer would change your
suggestions (expected change over the top results, plus a Jaccard distance on the
one-step set). Asking about an oven only happens when an oven would unlock something.

**3. A 718-dish catalog without a 718-dish prompt.** Reading your kitchen means matching
your dishes to the catalog. Rather than sending every name, code shortlists likely
matches first (IDF-weighted name words plus fuzzy matching). The prompt went from about
33.7k characters to at most 1.6k, so growing the catalog 5× didn't raise the cost per user.

**4. Real recipes, credited.** About 580 recipes come from the Wikibooks Cookbook (CC BY-SA
4.0). An LLM only judged whether each recipe belongs and mapped it onto the fixed
vocabulary. The recipe text is kept as written, with attribution on every page. Dish
images are AI-generated, about $0.002 each, and labelled as illustrations.

**5. Fine-tuning → a model bake-off.** v0.8 was planned as a fine-tuned parser, but OpenAI
closed new fine-tuning jobs. The question behind it was "is there a cheaper model that's
just as good?", and that can be answered without training. `evals/bakeoff.py` runs
the same AI checks on six models with a fresh cache and records the checks passed, cost
and latency. A rule in code picks the cheapest model that passes as many checks as the
current one:

| Model | Checks | $ / 1k calls | s / call |
|---|---|---|---|
| **gpt-5.4-mini** (in use) | 120/121 | 1.71 | 2.4 |
| gpt-4.1-mini | 119/121 | 0.67 | 1.7 |
| gpt-5-mini | 119/121 | 2.46 | 10.5 |
| gpt-5-nano | 115/121 | 0.55 | 8.5 |
| gpt-5.4-nano | 114/121 | 0.44 | 1.9 |
| gpt-4o-mini | 113/121 | 0.24 | 1.6 |

The current model stays. gpt-4.1-mini is 2.5× cheaper but sometimes misreads a protein or
drops a named ingredient, and in this app that error carries through to every
suggestion. The full table and each model's failures are public on `/evals`.

**6. Accounts without accounts.** Sign-in is optional and passkey-only (WebAuthn): no
email, no password, no third-party auth. The account is a random id. The server keeps
the passkey's public key, sessions stored by hash, and your kitchen. Signed out,
everything works on the device. It's tested end to end with a software authenticator in
pytest and Chrome's virtual authenticator in a browser test (save on a "phone", sign in on
a "laptop", same kitchen).

## Quality

- **131/131 live eval checks**, re-run in CI on every PR against the real model:
  - parsing (69 checks)
  - grounded differences (40)
  - end-to-end relevance (12)
  - a code-only diet sweep (10 rules over 152 kitchens, across suggestions, tonight's
    picks, the map and every offered swap)
- **151 API tests**, no network. Web lint, typecheck and build in CI.
- Every version shipped with light and dark screenshots from a headless-browser test.

## Cost

- **Running:** about $1.70 per 1,000 AI calls; a visit is a handful of calls. LLM
  responses are cached, rate-limited per IP, and capped per day (fail closed).
- **One-time, everything:** about $5 in API spend (estimated from token counts). That covers generating 931
  substitutions and 22 technique guides, importing about 890 Wikibooks recipes, 718 dish
  illustrations, and all eval runs.

## Timeline

v0.1 differences → v0.2 tonight's pick + diet filter → v0.3 the map, share links, public
evals → v0.4 voice input → v0.5 "what I heard" and gain-picked questions → v0.6 swaps from
your kitchen, how-to cards → v0.7 718 dishes, real recipes, illustrations → v0.8 model
bake-off → v0.9 passkey sync → **v1.0** installable app, share previews, this write-up.

## What I'd do next

- Learn from use: which suggestions get cooked, then re-weight the graph from that.
- A second model as a fallback behind the same gateway, chosen by the bake-off.
- Grocery-aware picks: "you have half a cabbage, here's what's one step away".

---

*Built by Tanmay Hatkar, pairing with Claude Code (Anthropic) as the coding agent.*
