# Launch plan

A plan for the first 30 days. The goal isn't "lots of users". It's to learn, cheaply and
fast, whether people come back and whether anyone would pay. Everything here can be done
by one person in a few hours a week.

## 1. Who it's for first

Pick **one** group to win before trying to please everyone. The app's strongest fit today:

> **Confident home cooks stuck on the same 5–10 dishes, often cooking for one or two,
> who'd try something new if it didn't feel like a project.**

The sharpest version of that group, and the founding user, is **Indian home cooks living
abroad** (students and young professionals): they cook dal, curry and biryani well, are
curious about the food around them, and gather in a few easy-to-reach places online. The
starter tiles and the dish graph already serve them well.

Say it plainly on launch posts. A narrow message ("for people who cook dal and curry on
autopilot") gets more clicks than a broad one ("discover new recipes").

## 2. The one-line pitch

> **Tell it what you already cook. It shows dishes from around the world you're one step
> away from, written as just the change.**

Proof to show, not tell: a screenshot of one card, e.g. *"Mesir Wat: your dal tadka,
but… use red lentils and stir in berbere."* That card is the whole product in one image.

## 3. Before posting (launch checklist)

- [ ] Merge and deploy the open PRs (API first, then web). See `docs/runbook.md`.
- [ ] Railway: move the start command off `railway.toml` (runbook, before Dec 1, 2026).
- [ ] A custom domain (about $10–15/year). `one-step-six-brown.vercel.app` looks unfinished
      in a Reddit post and can't be remembered. Decide the name first.
- [ ] Check the funnel works: visit the site in a private window, then
      `GET /api/admin/stats?days=1` should show `visited ≥ 1`.
- [ ] Set an OpenAI monthly budget limit (the hard backstop behind `DAILY_LLM_CALL_CAP`).
- [ ] Ask 3 friends to try it on their phones while you watch. Fix what confuses them.

## 4. Where to post (one a week, not all at once)

Posting everywhere on one day wastes the learning: you can't tell which message or place
worked. Space them out and change one thing at a time.

| Week | Where | Angle |
|---|---|---|
| 1 | Friends, family, WhatsApp groups of people who cook | "I built this, tell me what's confusing" |
| 2 | r/IndianFood, r/indiansabroad-type communities, student groups | "If you cook dal on autopilot, here's what's one step away" |
| 3 | r/Cooking, r/cookingforbeginners, r/EatCheapAndHealthy | The kabsa / jollof / plov "same method, new dish" angle |
| 4 | Show HN, Indie Hackers | The engineering story: code decides, the LLM only writes (`docs/case-study.md`) |

Read each community's self-promotion rules first. Most allow a post if you're open that
you built it and you're asking for feedback, not selling.

## 5. Draft posts (edit into your own voice)

**Reddit (cooking communities)**

> **I cook the same 6 dishes every week, so I built a thing that shows what I'm one step
> away from**
>
> You tap the dishes you already make (dal, chicken curry, fried rice…). It finds dishes
> from other cuisines that use the same method, and writes only what's different:
> "Mesir Wat: your dal tadka, but… red lentils and berbere."
>
> Free, no sign-up, works on your phone. I'd love to know which suggestion you'd actually
> cook, and which one made no sense. [link]

**Show HN**

> **Show HN: One Step – recipes written as diffs from the dishes you already cook**
>
> Cooking apps match by flavour; this connects dishes by cooking method over a 718-dish
> graph. Code decides what's "one step" (graph distance, diet and allergen filters); the
> LLM only writes the 3–5 bullet diff, and code drops bullets that re-tell steps you
> already do. Evals run against the live model on every PR. Write-up: [case study link]

## 6. What to measure (and what "working" looks like)

`GET /api/admin/stats?days=7` now returns a funnel. Rough targets for a small, warm launch:

| Step | Healthy | If it's low |
|---|---|---|
| visited → built a kitchen | 40%+ | The first screen doesn't explain itself; test a new headline |
| built a kitchen → saw results | 90%+ | Something is broken or too slow; check Sentry |
| saw results → saved or cooked | 15%+ | Suggestions don't feel cookable; read feedback, look at `top_dishes` |
| came back (2+ days) | 10%+ of visitors | No reason to return yet: reminders or a weekly pick |

Also read every feedback message. At this size one sentence of feedback is worth more
than any chart.

## 7. When to ask for money

Not before people come back on their own. Once "came back" is steady:

1. Add an opt-in "email me a new one-step dish each Sunday" after someone cooks or saves.
   It costs nothing to offer and shows who cares enough to give an address.
2. When that list has ~50 people, offer something small and paid to them (e.g. a
   weekly plan from their kitchen with a shopping list, ~$3/month) and count who says yes.
   Even 3–5 yeses is a real signal.

Ten people who pay teach more than a thousand who visited once.
