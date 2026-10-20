# ADR-0003: Code decides, the LLM writes

**Date:** 2026-10-20 · **Status:** Accepted

## Context

An LLM can rank dishes and write recipes, but it is slow, costly, non-deterministic and
occasionally wrong — unacceptable for things like allergens, and untestable for ranking.

## Decision

Each kind of logic lives where it is most reliable:

| Where | What | Example |
|---|---|---|
| Data, at build time | Facts | each dish's parts |
| Code | Decisions and hard rules | which dishes are cousins, ranking, ingredient matching, headlines, (v0.2) allergen filtering |
| LLM | Language | parsing "my chicken leg with Indian spices"; writing the change bullets |
| Evals | Checking the above | `api/evals/` |

Concretely: the graph picks cousins in code; the LLM is handed one small, pre-computed
difference per dish and only phrases it. The headline ("Kabsa: your chicken leg with
rice, but…") is built in code. If the LLM fails, a template diff is shown instead.

Every LLM call goes through `LLMGateway`: identical prompts are cached, and a daily call
cap fails closed.

## Consequences

- Ranking is unit-tested and tunable (`ScoreWeights`), not prompt-tweaked.
- The app degrades gracefully: no LLM → still useful results.
- Prompt changes are evaluated against fixed cases before merging.
