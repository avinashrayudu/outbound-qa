"""Per-email and batch checks.

Mechanical rules catch the obvious problems. The batch checks catch the
problem that single-email rules never will: twenty emails that each pass,
but read like the same template once you put them side by side.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import text as T

DEFAULT_RULES = Path(__file__).with_name("rules.yaml")


def load_rules(path: Path | None = None) -> dict:
    return yaml.safe_load(Path(path or DEFAULT_RULES).read_text())


@dataclass
class Draft:
    id: str
    to: str
    subject: str
    body: str

    @property
    def domain(self) -> str:
        return self.to.split("@")[-1].lower() if "@" in self.to else ""


@dataclass
class Finding:
    draft_id: str
    rule: str
    detail: str
    level: str = "fail"   # fail blocks the send; warn is for a human to look at


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    checked: int = 0

    def blocked_ids(self) -> set[str]:
        return {f.draft_id for f in self.findings if f.level == "fail"}

    def summary(self) -> dict:
        by_rule = Counter(f.rule for f in self.findings)
        return {
            "checked": self.checked,
            "blocked": len(self.blocked_ids()),
            "ready": self.checked - len(self.blocked_ids()),
            "findings_by_rule": dict(by_rule.most_common()),
        }


ROLE_INBOX = re.compile(r"^(info|hello|hi|hey|sales|contact|team|support|admin|orders|founders|office)@")


def check_draft(d: Draft, rules: dict) -> list[Finding]:
    out: list[Finding] = []
    add = lambda rule, detail, level="fail": out.append(Finding(d.id, rule, detail, level))
    body = T.core(d.body)
    low = body.lower()

    if ROLE_INBOX.match(d.to.lower()):
        add("role_inbox", d.to)

    n = len(T.words(body))
    if not rules["words"]["min"] <= n <= rules["words"]["max"]:
        add("word_count", f"{n} words (want {rules['words']['min']}-{rules['words']['max']})")

    subj_words = len(T.words(d.subject))
    if subj_words > rules["subject"]["max_words"]:
        add("subject_length", f"{subj_words} words")
    if rules["subject"].get("require_lowercase") and d.subject != d.subject.lower():
        add("subject_case", d.subject, "warn")
    if d.subject.lower().startswith(("re:", "fwd:")):
        add("fake_reply_subject", d.subject)

    if "—" in body or "—" in d.subject:
        add("em_dash", "contains an em dash")

    for phrase in rules["banned_phrases"]:
        if phrase in low:
            add("banned_phrase", phrase)

    links = T.LINK_RE.findall(body)
    if len(links) > rules["max_links"]:
        add("links", f"{len(links)} link(s) in a first touch")

    metrics = T.METRIC_RE.findall(body)
    if len(metrics) > rules["max_metrics"]:
        add("too_many_metrics", ", ".join(metrics))

    you, me = T.pronoun_ratio(body)
    if me and you / me < rules["min_you_ratio"]:
        add("self_focused", f"you={you} I={me}")

    grade = T.fk_grade(body)
    if grade > rules["max_grade"]:
        add("reading_grade", f"grade {grade}", "warn")

    spread = T.sentence_spread(body)
    if spread < rules["min_sentence_spread"]:
        add("flat_rhythm", f"sentence length spread {spread}", "warn")

    paras = T.paragraphs(body)
    run = best = 0
    for p in paras:
        run = run + 1 if len(T.sentences(p)) == 1 else 0
        best = max(best, run)
    if best > rules["max_adjacent_one_liners"]:
        add("one_line_paragraphs", f"{best} single-sentence paragraphs in a row", "warn")

    ss = T.sentences(body)
    if ss:
        first = ss[0].lower()
        if any(re.search(p, first) for p in rules["envelope_openers"]):
            add("envelope_opener", ss[0])
        last = ss[-1].lower()
        if any(re.search(p, last) for p in rules["weak_closers"]):
            add("weak_closer", ss[-1])
    return out


def check_batch(drafts: list[Draft], rules: dict) -> list[Finding]:
    b = rules["batch"]
    n = b["shape_words"]
    out: list[Finding] = []
    total = len(drafts)
    if total < 2:
        return out

    for label, from_end, limit in (("opener", False, b["max_same_opener_share"]),
                                   ("closer", True, b["max_same_closer_share"])):
        shapes = {d.id: T.shape(T.core(d.body), n, from_end) for d in drafts}
        counts = Counter(shapes.values())
        for s, c in counts.items():
            if s and c / total > limit and c > 1:
                for did, sh in shapes.items():
                    if sh == s:
                        out.append(Finding(did, f"repeated_{label}",
                                           f"'{s}...' used in {c} of {total} emails"))

    # identical sentences across different emails are template residue
    seen: dict[str, str] = {}
    for d in drafts:
        for s in T.sentences(T.core(d.body)):
            key = s.lower()
            if len(T.words(s)) < 5:
                continue
            if key in seen and seen[key] != d.id:
                out.append(Finding(d.id, "copied_sentence", f"same as in {seen[key]}: {s}", "warn"))
            else:
                seen.setdefault(key, d.id)

    per_domain = Counter(d.domain for d in drafts if d.domain)
    for d in drafts:
        if per_domain[d.domain] > b["max_emails_per_domain"]:
            out.append(Finding(d.id, "same_company_same_day",
                               f"{per_domain[d.domain]} emails to {d.domain}"))
    return out


def lint(drafts: list[Draft], rules: dict | None = None) -> Report:
    rules = rules or load_rules()
    report = Report(checked=len(drafts))
    for d in drafts:
        report.findings += check_draft(d, rules)
    report.findings += check_batch(drafts, rules)
    return report
