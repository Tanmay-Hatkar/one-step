# One Step — Concept

Living version (with research and sources): [concept doc](https://claude.ai/code/artifact/a31d5b95-6046-4847-b5c8-736adffad0d5).

## Pitch

A cooking agent that learns how you already cook, then shows you the dishes you're
one step away from, written as only what's different from your version.

## Problem

- **Deciding** — "I don't know what to cook" is decision fatigue, not a lack of recipes.
- **Discovering** — most people only know the dishes they grew up with; finding new
  ones takes effort (YouTube, cooking shows).
- **New recipes feel like projects** — a 14-step unfamiliar recipe loses to the usual.

## Who it's for

Confident home cooks stuck in a comfort zone — often cooking for one, away from home.
Founding user: weeknight chicken leg in an Indian marinade with rice-cooker broth rice;
biryani on weekends.

## How it works

1. **Your repertoire, in your words** — described like you'd tell a friend; saved as
   *your version*, broken into parts (protein, starch, flavor base, technique, equipment).
2. **Recipes as differences** — "Kabsa: your usual rice, but…" plus only what changes.
3. **Tonight's pick** — familiar / one step / stretch, from your time and mood. *(v0.2 ✓)*
4. **Substitutions by ingredient role** — acid for acid, binder for binder. *(v0.4)*
5. **A map that grows through dinner** — cook a cousin, unlock its cousins. *(v0.3 ✓)*

## Why it's different

Taste-profile apps (TasteOS, Mori, Vianda) match by flavor. One Step connects dishes
by **cooking method** and writes them relative to your own cooking. ChatGPT forgets
your repertoire and writes full recipes from scratch.

## Versions

| Version | Ships |
|---|---|
| v0.1 | Describe your dishes → 5 cousins written as differences. 150-dish seed graph. Live. |
| v0.2 | Tonight's pick, allergen/diet hard filter, "I cooked this" (on-device). ✓ |
| v0.3 | The map, shareable link, public eval page. ✓ |
| v0.4 | Voice input ✓ |
| v0.5 | "Here's what I heard": said vs guessed, questions picked by expected change ✓ |
| v0.6 | Substitutions by role, "what I have" chips, technique how-tos. |
| v1.0 | Real recipe dataset, fine-tuned parser model, eval dashboard, accounts, launch. |
| Later | Nutrition balance, native mobile, voice cook mode, fridge photos. |
