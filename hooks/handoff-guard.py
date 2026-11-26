#!/usr/bin/env python3
"""Handoff guard for Claude Code (all projects). Keeps chats short so the prompt cache stays cheap.
Never blocks: any error exits 0 silently.

  handoff-guard.py prompt   UserPromptSubmit: when the chat's context passes a step (150k, 300k, 500k)
                            or the chat sat idle past the cache lifetime, tells Claude to write a HANDOFF
                            file first and to tell the owner to start a new chat.
  handoff-guard.py start    SessionStart: if a fresh handoff exists for this folder, points the new chat at it.

Handoffs: ~/.claude/handoffs/<folder-slug>/HANDOFF-<yyyymmdd-hhmm>-<session8>.md
State:    ~/.claude/state/handoff-guard/
"""
import glob, json, os, sys, time

HOME = os.path.expanduser("~")
STATE = os.path.join(HOME, ".claude", "state", "handoff-guard")
HANDOFFS = os.path.join(HOME, ".claude", "handoffs")
STEPS = [150_000, 300_000, 500_000]   # context sizes that trigger a handoff
IDLE_SEC = 55 * 60                    # prompt cache lives about an hour
IDLE_MIN_CTX = 80_000                 # idle warning only for chats this big
FRESH_SEC = 3 * 24 * 3600             # handoffs older than this are not offered to new chats


def load(p, d):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return d


def save(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w") as f:
        json.dump(data, f)
    os.replace(p + ".tmp", p)


def slug(cwd):
    return (cwd or "unknown").strip("/").replace("/", "-") or "root"


def last_context(transcript):
    """Context size of the last main-thread answer, and when the chat last had activity."""
    try:
        size = os.path.getsize(transcript)
        with open(transcript, "rb") as fh:
            fh.seek(max(0, size - 600_000))
            lines = fh.read().splitlines()
    except Exception:
        return 0, None
    for line in reversed(lines):
        if b'"usage"' not in line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") != "assistant" or d.get("isSidechain"):
            continue
        u = (d.get("message") or {}).get("usage") or {}
        ctx = sum(u.get(k, 0) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
        ts = None
        try:
            from datetime import datetime
            ts = datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")).timestamp()
        except Exception:
            pass
        return ctx, ts
    return 0, None


def handoff_path(cwd, sid):
    return os.path.join(HANDOFFS, slug(cwd), f"HANDOFF-{time.strftime('%Y%m%d-%H%M')}-{sid[:8]}.md")


BRIEF = (
    "Write a handoff file at {path} BEFORE you answer (Write tool; create the folder if needed). "
    "English, under 60 lines, facts only: 1) goal of this chat; 2) what is done, with commits/URLs; "
    "3) current state and anything running or unverified; 4) key files with paths; 5) next steps in order; "
    "6) open questions for the owner; 7) constraints and owner preferences learned here. "
    "Then answer the owner's message as usual and end your reply with one line in the owner's language: "
    "\"{reason} Handoff saved: {path}. Open a new chat in this folder and it will pick it up.\" "
    "If this message is the last step of a task, finish it first and still write the handoff."
)


def on_prompt(inp):
    sid, tr, cwd = inp.get("session_id", "x"), inp.get("transcript_path", ""), inp.get("cwd", "")
    ctx, last_ts = last_context(tr)
    if not ctx:
        return
    sp = os.path.join(STATE, f"{sid}.json")
    st = load(sp, {"step": 0, "idle_at": 0})
    reason = None
    idle = last_ts and time.time() - last_ts > IDLE_SEC
    step = max([i + 1 for i, s in enumerate(STEPS) if ctx >= s] or [0])
    k = round(ctx / 1000)
    if step > st["step"]:
        st["step"] = step
        reason = f"Context is {k}k tokens and every answer re-reads all of it."
    elif idle and ctx >= IDLE_MIN_CTX and last_ts != st.get("idle_at"):
        st["idle_at"] = last_ts
        reason = f"This chat sat idle over an hour and the cache expired: this answer re-cached {k}k tokens."
    save(sp, st)
    if not reason:
        return
    path = handoff_path(cwd, sid)
    sys.stdout.write(json.dumps({
        "systemMessage": reason + " Writing a HANDOFF now; continue in a new chat.",
        "hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                               "additionalContext": BRIEF.format(path=path, reason=reason)},
    }, ensure_ascii=False))


def on_start(inp):
    if inp.get("source") not in (None, "startup", "clear"):
        return  # resume/compact keep their own context
    folder = os.path.join(HANDOFFS, slug(inp.get("cwd", "")))
    files = sorted(glob.glob(os.path.join(folder, "HANDOFF-*.md")), key=os.path.getmtime, reverse=True)
    sid = inp.get("session_id", "")
    files = [f for f in files if time.time() - os.path.getmtime(f) < FRESH_SEC and sid[:8] not in f]
    if not files:
        return
    newest = files[0]
    others = "" if len(files) == 1 else f" Older handoffs in {folder} ({len(files) - 1} more) if the newest does not match."
    sys.stdout.write(json.dumps({
        "systemMessage": f"Fresh handoff from a previous chat: {os.path.basename(newest)}",
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": (
            f"A previous chat in this folder left a handoff: {newest}. If the owner's first message continues "
            f"earlier work (\"continue\", \"next\", or it matches the handoff's topic), read that file first and "
            f"continue from its next steps without re-asking what is already settled. Ignore it for unrelated tasks.{others}")},
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        data = json.load(sys.stdin)
        {"prompt": on_prompt, "start": on_start}[sys.argv[1]](data)
    except Exception:
        pass
    sys.exit(0)
