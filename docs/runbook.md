# Runbook

How to ship, undo, and keep One Step healthy. Keep it short and true.

| Piece | Where | How it deploys |
|---|---|---|
| web (`web/`) | Vercel project `one-step` | Manual: `vercel --prod` from `web/` (not git-connected) |
| api (`api/`) | Railway service, root `api/`, Postgres attached | See `api/railway.toml`. Confirm in Railway → service → Settings → Source whether it auto-deploys from `main` |
| CI | GitHub Actions `.github/workflows/ci.yml` | Every PR and push to `main`: api tests, web build, live evals |

Live: https://one-step-six-brown.vercel.app · API health: `<railway-url>/health`

## Ship a version

1. PR green (API, Web, Evals). Squash-merge to `main`.
2. **API first** (the web app calls new endpoints): Railway deploys `main`, or
   `railway up` from `api/` if the service isn't git-connected. Wait for `/health` → `{"status":"ok"}`.
3. **Web**: `cd web && vercel --prod`.
4. Smoke test on a phone: pick 3 dishes → Tonight shows → Bring a recipe works → `/evals` loads.

## Roll back

- **Web:** `vercel ls one-step`, then `vercel promote <previous-deployment-url>` (or
  `vercel rollback`). Takes seconds.
- **API:** Railway → Deployments → previous one → **Redeploy**.
- **Code:** `git revert <sha>` on a branch, PR, merge. Never force-push `main`.
- DB changes are additive (`init_db` creates tables only), so rolling back code is safe.

## Environment variables

| Name | Where | Notes |
|---|---|---|
| `OPENAI_API_KEY` | Railway, GitHub secret, local `.env` | Rotate: create a new key in OpenAI → set in Railway + GitHub → redeploy → delete old key |
| `DATABASE_URL` | Railway (from Postgres) | SQLite locally |
| `CORS_ORIGINS` | Railway | Must include the web URL (and any custom domain) |
| `ADMIN_TOKEN` | Railway | Bearer token for `/api/admin/stats`; empty = off |
| `DAILY_LLM_CALL_CAP` | Railway | Default 2000/day. Lower it if spend spikes |
| `SENTRY_DSN`, `APP_ENV=production` | Railway | Error tracking; empty = off |
| `NEXT_PUBLIC_API_URL` | Vercel | The Railway API URL. Baked in at build: redeploy web after changing |
| `NEXT_PUBLIC_SENTRY_DSN`, `NEXT_PUBLIC_APP_ENV` | Vercel | Browser error tracking; empty = off |

## When something's wrong

| Symptom | Check | Fix |
|---|---|---|
| "Couldn't reach the kitchen brain" | Railway logs for `OpenAI call failed` | 401 → key revoked/expired, rotate. 429 → OpenAI quota/billing |
| Everything LLM fails after many users | Logs for `Daily LLM cap reached` | Cap reached (resets 00:00 UTC). Raise `DAILY_LLM_CALL_CAP` only if spend is OK |
| Web loads, every request fails | Browser console: CORS error? | Add the web origin to `CORS_ORIGINS` |
| OpenAI bill jumps | OpenAI usage page; `/api/admin/stats` | Lower `DAILY_LLM_CALL_CAP`, tighten `RATE_LIMIT`; set a hard monthly limit in OpenAI billing |
| Errors you didn't see | Sentry (once DSN is set) | |

## Costs to watch

- OpenAI: runtime `gpt-5.4-mini`, capped by `DAILY_LLM_CALL_CAP`. Set a monthly budget
  limit in the OpenAI dashboard as the final backstop.
- Railway: usage-based (API + Postgres). Vercel: Hobby tier.
- Sentry: free tier; tracing is off (`traces_sample_rate=0`).
