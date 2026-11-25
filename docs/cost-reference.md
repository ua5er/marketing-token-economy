# Where the money goes (marketing production)

Figures are rough references from real runs in late 2026. Check current provider pricing.

## Creative production
- Image drafts on a cheap image model, final on the hero model. Max 3 takes per asset.
- A 30 to 60 second video ad with AI live shots: external cost mostly in video generation, about $1 per 5-second clip; TTS under $0.01. The rest is Claude tokens.
- Always run a dry-run quote before a paid batch.

## Competitor research (ad libraries)
- Scraping an ad library through an actor costs about $0.50 to $0.75 per 1,000 ads; a full run is $0.10 to $1.
- Collection and scoring on Sonnet plus scripts; synthesis on the main thread.
- An approach counts as "working" only with 2 or more independent signals and 2 or more advertisers. Ad-library data shows what survives, not spend, CTR or ROAS.

## Claude tokens
- Resuming a long idle chat re-caches the whole context, about $1 each time. One chat per task.
- `max_tokens` includes thinking, so long helper answers get cut. Split long jobs.
- The most expensive mistake: re-running a research workflow three times because it was checked by started entries, not finished results. About 100M tokens.

## Measuring
- Claude: `hooks/usage-guard.py` status line and per-answer cost, or `npx ccusage@latest session`.
- External: `tools/cost_ledger.py` with a provider balance check before and after.
