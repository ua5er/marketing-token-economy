#!/usr/bin/env python3
"""Tiny cost ledger for external AI calls. Standard library only.

  cost_ledger.py log --task T --provider P --model M --units N --usd X [--note TEXT]
  cost_ledger.py report [--task T]

Rows go to ledger/usage.jsonl (override with COST_LEDGER=path).
"""
import argparse, json, os, sys, time
from collections import defaultdict

PATH = os.environ.get("COST_LEDGER", os.path.join("ledger", "usage.jsonl"))

def log(a):
    os.makedirs(os.path.dirname(PATH) or ".", exist_ok=True)
    row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "task": a.task, "provider": a.provider,
           "model": a.model, "units": a.units, "usd": round(a.usd, 4), "note": a.note or ""}
    with open(PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    print(f"logged {a.provider}/{a.model} {a.units} units ${a.usd:.4f}")

def report(a):
    if not os.path.exists(PATH):
        print("no ledger yet"); return
    by = defaultdict(lambda: [0.0, 0.0]); total = 0.0
    for line in open(PATH, encoding="utf-8"):
        r = json.loads(line)
        if a.task and r["task"] != a.task:
            continue
        k = f'{r["provider"]}/{r["model"]}'; by[k][0] += r["units"]; by[k][1] += r["usd"]; total += r["usd"]
    for k, (u, c) in sorted(by.items(), key=lambda x: -x[1][1]):
        print(f"{k:40s} {u:>10g} units  ${c:.4f}")
    print(f"External total: ${total:.4f}")

p = argparse.ArgumentParser(); s = p.add_subparsers(dest="cmd", required=True)
l = s.add_parser("log")
for n in ("task", "provider", "model"):
    l.add_argument("--" + n, required=True)
l.add_argument("--units", type=float, required=True); l.add_argument("--usd", type=float, required=True); l.add_argument("--note")
r = s.add_parser("report"); r.add_argument("--task")
a = p.parse_args(); {"log": log, "report": report}[a.cmd](a)
