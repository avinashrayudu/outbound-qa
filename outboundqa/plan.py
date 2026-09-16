"""Send-volume planner.

With multi-touch sequences, daily volume is not the number of new people.
Every new contact sends again on day +4 and day +9 unless they reply, so the
daily total climbs for about a week and then levels off near
new_per_day × (1 + sum of follow-up survival rates).
"""
from __future__ import annotations

import math


def simulate(new_per_day: int, days: int = 20, offsets: tuple[int, ...] = (4, 9),
             reply_rate: float = 0.05, bounce_rate: float = 0.02,
             business_days_only: bool = True) -> list[dict]:
    """Day-by-day sends. Offsets are counted in send days."""
    keep = 1 - reply_rate - bounce_rate
    schedule = [0.0] * (days + max(offsets) + 1)
    rows = []
    for d in range(days):
        new = new_per_day
        schedule[d] += new
        for step, off in enumerate(offsets, start=1):
            schedule[d + off] += new * keep ** step
        rows.append({"day": d + 1, "new": new, "follow_ups": round(schedule[d] - new, 1),
                     "total": round(schedule[d], 1)})
    return rows


def steady_state(new_per_day: float, offsets=(4, 9), reply_rate=0.05, bounce_rate=0.02) -> float:
    keep = 1 - reply_rate - bounce_rate
    return new_per_day * (1 + sum(keep ** i for i in range(1, len(offsets) + 1)))


def new_contacts_for(target_total: float, offsets=(4, 9), reply_rate=0.05, bounce_rate=0.02) -> int:
    """Largest whole number of new contacts per day that keeps steady-state sends at or under the target."""
    per_new = steady_state(1, offsets, reply_rate, bounce_rate)
    return math.floor(target_total / per_new)
