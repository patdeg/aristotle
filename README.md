# Aristotle

> *"With Large Language Models, every child on Earth can have a personal Aristotle."*
> Patrick Deglon, *The Unscarcity Blueprint*, [Chapter 5: The Education of a Citizen](https://unscarcity.ai/a/chapter5)

**A personal AI mentor for your child, modelled after the AI Aristotle described in Chapter 5 of [*The Unscarcity Blueprint*](https://unscarcity.ai).**

Aristotle reads your child's grades from Canvas, finds what they're struggling with, and every week writes a Socratic-style practice worksheet in the voice of a warm, patient, ancient Greek tutor, every scenario tailored to the things *this specific kid* actually cares about. The worksheet arrives as a printable PDF. The answer key goes to you.

It's not a homework bot. It's a one-on-one tutor, running on your laptop, free forever.

---

## Why this exists

For 180 years we've educated kids with a system designed in 1843 Prussia to produce obedient soldiers and compliant factory workers. Bells, rows of desks, standardized tests, silence. *The Unscarcity Blueprint* argues, and this project agrees, that the factory model is finally obsolete:

> *"We've trained an entire civilization to act like machines, and now the actual machines have arrived to do the job for real."*
> From [Education: Factory vs. Citizen](https://unscarcity.ai/a/education-factory-vs-citizen)

Chapter 5 describes a world where every kid has a personal tutor, an AI that teaches the way Aristotle taught Alexander, one kid at a time, adapted to that kid's pace and interests. That technology now exists. This repo is a small, working piece of it for parents who don't want to wait.

Read [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md) for the longer version of why this project is shaped the way it is. Read [`docs/MEDIUM.md`](docs/MEDIUM.md) for the story of using it with my own 12-year-old for the first time.

---

## Works for any subject

Math is the default, it ships with pixel-perfect number-line / inequality diagrams, but Aristotle writes practice in any subject your child takes: science, social studies, language arts, foreign language, or anything you add. List subjects in `.env`; Aristotle rotates through them.

```bash
SUBJECTS=math,science,social_studies,language_arts
```

Per-subject curriculum, textbook, and worksheet shape live in [`docs/SUBJECTS.md.template`](docs/SUBJECTS.md.template). Copy it, customize it, done.

---

## Quick start

```bash
git clone https://github.com/patdeg/aristotle.git
cd aristotle

cp .env.example .env
# Edit .env, fill in CHILD_NAME, SUBJECTS, Canvas + email details.

cp docs/CHILD_PROFILE.md.template docs/CHILD_PROFILE.md
# Describe your kid: interests, reading level, what motivates them.

cp docs/SUBJECTS.md.template docs/SUBJECTS.md
# For each subject, note textbook + standards + desired worksheet shape.

./weekly-practice.sh --dry-run
```

In `--dry-run`, all email goes to `PARENT_EMAIL` only, nothing lands in your child's inbox until you've reviewed the output and are happy.

### Scheduling

```cron
# Every Tuesday and Thursday at noon
0 12 * * 2,4 /path/to/aristotle/weekly-practice.sh >> /path/to/aristotle/logs/cron.log 2>&1
```

Most families run it twice a week (one set on Tuesday, a fresh set on Thursday). Run it as often as the kid can keep up with, and no more.

---

## Pick the mentor's name

Aristotle's the default, but the philosopher is a slot. Edit `MENTOR_NAME` in `.env`:

```bash
MENTOR_NAME=Aristotle       # the one-on-one tutor of Alexander
MENTOR_NAME=Socrates        # the relentless questioner
MENTOR_NAME=Hypatia         # the Alexandrian mathematician
MENTOR_NAME=Confucius       # the teacher of virtue
MENTOR_NAME=Ada             # Ada Lovelace, for a modern girl
MENTOR_NAME=Ibn_Sina        # Avicenna, for the Islamic Golden Age
```

The name flows through the prompt, the worksheet header, and the email signature. Pick whoever your kid would open a letter from.

---

## Email setup (one-time, ~15 minutes)

Aristotle sends the weekly PDF as an email attachment. You need a From: address your kid will recognize. Two parts:

### 1. Buy a domain (one-time, ~$10–15/year)

Any registrar works. Common choices:

| Registrar | Approx .com / year | Notes |
|---|---|---|
| [Cloudflare Registrar](https://www.cloudflare.com/products/registrar/) | $10.44 | At-cost pricing, no markup. |
| [Porkbun](https://porkbun.com) | $11 | WHOIS privacy free, clean UI. |
| [Namecheap](https://www.namecheap.com) | $13 | Most common, strong brand. |
| [GoDaddy](https://www.godaddy.com) | $12–22 | Easy to use, watch the second-year renewal price. |

Pick something family-flavoured: `smithfamily.net`, `yourkid.school`, `learnwith.us`. One domain covers every kid and every subject forever.

### 2. Host email on Migadu (~$9/month)

[Migadu](https://www.migadu.com/pricing/) is a small Swiss email host built for this exact use case. They charge per **account**, not per mailbox, one subscription covers every address across every domain you ever own.

Current plans (verified April 2026):

| Plan | Price | Daily outgoing | Daily incoming | Notes |
|---|---|---|---|---|
| **Micro** | $19/year | 20 msgs | 200 msgs | Fine for one kid, weekly worksheet. |
| **Mini** | $90/year ($9/mo) | 100 msgs | 1,000 msgs | Recommended, works as the whole family's email too. |
| **Standard** | $290/year | 500 msgs | 3,000 msgs | Large household / multiple kids. |
| **Maxi** | $990/year | 2,000 msgs | 10,000 msgs | Overkill for personal use. |

All plans: **unlimited addresses, unlimited domains** (Mini and up). For Aristotle, Micro handles one kid; Mini is the sweet spot if you want real family email on the same domain.

### 3. Configure `himalaya`

Once Migadu is set up, put this in `~/.config/himalaya/config.toml`:

```toml
[accounts.aristotle]
email = "aristotle@yourdomain.example"
display-name = "Aristotle"

backend = "imap"
imap.host = "imap.migadu.com"
imap.port = 993
imap.login = "aristotle@yourdomain.example"
imap.auth.passwd.cmd = "pass show aristotle-migadu"   # or any secret store

message.send.backend = "smtp"
smtp.host = "smtp.migadu.com"
smtp.port = 465
smtp.encryption = "tls"
smtp.login = "aristotle@yourdomain.example"
smtp.auth.passwd.cmd = "pass show aristotle-migadu"
```

Then `HIMALAYA_ACCOUNT=aristotle` and `MENTOR_EMAIL=aristotle@yourdomain.example` in `.env`.

> **Don't want email?** Comment out the `send_email.py` call in `weekly-practice.sh`. Worksheets still land as PDFs in `exercises/`, you can open or print them directly.

---

## Setup for your school / state

Aristotle was built for families in a US public school on Canvas, but none of the code hard-codes anyone's district, state, or grade.

### If your school uses Canvas

1. **Find your district's Canvas URL.** Always `https://<district>.instructure.com`. Whichever domain appears in the parent portal is the one you want, put it in `.env` as `CANVAS_BASE_URL`.
2. **Create a parent observer account** if you don't have one. Most districts link you automatically after the first year.
3. **Generate a personal access token.** *Account → Settings → "+ New Access Token"*. Copy into `.env` as `CANVAS_API_KEY`.
4. **Find each course ID.** Click into a class; the URL shows `…/courses/184581`, the trailing number is the ID. Put math in `CANVAS_COURSE_MATH`, science in `CANVAS_COURSE_SCIENCE`, etc.
5. **Find your child's Canvas observee ID.** *Account → Observing*; hover your kid's name, the link contains the ID. Put it in `CANVAS_STUDENT_ID`.

### If your school doesn't use Canvas

Aristotle still works, you just tell it manually what to drill on. Skip the `CANVAS_*` variables and keep a short list of weak topics in `docs/CHILD_PROFILE.md`:

```markdown
## Current trouble spots
- Fractions: dividing mixed numbers, 3/5 on last quiz
- Social studies: Ancient Egypt vocabulary, missed the test
```

The prompt reads this file whenever Canvas is missing.

### State standards / curriculum

Aristotle doesn't hardcode state standards or textbooks, it asks Claude to follow whatever you note in `docs/CHILD_PROFILE.md`:

```markdown
## Basics
- Textbook: enVision Math 2.0, Grade 5 (Pearson)
- Standards: Common Core (CCSS.MATH)
```

Works for Common Core, TEKS (Texas), SOL (Virginia), BEST (Florida), NGSS (science), or any other standard. Just name it.

---

## What ships in this repo

| File | Role |
|---|---|
| `weekly-practice.sh` | Cron entry point. Builds the prompt, invokes Claude Code, emails the result. |
| `generate_diagram.py` | Pixel-perfect matplotlib number lines / inequalities, no AI hallucination. |
| `generate_illustration.py` | Scenario illustrations via Demeterics GenAI (optional). |
| `md_to_pdf.py` | Markdown → styled printable PDF via headless chromium. |
| `embed_images.py` | Inlines images as base64 for standalone HTML. |
| `send_email.py` | SMTP sender via `himalaya`, with inline image + PDF attachment support. |
| `print-pdf.sh` | Wrapper that prepends a blank page (fixes the EPSON WF7820 page-1 drop bug). |
| `check-safety.sh` | Preflight: scans your staged changes for keys/PII before you push. Run this. |
| `docs/PHILOSOPHY.md` | Long-form "why this exists", the Chapter 5 argument in full. |
| `docs/MEDIUM.md` | The Medium article: first-person story of using this with my own 12-year-old. |
| `docs/LINKEDIN.md` | Short-form LinkedIn version of the same story. |
| `docs/CHILD_PROFILE.md.template` | Your kid's interests, cognitive style, voice. Copy, edit, keep local. |
| `docs/SUBJECTS.md.template` | Per-subject curriculum + worksheet shape. Copy, edit, keep local. |
| `docs/CODE_CURRICULUM.md.template` | Optional weekly CS/coding track. |
| `CONTRIBUTING.md` | How to share back without leaking other kids' PII. |

---

## Requirements

- **[Claude Code](https://claude.com/claude-code)** (subscription, OAuth), worksheet generator runs as `claude -p …`. Anthropic API key not required and not used.
- **[`himalaya`](https://github.com/pimalaya/himalaya)** CLI, SMTP sender.
- **`chromium`**, headless PDF rendering.
- **`pdfunite`** (poppler-utils), only if you use `print-pdf.sh`.
- **Python 3.10+** with `matplotlib` and `requests`.

---

## Privacy / safety, how this repo stays clean

This is a **public repo**, which means every file in it is visible to anyone on the internet. Two mechanisms keep your kid's data out of it:

1. **`.gitignore`**, `.env`, `logs/`, `exercises/`, and `*.pdf` never get staged. Your customized `docs/CHILD_PROFILE.md` and `docs/SUBJECTS.md` are gitignored too; only the `.template` versions are tracked.

2. **`.github/workflows/secret-scan.yml`** runs three checks on every push and PR:
   - `gitleaks`, catches API-key-shaped strings across 100+ providers.
   - `PII regex guard`, rejects real email addresses, phone numbers, Canvas tokens, `sk-/pk-/dmt_/AIza` keys, AWS access keys, and private-key headers.
   - `commit author email guard`, rejects commits authored with a personal `@gmail.com` / `@yahoo.com` / etc. Use the GitHub noreply form instead.

**Before you push**, run `./check-safety.sh` locally. It's the same scan the CI action runs, no surprises.

If the CI blocks you, see [`CONTRIBUTING.md`](CONTRIBUTING.md) for how to fix your git identity or rewrite a leaky commit.

---

## Further reading from *The Unscarcity Blueprint*

- [Chapter 5: The Education of a Citizen](https://unscarcity.ai/a/chapter5), the argument this project embodies.
- [Education: Factory vs. Citizen](https://unscarcity.ai/a/education-factory-vs-citizen), the Prussian model and what replaces it.
- [Gen Z and the Human Edge](https://unscarcity.ai/a/gen-z-human-edge), *"You don't learn the Human Edge in a classroom. You learn it by using it."*
- [Agentic AI & Orchestration](https://unscarcity.ai/a/agentic-ai-orchestration), the orchestration skills education now has to prioritize.
- [Four Living Pillars](https://unscarcity.ai/a/four-living-pillars), the wider post-scarcity architecture this project fits inside.
- [Guiding Axioms](https://unscarcity.ai/a/guiding-axioms), the principles underneath.

---

*MIT License. Contributions welcome, see [`CONTRIBUTING.md`](CONTRIBUTING.md).*

*Aristotle (384–322 BCE) tutored one student at a time and thought that was the point.*
