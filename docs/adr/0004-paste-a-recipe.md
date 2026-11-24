# ADR-0004: Paste a recipe — the catalog stops being the limit

**Date:** 2026-11-14 · **Status:** Accepted

## Context

One Step only knew its own 718 dishes, and people open it only when they want something
new. But they already find recipes elsewhere (web pages, video captions, messages) and
mostly don't cook them, because an unfamiliar recipe reads like a project. Recipe-saver
apps import those recipes and store them as written. Nobody rewrites them relative to
what the cook already makes, which is the one thing One Step does.

## Decision

`POST /api/paste` takes a link or recipe text plus the user's kitchen and returns the
same `Cousin` shape as every other suggestion.

| Where | What |
|---|---|
| Code | Is it a link or text; fetching the page safely; pulling schema.org JSON-LD out of it |
| LLM (1 call) | Reading the recipe into the catalog's parts: family, techniques, ingredients, steps |
| Code | Validating and trimming every field; allergens and vegetarian from keyword rules; the delta against the kitchen; one-step or stretch; diet flags |
| LLM (1 call) | Writing the diff, exactly as for catalog dishes (template fallback if it fails) |

- **Diet:** a pasted dish that breaks the user's diet is shown (they chose it) with a
  warning computed in code. Swaps still respect the diet.
- **Links are untrusted input.** `PageRepository` allows only http(s) on default ports,
  requires every resolved address to be public, connects to the address it checked,
  re-checks each redirect, and caps the body. Login-walled sites (Instagram, TikTok,
  YouTube…) are refused with a message asking for the caption text instead.
- **Pasted text is untrusted too.** The prompt treats it as content, the output schema is
  closed vocabularies, and an eval case carries an injected instruction.
- **Nothing is stored server-side** beyond the usual LLM answer cache. The recipe lives
  in the user's saved kitchen on their device (and their passkey sync), capped at 12.
  Steps are shortened, not copied, and the source link is kept and shown.
- The installed app is a **share target**, so "Share → One Step" from a browser lands
  in the paste box.

## Consequences

- Any recipe on the open web becomes a One Step dish; "I cooked this" adds it to the
  kitchen and the map grows from it like any other.
- Two LLM calls per paste (about 5 s). Rate-limited separately (`paste_rate_limit`).
- Pasted dishes have no illustration and no place on the map until cooked.
- Video links aren't opened, but a **screenshot or photo** is read (`POST
  /api/paste/photo`): the browser shrinks it, code checks its real type and size, and
  the same reading prompt runs with the picture attached. Pictures aren't stored.
- New eval suite `paste` (reading, allergens in code, injection, non-recipes).
