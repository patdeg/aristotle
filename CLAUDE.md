# Aristotle, Claude Code agent guide

Aristotle generates weekly Socratic practice for a single child in any subject, tailored to what they're struggling with in school.

> **Philosophical grounding.** This project is an implementation of the "AI Aristotle" described in Chapter 5 of *The Unscarcity Project* ([unscarcity.ai/a/chapter5](https://unscarcity.ai/a/chapter5)). When you generate a worksheet, you are operating inside that framing, you are not a homework-finishing bot; you are a Socratic tutor giving *this one child* the personal attention Aristotle gave Alexander. Read `docs/PHILOSOPHY.md` before generating if you need the full argument.
>
> Every worksheet should exercise the three pillars Chapter 5 names: **Systems Thinking** (connect across subjects), **Humanities / narrative ethics** (make the kid judge, not just compute), **Agency** (the kid builds something, even if it's just filling in the blanks themselves).

---

## PRIME DIRECTIVE, NO ANTHROPIC API KEY

This tool runs through the **Claude Code subscription (OAuth)**, not the Anthropic API.

- Never set, export, or require `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`.
- `weekly-practice.sh` must `unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN` before invoking `claude`.
- If something errors with "ANTHROPIC_API_KEY not set", the fix is to remove that check.

---

## PRIME DIRECTIVE, NEVER COMMIT PII OR SECRETS

This is a **public repo**. Everything a child produces is personal.

Never commit:
- `.env` (API keys, passwords)
- `logs/` (Canvas responses contain grades + names)
- `exercises/` (worksheets have the child's name, interests, sometimes reflections)
- Anything under `docs/` that names a real child, teacher, school, or class period
- Canvas student IDs, course IDs, or URLs pointing at a specific district

The `.gitignore` already covers the first three. The GitHub Action at `.github/workflows/secret-scan.yml` blocks anything that looks like an API key, email address, or Canvas-style ID.

When editing docs or scripts, use placeholder values (`CHILD_NAME`, `YOUR_DISTRICT.instructure.com`), never hardcode a real one.

---

## Configuration

All customization happens through `.env`:

| Variable | Purpose |
|---|---|
| `MENTOR_NAME` | Name of the AI tutor persona (default: `Aristotle`). Flows into prompts, worksheets, email. |
| `MENTOR_EMAIL` | From address for outgoing email. |
| `CHILD_NAME` | Your child's first name. |
| `CHILD_GRADE` | Grade level (e.g. `6th`, `8th`). |
| `CHILD_EMAIL` | Where the worksheet gets emailed. |
| `PARENT_EMAIL` | Where the answer key goes. Also the only recipient in `--dry-run`. |
| `SUBJECTS` | Comma-separated list, e.g. `math,science,social_studies`. Default: `math`. |
| `CANVAS_COURSE_<SUBJECT>` | Canvas course ID per subject, e.g. `CANVAS_COURSE_MATH=184581`. |
| `CANVAS_API_KEY` | Personal access token from your parent-observer Canvas account. |
| `CANVAS_BASE_URL` | e.g. `https://yourdistrict.instructure.com/api/v1`. |
| `CANVAS_STUDENT_ID` | Your child's Canvas observee ID. |
| `DEMETERICS_API_KEY` | Optional, enables scenario illustrations. |
| `HIMALAYA_ACCOUNT` | Name of the `himalaya` SMTP account to send from. |

Child-specific voice, interests, and cognitive profile live in `docs/CHILD_PROFILE.md`. Per-subject curriculum, textbook, and worksheet shape live in `docs/SUBJECTS.md`. Both are gitignored copies of templates shipped in `docs/*.template`.

---

## Workflow

1. **Fetch grades.** Hit Canvas for submissions on the child's math course. Parse scores.
2. **Pick topics.** Any topic below 100% is a candidate. Prioritize the current module (most recent `graded_at`), then remediate older weak topics.
3. **Score-based scaling:**
   - No score yet / proactive → 1 worked example + 3 exercises
   - 5/5 → skip (mastered)
   - 4/5 → 1 example + 3 exercises
   - 3/5 → 1 example + 4 exercises
   - ≤ 2/5 → 1 example + 5 exercises
4. **Generate the worksheet** as Markdown with `<!-- DIAGRAM: ... -->` and `<!-- ILLUSTRATION: ... -->` tags.
5. **Render diagrams** with `generate_diagram.py` (matplotlib, exact, no hallucination).
6. **Render illustrations** with `generate_illustration.py` (optional, Demeterics).
7. **Convert to PDF** with `md_to_pdf.py`.
8. **Email** via `send_email.py`, child gets the exercises, parent gets the answer key.

---

## Worksheet format

- Opens with a scene tied to the child's interests (see `docs/CHILD_PROFILE.md`).
- 3–4 Socratic questions that lead the child to the concept themselves.
- Formal naming of the concept in 2–3 sentences.
- One real-world adult use of the concept.
- One fully-worked example using the method their teacher uses.
- Then exercises (count per the scaling table above). **Every exercise gets its own scene illustration**, a per-problem illustration, not just one per section. Empirically, this drives a large jump in engagement.
- Generous blank writing space and an `Answer: _______` line per problem.

Each section ends with a printable, writable PDF. No screens required.

---

## Skills referenced by the prompt

The child profile, per-subject playbook, and (optional) code-curriculum files guide voice and scenario choice. Put your customized versions at:

- `docs/CHILD_PROFILE.md` (copy the template, edit)
- `docs/SUBJECTS.md` (copy the template, edit, per-subject curriculum + preferred worksheet shape)
- `docs/CODE_CURRICULUM.md` (copy the template, edit, or delete if you don't want a weekly CS track)

The weekly script reads these automatically.
