#!/usr/bin/env python3
"""Usage guard for Claude Code (all projects). Never blocks: any error exits 0 silently.

  usage-guard.py stop     Stop hook: after each answer, shows what the work cost at API list prices
                          (a calm line, only above a threshold), per model, for this chat.
  usage-guard.py prompt   UserPromptSubmit hook: once per chat warns when the chat runs on Fable (its
                          own small weekly bucket); tells Claude to keep helpers off Fable and, when the
                          plan's week or 5-hour window is nearly used, to prefer cheaper models.
  usage-guard.py status   statusLine: model, plan usage, chat cost; saves the plan usage for the hooks.

State lives in ~/.claude/state/usage-guard/. Transcripts are read incrementally (byte offsets).
Costs are estimates at public API list prices; on a subscription the work is included in the plan.
"""
import glob, json, os, sys, time

HOME = os.path.expanduser("~")
STATE = os.path.join(HOME, ".claude", "state", "usage-guard")
PLAN_FILE = os.path.join(STATE, "plan-usage.json")
SHOW_FROM_USD = 0.30          # answers cheaper than this print nothing
PLAN_PRESSURE = 80            # % of the 7-day or 5-hour window that counts as "nearly used"

# USD per million tokens: input, output, cache write 5 min, cache write 1 h, cache read.
PRICES = [
    ("fable-5-1", 10.0, 50.0, 12.5, 20.0, 1.00),
    ("fable-5",   10.0, 50.0, 12.5, 20.0, 1.00),
    ("fable",      8.0, 40.0, 10.0, 16.0, 0.20),
    ("mythos",     8.0, 40.0, 10.0, 16.0, 0.20),
    ("opus-5-5",   4.0, 20.0,  5.0,  8.0, 0.20),
    ("opus",       5.0, 25.0,  6.25, 10.0, 0.50),
    ("sonnet-5-5", 2.0, 10.0,  2.5,  4.0, 0.10),
    ("sonnet",     2.0, 10.0,  2.5,  4.0, 0.20),
    ("haiku-5-5",  0.10, 0.50, 0.125, 0.20, 0.01),
    ("haiku",      1.0,  5.0,  1.25, 2.0, 0.10),
]

def price(model):
    m = (model or "").lower()
    for key, *p in PRICES:
        if key in m:
            return p
    return PRICES[4][1:]  # unknown: price as Opus 5.5

def family(model):
    m = (model or "").lower()
    for f in ("fable", "mythos", "opus", "sonnet", "haiku"):
        if f in m:
            return f.capitalize()
    return "Other"

def cost(model, u):
    i, o, w5, w1, r = price(model)
    cc = u.get("cache_creation") or {}
    w1t = cc.get("ephemeral_1h_input_tokens", 0) or 0
    w5t = cc.get("ephemeral_5m_input_tokens", 0) or 0
    if not cc:
        w5t = u.get("cache_creation_input_tokens", 0) or 0
    return (i * (u.get("input_tokens", 0) or 0) + o * (u.get("output_tokens", 0) or 0)
            + w5 * w5t + w1 * w1t + r * (u.get("cache_read_input_tokens", 0) or 0)) / 1e6

def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default

def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)

def session_files(transcript):
    files = [transcript]
    base = transcript[:-6] if transcript.endswith(".jsonl") else transcript
    files += sorted(glob.glob(os.path.join(base, "subagents", "*.jsonl")))
    return files

def scan(session_id, transcript):
    """Adds new assistant messages since the last scan; returns the session state."""
    path = os.path.join(STATE, f"session-{session_id}.json")
    st = load(path, {"offsets": {}, "msgs": {}, "shown_usd": 0.0, "fable_warned": False})
    for f in session_files(transcript):
        try:
            size = os.path.getsize(f)
        except OSError:
            continue
        off = st["offsets"].get(f, 0)
        if off > size:
            off = 0
        if off == size:
            continue
        with open(f, "rb") as fh:
            fh.seek(off)
            chunk = fh.read()
        end = chunk.rfind(b"\n") + 1  # only whole lines; a half-written line is read next time
        for line in chunk[:end].splitlines():
            if b'"usage"' not in line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            m = d.get("message") or {}
            u = m.get("usage")
            if d.get("type") != "assistant" or not u or not m.get("id"):
                continue
            # The same response can be written several times; the last record per id wins.
            st["msgs"][m["id"]] = [m.get("model") or "", round(cost(m.get("model"), u), 6)]
        st["offsets"][f] = off + end
    st["_path"] = path
    return st

def totals(st):
    by = {}
    for model, c in st["msgs"].values():
        by[family(model)] = by.get(family(model), 0.0) + c
    return sum(by.values()), by

def usd(x):
    return f"${x:.2f}" if x < 10 else f"${x:.0f}"

def last_model(st, transcript):
    try:
        with open(transcript, "rb") as fh:
            fh.seek(max(0, os.path.getsize(transcript) - 400_000))
            for line in reversed(fh.read().splitlines()):
                if b'"assistant"' in line and b'"model"' in line:
                    d = json.loads(line)
                    if d.get("type") == "assistant" and not d.get("isSidechain"):
                        return (d.get("message") or {}).get("model", "")
    except Exception:
        pass
    return ""

def plan_usage():
    p = load(PLAN_FILE, {})
    if not p or time.time() - p.get("at", 0) > 6 * 3600:
        return None
    return p

def out(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))

def on_stop(inp):
    if inp.get("stop_hook_active"):
        return
    path0 = os.path.join(STATE, f"session-{inp['session_id']}.json")
    first = not os.path.exists(path0)
    st = scan(inp["session_id"], inp["transcript_path"])
    total, by = totals(st)
    if first and total > 20:
        st["shown_usd"] = total  # guard installed into a long-running chat: start counting from here
    turn = total - st.get("shown_usd", 0.0)
    if turn >= SHOW_FROM_USD:
        parts = " · ".join(f"{k} {usd(v)}" for k, v in sorted(by.items(), key=lambda kv: -kv[1]) if v >= 0.01)
        pl = plan_usage() or {}
        over = (pl.get("seven_day") or 0) >= 100 or (pl.get("five_hour") or 0) >= 100
        tail = "Plan limit reached: answers like this are billed as paid credits." if over else "Included in your subscription."
        msg = f"This answer ≈ {usd(turn)} at API list prices, whole chat ≈ {usd(total)} ({parts}). {tail}"
        st["shown_usd"] = total
        out({"systemMessage": msg})
    path = st.pop("_path")
    save(path, st)

def on_prompt(inp):
    st = scan(inp["session_id"], inp["transcript_path"])
    model = last_model(st, inp["transcript_path"])
    ctx, user = [], None
    if "fable" in model.lower():
        ctx.append("This chat runs on Fable, a scarce weekly bucket: do not start subagents, workflows or API helpers on Fable; use Opus/Sonnet/Haiku.")
        if not st.get("fable_warned"):
            user = "This chat runs on Fable, which has its own small weekly limit. For routine work, switch the chat model to Opus."
            st["fable_warned"] = True
    p = plan_usage()
    if p:
        week, five = p.get("seven_day"), p.get("five_hour")
        if (week or 0) >= PLAN_PRESSURE or (five or 0) >= PLAN_PRESSURE:
            ctx.append(f"Plan usage is high (7-day {week}%, 5-hour {five}%). Prefer Haiku/Sonnet for subagents, avoid large agent fan-outs, and say so before heavy work; for long text-only jobs offer the owner's API-key helpers (they cost real money: ask first).")
    path = st.pop("_path")
    save(path, st)
    if ctx or user:
        o = {}
        if user:
            o["systemMessage"] = user
        if ctx:
            o["hookSpecificOutput"] = {"hookEventName": "UserPromptSubmit", "additionalContext": " ".join(ctx)}
        out(o)

def on_status(inp):
    rl = inp.get("rate_limits") or {}
    week = (rl.get("seven_day") or {}).get("used_percentage")
    five = (rl.get("five_hour") or {}).get("used_percentage")
    if week is not None or five is not None:
        save(PLAN_FILE, {"at": time.time(), "seven_day": week, "five_hour": five,
                         "week_resets_at": (rl.get("seven_day") or {}).get("resets_at")})
    model = (inp.get("model") or {}).get("display_name") or ""
    bits = [model]
    if week is not None:
        bits.append(f"week {round(week)}%")
    if five is not None:
        bits.append(f"5h {round(five)}%")
    c = (inp.get("cost") or {}).get("total_cost_usd")
    if c:
        bits.append(f"chat ≈{usd(c)}")
    sys.stdout.write(" · ".join(b for b in bits if b))

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        inp = json.load(sys.stdin)
        {"stop": on_stop, "prompt": on_prompt, "status": on_status}[mode](inp)
    except Exception:
        pass
    sys.exit(0)

if __name__ == "__main__":
    main()
