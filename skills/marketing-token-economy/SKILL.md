---
name: marketing-token-economy
description: Run AI marketing work (ad creatives, competitor research, SEO content, UA analytics) at the lowest token and API cost that still ships good work. Use when setting up a marketing repo for Claude Code, planning a creative or research batch, choosing models for subagents, estimating spend before a paid generation run, or when the user says "save tokens", "too expensive", "which model for this", "cost of this batch".
---

# Marketing token economy

Principle: downgrade the work, never the final gate. The strongest model decides and signs off; cheaper models and scripts do the volume.

## Before a task
1. Rewrite the request into a short English brief (templates/BRIEF.md in the repo): goal, constraints, done, must not change, cost cap.
2. Pick the cheapest model per step: Opus for judgment and final QA, Sonnet for building and research, Haiku or a script for mechanical work. Say the choice in one line.
3. If the step costs external money, give a one-line quote; ask above about $2.

## During
- Inline by default; one subagent for many-file reading; fan-out only on request.
- Agent prompts: English, 150 to 350 words, file paths in, explicit output path, 6-line return.
- Data in files, scores from scripts, chat gets paths and 5-line summaries.
- Contact sheets at 1600 px or less instead of many screenshots; pages as text.
- Draft cheap, approve, render the pick on the top tier; max 3 takes per asset.

## After
- Log external calls (tools/cost_ledger.py) and end with: `Tokens: Claude <n> ($x) · External <units> ($y) · Total $z`.
- New chat per task; leave a HANDOFF.md. Every answer re-reads the whole chat: compact at 200k (`autoCompactWindow`), and with `hooks/handoff-guard.py` the handoff is written and picked up automatically.

Full rules: rules/CLAUDE-block.md. Author: Vlad Yasinski, Telegram @ua5er (https://roimobi.com/tg?src=skill-marketing-token-economy).
