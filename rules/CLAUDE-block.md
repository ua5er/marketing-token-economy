## Token economy (marketing work)

### Language
- Talk to the owner in their language. Everything sent to other models (subagent and workflow prompts, briefs, external-model prompts, handoff notes) is in English.
- Requests are often dictated: long, repetitive, with recognition errors. Rewrite each into a short English brief (goal, constraints, what "done" looks like, what must not change), fix obvious recognition errors from context, and pass the brief, not the dictation, to agents. Keep `docs/GLOSSARY.md` of product terms and their spoken forms.
- Ask only when two readings lead to different work.

### Models
- The owner picks the main chat model. Never switch it. Never start helpers on the scarcest premium model unless the owner asks.
- Set the model on every agent call: Opus for judgment (strategy, money, security, final QA, experiment design), Sonnet for implementation and research, Haiku or a script for mechanical work.
- When plan usage is above 80% of a window, move helpers to Sonnet or Haiku and say so in one line.

### Orchestration: downgrade the work, never the final gate
| Work | Who |
|---|---|
| Positioning, approach pick, hooks, final copy, art direction, final QA | main thread |
| Independent sign-off of a batch (once per batch) | `critic` (Opus) |
| HTML/Figma build of banners, posts, layouts | `builder` (Sonnet) |
| Competitor and account research, data processing | `researcher` (Sonnet) + scripts |
| Renames, size checks, export packs, contact sheets | `file-ops` (Haiku) or a script |
| Image drafts, copy variants, tagging, glance panels | external models through one wrapper with a ledger |

Draft cheap, have the top model approve, render the final on the top tier.

### Agent prompts
- English, 150 to 350 words, inputs as file paths, an explicit output path and schema, return 6 lines or less.
- Never paste datasets into a prompt. Background agents stop when the turn ends, so keep the turn busy or run them in the foreground.

### Token hygiene
- Inline work by default; one agent when the job means reading many files; a fan-out only on request.
- One chat per task; start a new chat after the first compaction or when the task changes; hand off through `HANDOFF.md`.
- When the handoff hook asks (150k / 300k / 500k context or an idle hour), write the HANDOFF file it names before answering and end the reply with one line telling the owner to open a new chat. In a new chat, read the handoff the start hook points to when the first message continues that work.
- When a task is finished and the chat is already big, suggest a new chat even without the hook. Delegate bulk reading to subagents so the main chat stays small.
- Enable only the connectors the task needs.
- Batch independent tool calls; load deferred tool schemas in one call; batch predictable browser clicks.
- Read pages as text, not screenshots; screenshots at 0.4 to 0.6 scale; contact sheets at 1600 px or less for many images.
- Data goes to files, scripts compute scores, chat gets paths and 5-line summaries.
- Do not re-read files you just wrote; edit with diffs.
- Web search only when model knowledge is not enough.
- When checking a workflow, count finished results, not started entries.
- Delete per-agent worktrees and render scratch right after use.

### Money
- External API keys are real money. Never print keys; use a gateway or env file.
- Quote one cost line before any paid batch; ask the owner above about $2.
- Max 3 takes per generated asset, then one edit with a reference image. Generated images carry no text; copy stays in live text layers.
- Log every external call; end each task with: `Tokens: Claude <n> ($x) · External <units> ($y) · Total $z`.
