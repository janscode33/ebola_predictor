# DRC Ebola Spatial Forecasting

## Summary

Goal: learn spatial epidemic forecasting properly, with a real deployable
output, using DRC Ebola data as the testbed.

Two components, one shared foundation:

| | Audit Pipeline | Magnitude Predictor |
|---|---|---|
| **What** | Independently scores INRB/UMIE's live invasion-probability forecasts (2026 outbreak) against what actually happens | From-scratch model predicting probability a health zone exceeds case thresholds (2/5/10/20) next month |
| **Data** | Live 2026 outbreak, scraped daily from the public dashboard | Historical 2018–2020 Kivu outbreak |
| **Validated against** | Ground truth as it arrives | Munday et al.'s published expert-elicitation benchmark |
| **Status** | Live — daily scraper deployed, verified against the real dashboard | Not started — crosswalk is next |

**Shared infrastructure (Phase 0):** health-zone name crosswalk, contiguity
graph, clean ingestion pipeline, scoring harness (Brier decomposition,
rolling-origin backtesting). Both components sit on top of this; it's built
once.

## Need Statement

Health-zone-level Ebola spread forecasts already exist — INRB/UMIE runs one
operationally for the current outbreak, and Munday et al. academically
validated spatial models against the 2018–2020 outbreak. But two gaps
remain. First, no one independently tracks whether INRB's live forecasts
are actually accurate once published — a real-time public tool's track
record goes unverified by default. Second, existing spatial models estimate
the probability a zone gets *seeded* with a case (introduction), not the
probability an outbreak there grows *large* (establishment) — a distinct
question that matters more for resource allocation. This project fills
both gaps: an independent auditor scoring INRB's public forecasts against
outcomes, and a magnitude-threshold model benchmarked against the one
existing academic baseline for this exact question.

**Scope note:** personal learning project, not an operational tool —
outputs would carry that label if ever shared publicly, given the live
humanitarian context.
