# outbound-qa

![tests](https://github.com/avinashrayudu/outbound-qa/actions/workflows/tests.yml/badge.svg)

Three checks to run before any cold email goes out:

1. **`lint`** checks every draft, then the batch as a whole.
2. **`gate`** decides which threads may get a follow-up today.
3. **`plan`** shows what your daily send volume will actually be once follow-ups stack up.

No API keys, and no dependencies beyond PyYAML.

```bash
pip install -e ".[dev]"
python -m outboundqa lint examples/drafts.jsonl
python -m outboundqa gate examples/threads.json --me me@sender.com --today 2026-09-15
python -m outboundqa plan --target 50
```

## Why

A word count and a spam-word list catch the obvious problems. They miss the three that actually hurt a sender:

- **Emails that each pass every rule but read like the same template.** You only see it when you put them side by side, and a prospect at the same company sees it too.
- **Follow-ups sent on top of a reply.** Mailbox search previews often show only the oldest messages in a thread, so a recent "not now" is easy to miss.
- **Volume that creeps up.** Every new contact comes back on day 4 and day 9, so 18 new contacts a day turns into roughly 50 sends a day within two weeks.

## lint

Per-draft rules, configurable in `outboundqa/rules.yaml`:

| rule | blocks send? | why |
|---|---|---|
| `role_inbox` | yes | `info@`, `orders@` and similar can't carry a personal note |
| `word_count` | yes | 50 to 125 words by default |
| `banned_phrase` | yes | "hope this finds you well", "circle back", "leverage"... |
| `envelope_opener` | yes | openers that announce the email ("I'm writing about...") instead of saying something |
| `weak_closer` | yes | subjectless scheduling fragments like "Whenever suits you." |
| `too_many_metrics` | yes | one number per email; three numbers read like a resume |
| `self_focused` | yes | "I/my" appearing more often than "you/your" |
| `links` | yes | no links in a first touch |
| `fake_reply_subject` | yes | `Re:` on a first touch |
| `em_dash` | yes | house style |
| `subject_case`, `reading_grade`, `flat_rhythm`, `one_line_paragraphs` | warn | for a human to look at |

The greeting line and the sign-off are stripped before checking, so "Hi Maria," and "Avinash" don't count as template text.

Batch rules:

| rule | what it catches |
|---|---|
| `repeated_opener` / `repeated_closer` | The same first or last four words in more than 20% of the batch |
| `copied_sentence` | A sentence of five or more words that appears word for word in two different emails |
| `same_company_same_day` | More than one email to the same domain in one send |

Output on the sample batch (trimmed):

```
    d2  fail  banned_phrase          i hope this email finds you well
    d2  fail  envelope_opener        I hope this email finds you well.
    d2  fail  role_inbox             info@brightbotanicals.com
    d2  fail  self_focused           you=3 I=5
    d2  fail  too_many_metrics       60%, 95%, 40%, 15
    d2  fail  weak_closer            Whenever suits you.
    d3  fail  repeated_opener        'saw kind grain's granola...' used in 2 of 5 emails
    d3  fail  same_company_same_day  2 emails to kindgrain.co
    d4  warn  copied_sentence        same as in d3: Saw Kind Grain's granola go from two SKUs to five on Faire this summer.
{ "checked": 5, "blocked": 3, "ready": 2 }
```

Use `--strict` in a scheduled job to exit non-zero when anything is blocked.

## gate

Give it full threads (`examples/threads.json`) and your sending address:

```
SEND  maria@northfieldfoods.com        follow-up 1 due since 2026-09-12; no reply in thread
hold  leo@kindgrain.co                 leo@kindgrain.co replied; this thread is a conversation now, not a sequence
hold  sam@saltsnacks.com               out of office; wait until 2026-09-23
hold  ivy@evergreenpaws.com            address bounced; contact is closed for good
SEND  omar@coastalsips.com             follow-up 2 due since 2026-09-11; no reply in thread
```

The rules, in order:

1. A bounce closes the contact for good.
2. Any reply from anyone other than you closes the thread. That includes a plain "no", an assistant, or a forward.
3. An out-of-office message holds the thread until the return date it mentions, plus two days. If it gives no date, the hold lasts a week.
4. If you replied by hand, the thread is yours to handle.
5. Follow-ups go out on day 4 and day 9 after the first touch, and never more than two.

`daily_domain_guard()` drops any address at a company that already got an email today, counting follow-ups too.

## plan

```
$ python -m outboundqa plan --target 50 --days 12
To stay near 50.0 sends/day, add 17 new contacts/day (steady state 47.5).
 day   new  follow-ups   total
   1    17         0.0    17.0
   5    17        15.8    32.8
  10    17        30.5    47.5
```

The steady state is `new × (1 + keep + keep²)`, where `keep` is the share of contacts that neither replied nor bounced.

## Layout

```
outboundqa/lint.py     per-draft and batch checks
outboundqa/gate.py     reply gate and daily domain guard
outboundqa/plan.py     volume simulation
outboundqa/text.py     sentence, word, readability helpers
outboundqa/rules.yaml  every threshold and phrase list
examples/              sample drafts and threads (people and companies are made up)
```
