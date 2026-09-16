"""Reply gate for follow-ups.

Rule of thumb: when in doubt, don't send. A missed follow-up costs nothing.
A follow-up sent on top of someone's answer costs the relationship.

A thread is a list of messages: {"from": str, "at": ISO datetime, "subject": str, "body": str}.
Always pass the whole thread. Mailbox search previews often return only the
oldest few messages of a thread, which is exactly where a reply is not.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

OOO_RE = re.compile(r"(out of (the )?office|on (annual )?leave|away until|automatic reply|auto-?reply)", re.I)
RETURN_RE = re.compile(r"(?:back|return(?:ing)?)\s+(?:on\s+)?(\w+ \d{1,2}(?:, \d{4})?|\d{4}-\d{2}-\d{2})", re.I)
BOUNCE_RE = re.compile(r"(delivery status notification|undeliverable|mail delivery (failed|subsystem)|address not found)", re.I)


@dataclass
class Decision:
    send: bool
    step: int | None     # which follow-up this would be (1 or 2)
    reason: str


def _dt(v: str) -> datetime:
    return datetime.fromisoformat(v.replace("Z", "+00:00")).replace(tzinfo=None)


def _return_date(body: str, year: int) -> date | None:
    m = RETURN_RE.search(body or "")
    if not m:
        return None
    raw = m.group(1)
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%B %d", "%b %d, %Y", "%b %d"):
        try:
            d = datetime.strptime(raw, fmt)
            return d.date() if "%Y" in fmt else d.replace(year=year).date()
        except ValueError:
            continue
    return None


def decide(thread: list[dict], me: str, today: date,
           offsets: tuple[int, ...] = (4, 9), ooo_grace_days: int = 2) -> Decision:
    if not thread:
        return Decision(False, None, "empty thread; nothing to follow up on")
    me = me.lower()
    msgs = sorted(thread, key=lambda m: _dt(m["at"]))
    mine = [m for m in msgs if m["from"].lower() == me]
    others = [m for m in msgs if m["from"].lower() != me]

    if not mine:
        return Decision(False, None, "you never wrote in this thread")

    for m in others:
        text = f"{m.get('subject', '')} {m.get('body', '')}"
        if BOUNCE_RE.search(text) or m["from"].lower().startswith(("mailer-daemon", "postmaster")):
            return Decision(False, None, "address bounced; contact is closed for good")

    real_replies = [m for m in others if not OOO_RE.search(f"{m.get('subject', '')} {m.get('body', '')}")]
    if real_replies:
        who = real_replies[0]["from"]
        return Decision(False, None, f"{who} replied; this thread is a conversation now, not a sequence")

    if any(m for m in mine[1:] if _dt(m["at"]) > _dt(mine[0]["at"]) and m.get("manual")):
        return Decision(False, None, "you replied by hand; leave it to you")

    for m in others:  # only auto-replies left
        back = _return_date(m.get("body", ""), today.year)
        if back is None:
            back = _dt(m["at"]).date() + timedelta(days=7)
        if today < back + timedelta(days=ooo_grace_days):
            return Decision(False, None, f"out of office; wait until {back + timedelta(days=ooo_grace_days)}")

    sent = len(mine)
    if sent > len(offsets):
        return Decision(False, None, f"{sent} messages already sent; sequence is finished")
    first = _dt(mine[0]["at"]).date()
    due = first + timedelta(days=offsets[sent - 1])
    if today < due:
        return Decision(False, sent, f"follow-up {sent} not due until {due}")
    return Decision(True, sent, f"follow-up {sent} due since {due}; no reply in thread")


def daily_domain_guard(planned: list[str], already_sent_today: list[str]) -> list[str]:
    """Drop any address whose company domain already got an email today."""
    used = {a.split("@")[-1].lower() for a in already_sent_today}
    keep = []
    for addr in planned:
        dom = addr.split("@")[-1].lower()
        if dom in used:
            continue
        used.add(dom)
        keep.append(addr)
    return keep
