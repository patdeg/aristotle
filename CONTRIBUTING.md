# Contributing to Aristotle

First, thank you. This project only works if other parents share what they've learned.

## Things to contribute

**Most valuable:**
- A new subject playbook in `docs/SUBJECTS.md.template`, if you've dialled in science, foreign language, or art in a way that works for your kid, that shape belongs in the template.
- A new mentor persona. Aristotle is the default, but Socrates, Hypatia, Ada Lovelace, Confucius, Ibn Sina all fit the same pedagogy. A `docs/personas/hypatia.md` with voice guidelines would help other families pick.
- Accessibility improvements to the worksheet template (color contrast, dyslexia-friendly fonts, screen-reader hooks on the PDF).
- Fixes to the diagram / illustration generators, especially new `<!-- DIAGRAM: ... -->` types (coordinate planes, bar models, geometry proofs).

**Also welcome:**
- LMS adapters (Google Classroom, Schoology, PowerSchool) alongside the Canvas default.
- Non-English language support, the prompt is English now, but the scenario logic is language-agnostic.
- Docs improvements, typo fixes, example `.env` configurations for different district setups.

## Things that will get a PR closed

**Never, ever:**
- Any real child's name, email, school, teacher, or grade, in code, docs, tests, or commit messages.
- Any real Canvas token, Anthropic key, SMTP password, or any other live credential.
- Any worksheet output, those are personal artifacts. Contribute the *template*, never the generated file.
- `.env`, `logs/`, `exercises/`, or anything else covered by `.gitignore`.

The GitHub Action at `.github/workflows/secret-scan.yml` will block PRs that introduce API-key-shaped strings, real email addresses, phone numbers, or Canvas-style tokens. If it trips on something you meant to be a placeholder, use `example.com` / `yourdomain.example` / `YOUR_DISTRICT`, those are on the allowlist.

## Your git identity

Configure git to use GitHub's **noreply** email before pushing, not your personal address:

```bash
# Find your numeric GitHub user ID at https://api.github.com/users/YOUR_USERNAME
git config user.email "<NUMERIC_ID>+<username>@users.noreply.github.com"
git config user.name "Your Name"
```

If you've already pushed with a personal email by accident, you can rewrite history before the PR. Replace `<OLD_EMAIL>` with the address leaked in your git log and `<NEW_NOREPLY_EMAIL>` with your GitHub noreply form:

```bash
git filter-repo --email-callback '
  return b"<NEW_NOREPLY_EMAIL>" if email == b"<OLD_EMAIL>" else email
'
git push --force-with-lease origin main
```

`--force-with-lease` is safer than `--force`, it refuses the push if someone else has pushed to main since your last fetch.

## Shape of a good PR

- One change per PR. A subject playbook addition is one PR. A bug fix is another.
- Title in imperative mood: `Add Spanish foreign-language playbook`, not `Adding Spanish` or `Spanish stuff`.
- Include a short description of what a parent would do differently because of this change.
- If you touched the prompt in `weekly-practice.sh`, test it in `--dry-run` first and paste one sanitized example output.

## Code of conduct

Be kind. Remember that every user of this tool is a parent trying to help their kid. That includes you.
