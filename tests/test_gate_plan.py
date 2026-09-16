from datetime import date

from outboundqa.gate import daily_domain_guard, decide
from outboundqa.plan import new_contacts_for, simulate, steady_state

ME = "me@sender.com"


def msg(frm, at, subject="s", body="...", **kw):
    return {"from": frm, "at": at, "subject": subject, "body": body, **kw}


def test_no_reply_and_due_sends_first_follow_up():
    d = decide([msg(ME, "2026-09-08T13:00:00")], ME, date(2026, 9, 12))
    assert d.send and d.step == 1


def test_not_due_yet():
    d = decide([msg(ME, "2026-09-10T13:00:00")], ME, date(2026, 9, 12))
    assert not d.send and "not due" in d.reason


def test_any_reply_closes_even_a_no():
    thread = [msg(ME, "2026-09-01T13:00:00"), msg("x@co.com", "2026-09-02T09:00:00", body="no thanks")]
    assert not decide(thread, ME, date(2026, 9, 20)).send


def test_reply_from_a_colleague_also_closes():
    thread = [msg(ME, "2026-09-01T13:00:00"), msg("assistant@co.com", "2026-09-02T09:00:00", body="Looping in Dana")]
    assert "replied" in decide(thread, ME, date(2026, 9, 20)).reason


def test_out_of_office_waits_for_return_plus_grace():
    thread = [msg(ME, "2026-09-10T13:00:00"),
              msg("x@co.com", "2026-09-10T13:01:00", subject="Automatic reply",
                  body="I'm out of the office and back on September 21, 2026.")]
    assert not decide(thread, ME, date(2026, 9, 22)).send
    assert decide(thread, ME, date(2026, 9, 23)).send


def test_bounce_closes_permanently():
    thread = [msg(ME, "2026-09-01T13:00:00"),
              msg("mailer-daemon@googlemail.com", "2026-09-01T13:00:05", subject="Delivery Status Notification (Failure)")]
    assert "bounced" in decide(thread, ME, date(2026, 9, 30)).reason


def test_sequence_ends_after_two_follow_ups():
    thread = [msg(ME, "2026-09-01T13:00:00"), msg(ME, "2026-09-05T13:00:00"), msg(ME, "2026-09-10T13:00:00")]
    assert "finished" in decide(thread, ME, date(2026, 9, 30)).reason


def test_domain_guard():
    kept = daily_domain_guard(["a@x.com", "b@x.com", "c@y.com"], ["z@y.com"])
    assert kept == ["a@x.com"]


def test_volume_math():
    assert round(steady_state(18, reply_rate=0.0, bounce_rate=0.0)) == 54
    assert new_contacts_for(50) == 17
    rows = simulate(10, days=12, reply_rate=0, bounce_rate=0)
    assert rows[0]["total"] == 10 and rows[-1]["total"] == 30
