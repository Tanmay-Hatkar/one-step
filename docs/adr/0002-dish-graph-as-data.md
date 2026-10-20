# ADR-0002: The dish graph is reviewed data on a closed vocabulary

**Date:** 2026-10-20 · **Status:** Accepted

## Context

"One step away" needs dishes broken into comparable parts. Free-text recipes can't be
compared reliably; processing a 2M-recipe dataset would take weeks before anything ships.

## Decision

- Every dish is described with a **closed vocabulary** (`api/app/models/vocab.py`):
  family, protein, starch, techniques, equipment, flavors, allergens. Pydantic enforces
  it, including in the LLM's structured output — the model cannot invent a technique.
- v0.1 uses a **150-dish seed catalog generated once by an LLM** (`scripts/generate_dishes.py`),
  committed as `api/data/dishes.json` and reviewed like code. `test_catalog.py` checks it
  on every CI run (unique ids, family coverage, allergen sanity, the founding scenario).
- The catalog lives in a JSON file, loaded into memory. It moves to Postgres when it
  grows past what a file comfortably holds (v1.0, real recipe dataset).

## Consequences

- Distance between dishes is plain, testable code (`GraphService`).
- Vocabulary changes are schema changes: regenerate or migrate the catalog.
- Seed data inherits LLM errors; evals and catalog tests are the guard.
