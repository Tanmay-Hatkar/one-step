# ADR-0005: Public dish pages for search

**Date:** 2026-11-23 · **Status:** Accepted

## Context

People only reach One Step through a link. The 718 catalog dishes already had pages, but
they loaded in the browser, so search engines saw an empty shell. Search traffic is how
food sites are found and paid for (ads, affiliate links). This is the project's way of
learning that.

## Decision

- `/dish/[id]` renders on the server: name, summary, recipe (when we have one), and
  **"If you can cook X, you're one step from…"**. That list is computed in code by
  `GraphService.related`: the same one-step rule as for a user's kitchen, with the page's
  dish as the anchor and diversified by region. No LLM, so it's free, deterministic and
  identical for every visitor.
- schema.org `Recipe` JSON-LD, canonical URL, and a description naming the nearest dishes.
- `/dishes` directory (every dish, by region), `sitemap.xml` (721 URLs), `robots.txt`
  (keeps `/k/` shared kitchens and `/saved` out of search).
- Data comes from the API (`GET /api/dishes`, `GET /api/dishes/{id}` now with `related`),
  cached for days. If the API is unreachable the page falls back to loading in the browser.

## Consequences

- Deploy the API before the web app: the sitemap and directory are built from it.
- Unknown dish ids show a `noindex` 404 page with HTTP 200 (streaming); fine for search.
- Next: submit the sitemap in Google Search Console (needs the site's owner to verify it).
