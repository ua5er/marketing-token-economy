# Marketing Token Economy

Rules, agents, a usage hook and a cost ledger for running AI marketing work (ad creatives, competitor research, SEO content, UA analytics) with Claude Code and external models at the lowest cost that still ships good work.

This is the setup I use every day for paid acquisition and growth work. It came out of real production: static and video ad studios, competitor ad-library research, SEO sites and BI. The rules are plain files. Drop them into a repo and the agent follows them.

## The core idea

**Downgrade the work, never the final gate.** The expensive model decides and signs off. Cheaper models and scripts do the volume. External models draft images and copy variants cheaply, and only the approved pick is rendered on the top tier.

## What is inside

| Path | What it does |
|---|---|
| `rules/CLAUDE-block.md` | Drop-in block for `CLAUDE.md` / `AGENTS.md`: language routing, model routing, orchestration, token hygiene, money rules |
| `agents/` | Four subagents with fixed models: `critic` (Opus), `builder` and `researcher` (Sonnet), `file-ops` (Haiku) |
| `hooks/usage-guard.py` | Claude Code hook + status line: cost of every answer at API list prices, plan usage, warnings at 80% of the weekly or 5-hour window |
| `hooks/handoff-guard.py` | Claude Code hook: at 150k / 300k / 500k context or after an idle hour, the agent writes a HANDOFF file and tells you to open a new chat; the next chat in the same folder picks the handoff up by itself |
| `tools/cost_ledger.py` | Log every external call (images, TTS, video, scraping) and print a cost line per task |
| `templates/` | English brief, handoff doc, module card |
| `docs/cost-reference.md` | Where money actually goes in creative production and research, with the mistakes that burned the most |
| `skills/marketing-token-economy/SKILL.md` | The same method as an agent skill |

## Ten rules that save the most

1. **Talk in your language, prompt in English.** Dictated requests get rewritten into a short English brief before any agent or external model sees them.
2. **Cheapest model per task, set explicitly.** Opus for judgment (strategy, money, final QA), Sonnet for building and research, Haiku or a script for mechanical work. Premium models only when a human picks them.
3. **Inline by default.** One subagent when the job means reading many files. A fan-out only when someone asks for it.
4. **Agent prompts are short.** English, 150 to 350 words, inputs as file paths, an explicit output path, a return of 6 lines or less. Never paste datasets into a prompt.
5. **Data lives in files, scripts compute scores.** The chat gets paths and five-line summaries, not tables.
6. **Look at contact sheets, not single files.** One image of 20 thumbnails at 1600 px or less instead of 20 screenshots. Read pages as text, not screenshots.
7. **Draft cheap, approve, render once.** Max 3 takes per asset, then one edit with a reference image.
8. **Quote before you spend.** One cost line before any paid batch; ask a human above about $2.
9. **Short chats, automatic handoffs.** Every answer re-reads the whole chat from cache, so a chat at 400k context costs about 3x one at 130k for the same answer. Compact at 200k, hand off through a HANDOFF file and start a new chat. Resuming a long idle chat re-caches the whole context.
10. **Count finished results, not started jobs.** Checking a workflow by started entries once re-ran research three times and burned about 100M tokens.

## Install

```bash
git clone https://github.com/ua5er/marketing-token-economy
cat marketing-token-economy/rules/CLAUDE-block.md >> your-repo/CLAUDE.md
mkdir -p your-repo/.claude/agents && cp marketing-token-economy/agents/*.md your-repo/.claude/agents/
cp marketing-token-economy/hooks/*.py ~/.claude/hooks/
```

Hook wiring for `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [{"hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/usage-guard.py stop", "timeout": 10}]}],
    "UserPromptSubmit": [
      {"hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/usage-guard.py prompt", "timeout": 10}]},
      {"hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/handoff-guard.py prompt", "timeout": 10}]}
    ],
    "SessionStart": [{"hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/handoff-guard.py start", "timeout": 10}]}]
  },
  "autoCompactWindow": 200000,
  "statusLine": {"type": "command", "command": "python3 ~/.claude/hooks/usage-guard.py status", "padding": 0, "refreshInterval": 60}
}
```

## Short chats without discipline

Measured on about 57,000 answers in my own Claude Code logs: the median answer re-read 336k tokens of context, the slowest 10% over 764k. Cache reads were 97% of all tokens. Keeping the context under 200k would cut those re-reads by about half (an upper bound: the compaction summary adds some back).

Two settings do it without relying on willpower:

- `"autoCompactWindow": 200000` in `~/.claude/settings.json` (minimum 100000) makes Claude Code compact at 200k instead of near the end of a 1M window. `/autocompact` sets it per model.
- `handoff-guard.py` fires when the context passes 150k, 300k and 500k, or when a big chat sat idle past the one-hour cache. The agent writes `~/.claude/handoffs/<folder>/HANDOFF-<time>-<session>.md` (goal, done, state, files, next steps, open questions, constraints) before it answers and ends the reply with one line telling you to open a new chat. A new chat in the same folder gets the newest handoff path at start (only the path, not the file) and reads it when your first message continues that work. Each step fires once per chat.

Cost ledger:

```bash
python3 tools/cost_ledger.py log --task banner-batch-07 --provider openai --model gpt-image-1-mini --units 12 --usd 0.18
python3 tools/cost_ledger.py report --task banner-batch-07
```

Prices in `usage-guard.py` are public list prices at the time of writing. Check your provider's pricing page and edit the `PRICES` table.

## Related

- [user-acquisition-skills](https://github.com/ua5er/user-acquisition-skills): agent skills for UA, creative testing, paywalls and web2app funnels
- [web2web-bi-board](https://github.com/ua5er/web2web-bi-board): open-source BI board for subscription web funnels

## Author

Vlad Yasinski, growth and user acquisition lead. [roimobi.com](https://roimobi.com) · Telegram [@ua5er](https://roimobi.com/tg?src=token-economy) · [LinkedIn](https://www.linkedin.com/in/vlad-yasinski-ua5er/)

MIT licence.
