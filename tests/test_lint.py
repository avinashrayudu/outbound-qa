import json
from pathlib import Path

from outboundqa import text as T
from outboundqa.io import read_drafts
from outboundqa.lint import Draft, check_draft, lint, load_rules

ROOT = Path(__file__).resolve().parents[1]
RULES = load_rules()


def rules_hit(d):
    return {f.rule for f in check_draft(d, RULES)}


def test_core_strips_greeting_and_signoff_but_keeps_real_closers():
    body = "Hi Maria,\n\nFirst point here.\n\nWhenever suits you.\n\nAvinash"
    assert T.core(body) == "First point here.\n\nWhenever suits you."


def test_metric_and_pronoun_helpers():
    assert len(T.METRIC_RE.findall("went from 60% to 95% and saved $12k")) == 3
    assert T.pronoun_ratio("I think your team and you") == (2, 1)


def test_good_sample_drafts_pass():
    drafts = {d.id: d for d in read_drafts(ROOT / "examples/drafts.jsonl")}
    report = lint(list(drafts.values()), RULES)
    assert "d1" not in report.blocked_ids()
    assert "d5" not in report.blocked_ids()


def test_bad_draft_hits_the_expected_rules():
    drafts = {d.id: d for d in read_drafts(ROOT / "examples/drafts.jsonl")}
    hit = rules_hit(drafts["d2"])
    assert {"banned_phrase", "role_inbox", "too_many_metrics", "self_focused", "weak_closer"} <= hit


def test_em_dash_and_fake_reply_subject():
    d = Draft("x", "a@b.com", "RE: hello", "Hi A,\n\nThis line has an em dash — right here. " * 6)
    hit = rules_hit(d)
    assert "em_dash" in hit and "fake_reply_subject" in hit


def test_envelope_opener():
    d = Draft("x", "a@b.com", "hello", "Hi A,\n\nI'm writing to ask about your team. " + "Your stores grew fast this year and you added three regions. " * 5)
    assert "envelope_opener" in rules_hit(d)


def test_batch_catches_template_residue_and_domain_collisions():
    body = ("Hi {n},\n\nNoticed your brand expanded into new grocery doors this quarter. "
            "Expansion usually brings a reorder tracking gap for your team. "
            "Stores that go quiet are hard to spot from a distributor report. "
            "A per-store weekly view fixes most of that for you. "
            "Is that on your list for this quarter?\n\nAvinash")
    drafts = [Draft(str(i), f"p{i}@{'same.com' if i < 2 else f'c{i}.com'}", "your new doors", body.format(n=i))
              for i in range(4)]
    report = lint(drafts, RULES)
    rules = {f.rule for f in report.findings}
    assert {"repeated_opener", "repeated_closer", "same_company_same_day", "copied_sentence"} <= rules


def test_json_and_csv_inputs(tmp_path):
    rows = [{"id": "a", "to": "x@y.com", "subject": "s", "body": "b"}]
    (tmp_path / "d.json").write_text(json.dumps(rows))
    (tmp_path / "d.csv").write_text("id,to,subject,body\na,x@y.com,s,b\n")
    assert read_drafts(tmp_path / "d.json")[0].to == read_drafts(tmp_path / "d.csv")[0].to
