#!/usr/bin/env bash
#
# check-safety.sh — preflight scan for keys and PII.
#
# Run this before pushing, especially before the first push of your fork.
# It runs the same checks as .github/workflows/secret-scan.yml, locally.
#
# Usage:
#   ./check-safety.sh           # scan all tracked files
#   ./check-safety.sh --staged  # scan only files you've git-added
#
# Exits 0 if clean, 1 if anything suspicious is found.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="all"
if [[ "${1:-}" == "--staged" ]]; then
    MODE="staged"
fi

if [[ "$MODE" == "staged" ]]; then
    mapfile -t FILES < <(git diff --cached --name-only --diff-filter=ACM)
else
    mapfile -t FILES < <(git ls-files)
fi

# Skip files that legitimately contain detection patterns.
SKIPS=(
    '^\.github/workflows/secret-scan\.yml$'
    '^\.github/gitleaks\.toml$'
    '^README\.md$'
    '^check-safety\.sh$'
    '^docs/images/.*\.(png|jpg|jpeg|gif|webp)$'
)
for skip in "${SKIPS[@]}"; do
    mapfile -t FILES < <(printf '%s\n' "${FILES[@]}" | grep -v -E "$skip" || true)
done

if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "No files to scan."
    exit 0
fi

echo "Scanning ${#FILES[@]} file(s)..."
echo ""

FAIL=0

check() {
    local label="$1" pattern="$2"
    local hits
    hits=$(grep -HnP "$pattern" "${FILES[@]}" 2>/dev/null || true)
    if [[ -n "$hits" ]]; then
        echo "❌ $label"
        echo "$hits" | sed 's/^/   /'
        echo ""
        FAIL=1
    else
        echo "✅ $label"
    fi
}

check "no real email addresses" \
    '[A-Za-z0-9._%+-]+@(?!example\.)(?!your[a-z]*\.)(?!yourdomain\b)(?!placeholder\b)[A-Za-z0-9.-]+\.(?!example\b)[A-Za-z]{2,}'

check "no US phone numbers" \
    '\b(?:\+?1[-. ]?)?\(?[2-9][0-9]{2}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}\b'

check "no Canvas access tokens" \
    '\b[0-9]{3,6}~[A-Za-z0-9]{40,}\b'

check "no API keys (sk-/pk-/dmt_/AIza)" \
    '\b(?:sk|pk|dmt|AIza)[-_][A-Za-z0-9_-]{20,}\b'

check "no AWS access keys" \
    '\bAKIA[0-9A-Z]{16}\b'

check "no private key blocks" \
    '-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----'

echo ""

# Commit author emails — check local history too
BAD_AUTHORS=$(git log --all --format='%ae%n%ce' 2>/dev/null | sort -u | \
    grep -iE '@(gmail|yahoo|hotmail|outlook|icloud|protonmail|me|aol|msn|live)\.(com|net)$' || true)

if [[ -n "$BAD_AUTHORS" ]]; then
    echo "❌ personal email in commit history:"
    echo "$BAD_AUTHORS" | sed 's/^/   /'
    echo ""
    echo "   Fix: git config user.email \"<NUMERIC_ID>+<username>@users.noreply.github.com\""
    echo "   Then rewrite history with git filter-repo. See CONTRIBUTING.md."
    FAIL=1
else
    echo "✅ git history uses noreply emails"
fi

echo ""

if [[ $FAIL -ne 0 ]]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠  Fix the issues above before pushing to a public repo."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓  Clean. Safe to push."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
