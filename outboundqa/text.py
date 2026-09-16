"""Small text helpers. No NLP library needed for any of this."""
from __future__ import annotations

import re
import statistics

WORD_RE = re.compile(r"[A-Za-z0-9'’$%.,-]+")
SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")
METRIC_RE = re.compile(r"(\$\s?\d[\d,.]*\s?[kKmM]?|\b\d[\d,.]*\s?%|\b\d+x\b|\b\d{2,}[\d,]*\b)")
LINK_RE = re.compile(r"(https?://|www\.)\S+|\b[a-z0-9-]+\.(com|io|co|ai|net|org)\b", re.I)
GREETING_RE = re.compile(r"^(hi|hello|hey|dear|good (morning|afternoon))\b", re.I)


def core(body: str) -> str:
    """The body without the greeting line and the sign-off.

    "Hi Maria," and "Avinash" are the same in every email on purpose;
    they shouldn't count as a repeated opener or closer.
    """
    paras = paragraphs(body)
    if paras and GREETING_RE.match(paras[0]) and len(paras[0].split()) <= 4:
        paras = paras[1:]
    while paras and len(paras[-1].split()) <= 3 and not paras[-1].rstrip().endswith((".", "?", "!")):
        paras = paras[:-1]
    return "\n\n".join(paras)


def words(text: str) -> list[str]:
    return [w for w in WORD_RE.findall(text) if any(c.isalnum() for c in w)]


def sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text.strip())
    return [s.strip() for s in SENT_RE.split(flat) if s.strip()]


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def count_syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and not w.endswith(("le", "ee")) and n > 1:
        n -= 1
    return max(1, n)


def fk_grade(text: str) -> float:
    ws = words(text)
    ss = sentences(text) or [text]
    if not ws:
        return 0.0
    syl = sum(count_syllables(w) for w in ws)
    return round(0.39 * len(ws) / len(ss) + 11.8 * syl / len(ws) - 15.59, 1)


def sentence_spread(text: str) -> float:
    lengths = [len(words(s)) for s in sentences(text)]
    return round(statistics.pstdev(lengths), 1) if len(lengths) > 1 else 0.0


def pronoun_ratio(text: str) -> tuple[int, int]:
    low = f" {text.lower()} "
    you = len(re.findall(r"\b(you|your|yours|you're|you’re)\b", low))
    me = len(re.findall(r"\b(i|me|my|mine|i'm|i’m|i've|i’ve)\b", low))
    return you, me


def shape(text: str, n: int, from_end: bool = False) -> str:
    ss = sentences(text)
    if not ss:
        return ""
    s = ss[-1] if from_end else ss[0]
    ws = [w.lower().strip(".,!?") for w in words(s)]
    return " ".join(ws[:n])
