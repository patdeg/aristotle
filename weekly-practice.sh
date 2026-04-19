#!/usr/bin/env bash
#
# Aristotle — weekly practice generator.
#
# Reads your child's grades from Canvas, generates a Socratic practice
# worksheet tuned to what they're struggling with, renders it to PDF,
# and emails the result.
#
# Usage:
#   ./weekly-practice.sh                # Normal run — emails child + parent
#   ./weekly-practice.sh --dry-run      # Emails only PARENT_EMAIL
#   ./weekly-practice.sh --since 2w     # Override Canvas lookback window
#
# Cron:
#   0 12 * * 2,4 /path/to/aristotle/weekly-practice.sh \
#     >> /path/to/aristotle/logs/cron.log 2>&1
#
# See README.md for setup. All configuration lives in .env next to this script.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXERCISES_DIR="$SCRIPT_DIR/exercises"
LOG_DIR="$SCRIPT_DIR/logs"
DATE=$(date +%Y-%m-%d)
LOGFILE="$LOG_DIR/run-$DATE.log"

mkdir -p "$EXERCISES_DIR" "$LOG_DIR"

# --- Environment ------------------------------------------------------------
# Aristotle runs through the Claude Code subscription (OAuth). It does NOT
# use the Anthropic API. Unset any inherited key so `claude` picks up the
# subscription credentials instead.
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN 2>/dev/null || true

export PATH="$HOME/.local/bin:$HOME/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
    echo "ERROR: $SCRIPT_DIR/.env not found. Copy .env.example and fill it in." >&2
    exit 1
fi

set -a
# shellcheck disable=SC1091
source "$SCRIPT_DIR/.env"
set +a

# Required vars
: "${MENTOR_NAME:?MENTOR_NAME must be set in .env}"
: "${CHILD_NAME:?CHILD_NAME must be set in .env}"
: "${CHILD_GRADE:?CHILD_GRADE must be set in .env}"
: "${PARENT_EMAIL:?PARENT_EMAIL must be set in .env}"
: "${SUBJECTS:=math}"

CHILD_NAME_LOWER="$(echo "$CHILD_NAME" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9' '-' | sed 's/-*$//')"

# --- Parse args -------------------------------------------------------------
DRY_RUN=false
SINCE_FLAG=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)  DRY_RUN=true; shift ;;
        --since)    SINCE_FLAG="--since $2"; shift 2 ;;
        -h|--help)  sed -n '3,18p' "$0"; exit 0 ;;
        *)          echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

if [[ "$DRY_RUN" = true ]]; then
    RECIPIENTS_INSTRUCTION="DRY RUN: send all email ONLY to $PARENT_EMAIL. Do NOT email the child."
    EXERCISES_TO="$PARENT_EMAIL"
else
    EXERCISES_TO="${CHILD_EMAIL:-$PARENT_EMAIL}, $PARENT_EMAIL"
    RECIPIENTS_INSTRUCTION="Send the exercises email to: $EXERCISES_TO. Do NOT send a separate answer-key email — the answer key is saved to disk for parent reference only."
fi

# --- Build prompt -----------------------------------------------------------
read -r -d '' PROMPT_TEMPLATE << 'PROMPT_EOF' || true
You are {MENTOR} — a Socratic AI mentor generating this week's practice
worksheet for {CHILD}, a {GRADE} student. Today is {DATE}.

This week's subjects: **{SUBJECTS}**. Generate one section per subject.

Read these files for full context:
- {SCRIPT_DIR}/CLAUDE.md — operating rules, what never to commit, etc.
- {SCRIPT_DIR}/docs/PHILOSOPHY.md — the Chapter 5 framing of this project. You are the AI Aristotle; act like it.
- {SCRIPT_DIR}/docs/CHILD_PROFILE.md — the child's interests, cognitive style, voice.
- {SCRIPT_DIR}/docs/SUBJECTS.md (if present) — per-subject curriculum, textbook, and preferred worksheet shape.

Every scenario must be grounded in the profile. Generic examples are
forbidden. Every worksheet section should exercise at least one of the
Three Pillars from Chapter 5: **Systems Thinking** (cross-subject
connections), **Humanities / narrative ethics** (a situation the child
must judge, not just compute on), or **Agency** (the child builds
something — even small).

## Step 1 — Pull Canvas submissions for each subject

For each subject in SUBJECTS, look up its Canvas course ID from the
environment. The variable name is `CANVAS_COURSE_<UPPERCASE_SUBJECT>`:

- `math`           → `$CANVAS_COURSE_MATH`
- `science`        → `$CANVAS_COURSE_SCIENCE`
- `social_studies` → `$CANVAS_COURSE_SOCIAL_STUDIES`
- `language_arts`  → `$CANVAS_COURSE_LANGUAGE_ARTS`
- `foreign_language` → `$CANVAS_COURSE_FOREIGN_LANGUAGE`

For each subject whose course ID is set, fetch submissions:

```bash
curl -s -H "Authorization: Bearer $CANVAS_API_KEY" \
  "$CANVAS_BASE_URL/courses/<COURSE_ID>/students/submissions?student_ids[]=$CANVAS_STUDENT_ID&per_page=100" {SINCE}
```

If the course ID is blank, the school doesn't use Canvas, or Canvas returns
nothing, read the "Current trouble spots" table in CHILD_PROFILE.md for that
subject and use it as the source of weak topics. If that's empty too, treat
it as "diagnostic week" and pick 3 topics from the grade-level standards the
child is likely on.

Identify the current module per subject (the one containing the most
recently `graded_at` submission). Topics in that module are highest
priority. Earlier modules that still scored below 100% are remediation
candidates.

## Step 2 — Score-based scaling

For each topic that needs practice:

| Most recent score           | Output                                |
|-----------------------------|---------------------------------------|
| No score yet / diagnostic   | 1 worked example + **3** exercises    |
| 5/5 (100%)                  | **Skip** — already mastered           |
| 4/5 (80%)                   | 1 worked example + **3** exercises    |
| 3/5 (60%)                   | 1 worked example + **4** exercises    |
| ≤ 2/5 (≤ 40%)               | 1 worked example + **5** exercises    |

Pick up to 3 topic groups **per subject**. Current-module topic first, then
remediation (lowest score first). If the child has many subjects, keep each
subject section short — one strong topic beats three shallow ones.

## Step 2.5 — Per-subject worksheet shape

Follow the shape defined in `docs/SUBJECTS.md` for each subject. If that
file isn't present, use these defaults:

- **math** — scenario → 3-4 Socratic questions → worked example → 3-5 drill
  problems. Include `<!-- DIAGRAM: ... -->` tags (rendered by matplotlib)
  whenever a number line, inequality, or coordinate figure helps.
  **One `<!-- ILLUSTRATION_EXERCISE: ... -->` tag per problem** — each
  drill problem gets its own scene, not just the section header.
- **science** — phenomenon → "what do you notice / wonder" Socratic
  questions → concept explanation → label-a-diagram + predict / observe /
  explain + short-answer items.
- **social_studies** — short primary-source excerpt (≤1 paragraph, public
  domain or paraphrase — never reproduce copyrighted material verbatim) →
  "what do you see / infer" questions → vocabulary drill → one DBQ-style
  short-essay prompt with a brief rubric.
- **language_arts** — 150-300 word reading passage (public domain or
  paraphrase) → 3-5 comprehension questions → grammar/vocabulary mini-drill
  → paragraph-writing prompt with a rubric.
- **foreign_language** — short dialogue in the target language →
  translation drill → verb-conjugation table with blanks → cultural tie-in.

Illustrations (via `<!-- ILLUSTRATION_SECTION: ... -->` and
`<!-- ILLUSTRATION_EXERCISE: ... -->` tags) are PURE SCENES — never include
formulas, equations, or text labels in the artwork itself.

## Step 3 — Generate the worksheet

Write a Markdown file at:

  {SCRIPT_DIR}/exercises/practice-{CHILD_LOWER}-{DATE}.md

## Step 4 — Generate a hero image for this week

```bash
python3 {SCRIPT_DIR}/generate_illustration.py \
  --style hero \
  --prompt "ONE SINGLE PERSON ONLY — exactly one figure in the frame,
  no duplicates. The figure is {MENTOR}, shown as a warm, approachable
  teacher in a scene tied to this week's dominant topic. Clean ligne
  claire style, flat colors, no shading." \
  --output {SCRIPT_DIR}/exercises/images/mentor_hero_{CHILD_LOWER}_{DATE}.png \
  --size 1024x1024
```

Reference this image at the top of the worksheet:

  ![{MENTOR}](images/mentor_hero_{CHILD_LOWER}_{DATE}.png)

## Step 5 — Generate the answer key

Write a second Markdown file at:

  {SCRIPT_DIR}/exercises/practice-{CHILD_LOWER}-{DATE}-ANSWERS.md

Include:
- Full worked solutions for every problem.
- "Watch for" notes listing the common mistakes per problem.
- Suggested parent-guide responses to each Socratic question.
- A table of the Canvas assignments that triggered each section.

## Step 6 — Render diagrams, illustrations, and PDFs

```bash
python3 {SCRIPT_DIR}/generate_diagram.py \
  --process {SCRIPT_DIR}/exercises/practice-{CHILD_LOWER}-{DATE}.md

python3 {SCRIPT_DIR}/generate_illustration.py \
  --process {SCRIPT_DIR}/exercises/practice-{CHILD_LOWER}-{DATE}.md

python3 {SCRIPT_DIR}/md_to_pdf.py \
  {SCRIPT_DIR}/exercises/practice-{CHILD_LOWER}-{DATE}.md
python3 {SCRIPT_DIR}/md_to_pdf.py \
  {SCRIPT_DIR}/exercises/practice-{CHILD_LOWER}-{DATE}-ANSWERS.md
```

## Step 7 — Send the email

{RECIPIENTS}

Write a short, warm email body (< 200 words) to /tmp/exercises_body.html in
{MENTOR}'s voice. The PDF has the full worksheet — the email is just the
hook. The email must embed this week's hero image by CID, matching its
basename exactly:

  <img src="cid:mentor_hero_{CHILD_LOWER}_{DATE}.png" ...>

Then send:

```bash
python3 {SCRIPT_DIR}/send_email.py \
  --to "{RECIPIENTS_TO}" \
  --subject "{MENTOR} — Practice for {CHILD} — {DATE}" \
  --html /tmp/exercises_body.html \
  --attach {SCRIPT_DIR}/exercises/practice-{CHILD_LOWER}-{DATE}.pdf \
  --inline {SCRIPT_DIR}/exercises/images/mentor_hero_{CHILD_LOWER}_{DATE}.png
```

Do NOT send a separate answer-key email. The answer-key PDF is saved to
disk for the parent to open locally.

## Step 8 — Print a summary

Print which topics were covered, the files produced, and confirmation the
email was sent.
PROMPT_EOF

PROMPT="$PROMPT_TEMPLATE"
PROMPT="${PROMPT//\{MENTOR\}/$MENTOR_NAME}"
PROMPT="${PROMPT//\{CHILD\}/$CHILD_NAME}"
PROMPT="${PROMPT//\{CHILD_LOWER\}/$CHILD_NAME_LOWER}"
PROMPT="${PROMPT//\{GRADE\}/$CHILD_GRADE}"
PROMPT="${PROMPT//\{SUBJECTS\}/$SUBJECTS}"
PROMPT="${PROMPT//\{DATE\}/$DATE}"
PROMPT="${PROMPT//\{SINCE\}/$SINCE_FLAG}"
PROMPT="${PROMPT//\{SCRIPT_DIR\}/$SCRIPT_DIR}"
PROMPT="${PROMPT//\{RECIPIENTS\}/$RECIPIENTS_INSTRUCTION}"
PROMPT="${PROMPT//\{RECIPIENTS_TO\}/$EXERCISES_TO}"

# --- Run Claude Code --------------------------------------------------------
echo "=== Aristotle run: $DATE (dry_run=$DRY_RUN) ===" | tee -a "$LOGFILE"
echo "Mentor: $MENTOR_NAME  |  Child: $CHILD_NAME ($CHILD_GRADE)  |  Subjects: $SUBJECTS" | tee -a "$LOGFILE"

claude \
    --dangerously-skip-permissions \
    -p \
    --model opus \
    "$PROMPT" \
    2>&1 | tee -a "$LOGFILE"

echo "=== Done: $(date) ===" | tee -a "$LOGFILE"
