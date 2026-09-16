from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .gate import decide
from .io import read_drafts
from .lint import lint, load_rules
from .plan import new_contacts_for, simulate, steady_state


def cmd_lint(args) -> int:
    drafts = read_drafts(args.drafts)
    report = lint(drafts, load_rules(args.rules))
    for f in sorted(report.findings, key=lambda f: (f.draft_id, f.level, f.rule)):
        print(f"{f.draft_id:>6}  {f.level:<4}  {f.rule:<22} {f.detail}")
    print(json.dumps(report.summary(), indent=2))
    return 1 if report.blocked_ids() and args.strict else 0


def cmd_gate(args) -> int:
    threads = json.loads(Path(args.threads).read_text())
    today = date.fromisoformat(args.today) if args.today else date.today()
    for t in threads:
        d = decide(t["messages"], args.me, today)
        flag = "SEND" if d.send else "hold"
        print(f"{flag:<5} {t['to']:<32} {d.reason}")
    return 0


def cmd_plan(args) -> int:
    if args.target:
        n = new_contacts_for(args.target, reply_rate=args.reply_rate)
        print(f"To stay near {args.target} sends/day, add {n} new contacts/day "
              f"(steady state {steady_state(n, reply_rate=args.reply_rate):.1f}).")
        args.new = n
    print(f"{'day':>4} {'new':>5} {'follow-ups':>11} {'total':>7}")
    for r in simulate(args.new, args.days, reply_rate=args.reply_rate):
        print(f"{r['day']:>4} {r['new']:>5} {r['follow_ups']:>11} {r['total']:>7}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="outboundqa", description="Checks to run before any outbound send.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    l = sub.add_parser("lint", help="check a batch of drafts")
    l.add_argument("drafts", type=Path, help="CSV, JSON or JSONL with id,to,subject,body")
    l.add_argument("--rules", type=Path)
    l.add_argument("--strict", action="store_true", help="exit 1 if any draft is blocked")
    l.set_defaults(func=cmd_lint)

    g = sub.add_parser("gate", help="decide which threads may get a follow-up today")
    g.add_argument("threads", type=Path)
    g.add_argument("--me", required=True, help="your sending address")
    g.add_argument("--today")
    g.set_defaults(func=cmd_gate)

    p = sub.add_parser("plan", help="daily send volume for a sequence")
    p.add_argument("--new", type=int, default=18, help="new contacts per day")
    p.add_argument("--target", type=float, help="solve for new contacts given a daily send target")
    p.add_argument("--days", type=int, default=15)
    p.add_argument("--reply-rate", type=float, default=0.05)
    p.set_defaults(func=cmd_plan)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
