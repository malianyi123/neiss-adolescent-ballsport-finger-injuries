#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# One-shot helper: initialise the git repository and make the first commit.
#
# Usage:
#   bash setup_git.sh "Your Name" "your.email@example.com"
#
# It does NOT push anything and does NOT contact GitHub. After it finishes,
# follow the tutorial to create the remote repository and push.
# ---------------------------------------------------------------------------
set -euo pipefail

NAME="${1:-}"
EMAIL="${2:-}"

if [[ -z "$NAME" || -z "$EMAIL" ]]; then
  echo "Usage: bash setup_git.sh \"Your Name\" \"your.email@example.com\"" >&2
  exit 1
fi

cd "$(dirname "$0")"

if ! command -v git >/dev/null 2>&1; then
  echo "git is not installed."
  echo "  macOS:  xcode-select --install"
  echo "  Ubuntu: sudo apt install git"
  exit 1
fi

if [[ -d .git ]]; then
  echo "This directory is already a git repository. Nothing to do."
  exit 0
fi

git init -b main
git config user.name  "$NAME"
git config user.email "$EMAIL"

git add .

echo
echo "Files staged for the first commit:"
git diff --cached --name-only | wc -l
echo
echo "Sanity check — the following must NOT appear (raw data must stay out of git):"
BAD=$(git diff --cached --name-only \
        | grep -E '^data/(intermediate/|processed/|raw/neiss/)' \
        | grep -v '^data/raw/neiss/\.gitkeep$' || true)
if [[ -n "$BAD" ]]; then
  echo "$BAD" | sed 's/^/  /'
  echo "  !! raw or intermediate data is staged; check .gitignore before committing" >&2
  exit 1
fi
echo "  OK - no raw or intermediate data staged"

git commit -m "Reproducible NEISS analysis pipeline for adolescent ball-sport finger injuries, 2015-2025

Includes the full cohort-construction and analysis pipeline, the verified official
CPSC code mappings, the download log recording data provenance, and the revision
analyses added during peer review (design-based confidence intervals, survey-weighted
trend analysis, multiplicity adjustment, severe-disposition instability assessment,
and narrative diagnostic concordance)."

echo
echo "Done. First commit created on branch 'main'."
echo "Next: create an empty PUBLIC repository on GitHub, then run"
echo "  git remote add origin https://github.com/USERNAME/neiss-adolescent-ballsport-finger-injuries.git"
echo "  git push -u origin main"
