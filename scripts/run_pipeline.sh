#!/usr/bin/env bash
# run_pipeline.sh — TransferAI end-to-end helper
#
# Usage:
#   ./scripts/run_pipeline.sh "Will PSYC 1 at SMC satisfy UCSD prep?" [answer.md]
#
# The script performs:
#   1. Planner → generates plan JSON
#   2. Executor → runs plan and saves node outputs
#   3. Composer → produces a counselor-style Markdown answer
#
# All intermediate artefacts are kept in tmp files unless you set
# the ANSWER_MD (optional 2nd argument).

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 \"USER QUESTION\" [ANSWER.md]" >&2
  exit 1
fi

QUESTION="$1"
ANSWER_MD="${2:-answer.md}"

# Temp files for plan and executor results
PLAN_JSON="$(mktemp /tmp/ta-plan-XXXXXX.json)"
RESULTS_JSON="$(mktemp /tmp/ta-results-XXXXXX.json)"

printf '\n▶ Planning…\n' >&2
# The planner prints JSON plan to stdout; capture it into file
python -m agent.planner "${QUESTION}" > "$PLAN_JSON"

printf '\n▶ Executing plan (results → %s)…\n' "$RESULTS_JSON" >&2
python -m agent.executor "$PLAN_JSON" -o "$RESULTS_JSON"

printf '\n▶ Composing Markdown answer (→ %s)…\n' "$ANSWER_MD" >&2
python -m agent.composer "$RESULTS_JSON" --question "${QUESTION}" -o "$ANSWER_MD"

printf '\n✔ Done!\n' >&2
printf '   • Plan JSON:    %s\n' "$PLAN_JSON" >&2
printf '   • Tool results: %s\n' "$RESULTS_JSON" >&2
printf '   • Markdown:     %s\n' "$ANSWER_MD" >&2 