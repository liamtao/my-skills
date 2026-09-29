#!/usr/bin/env bash
#
# runner.sh — implement ONE ticket in a brand-new Claude session.
#
# This script deliberately knows nothing about dependency order, review gates, or which
# ticket should come next. Those live in prose inside the tickets and only an agent can
# read them. All this does is run one ticket cleanly and report honestly what happened,
# so the calling agent can decide what to do next.
#
# Usage:
#   runner.sh --ticket <path> [--verify "<cmd>"] [--model <name>] [--log-dir <dir>]
#
# Logs land flat in <feature>/runs/ as <YYYYMMDD-HHMMSS>-<ticket>.jsonl and .verify.log.
# One file per run rather than one directory per batch: the caller then has no name to
# invent, which is what used to make the directory a pile of ad-hoc names. Sorting by
# name sorts by time, a rerun never overwrites the run it is repeating, and pruning old
# logs is `ls runs/*.jsonl | head -n -10 | xargs rm`.
#
# Exit codes — the caller branches on these:
#   0  done: implemented, verified, Status rewritten to done
#   2  skipped: Status was not ready-for-agent (already done, or blocked)
#   3  verify failed: the session ended but the verify command does not pass
#   4  not marked done: session ended without the agent claiming the ticket
#   1  usage error

set -uo pipefail

TICKET="" VERIFY="" MODEL="" LOG_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --ticket)  TICKET="${2:-}"; shift 2 ;;
    --verify)  VERIFY="${2:-}"; shift 2 ;;
    --model)   MODEL="${2:-}";  shift 2 ;;
    --log-dir) LOG_DIR="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 1 ;;
  esac
done

[ -n "$TICKET" ] || { echo "usage: runner.sh --ticket <path> [--verify CMD] [--model NAME] [--log-dir DIR]" >&2; exit 1; }
[ -f "$TICKET" ] || { echo "no such ticket: $TICKET" >&2; exit 1; }

name=$(basename "$TICKET" .md)
LOG_DIR="${LOG_DIR:-$(cd "$(dirname "$TICKET")/.." && pwd)/runs}"

# Only ready-for-agent tickets run. Status values are free text in practice — "done" often
# carries a trailing note like "done — src/foo.tsx" — so match on the prefix, never equality.
# This guard is what makes re-running the whole directory safe: finished tickets fall out here.
#
# Ahead of mkdir on purpose: sweeping a finished directory should leave no trace, and the
# old layout's empty timestamp directories were exactly this guard firing after the mkdir.
if ! grep -qiE '^\*\*Status:\*\*[[:space:]]*ready-for-agent' "$TICKET"; then
  current=$(grep -iE '^\*\*Status:\*\*' "$TICKET" | head -1 | sed 's/^\*\*Status:\*\*[[:space:]]*//')
  echo "SKIP  $name — status is '${current:-<none>}', not ready-for-agent"
  exit 2
fi

mkdir -p "$LOG_DIR"
# Stamped at launch, so the name records when the run started rather than when it ended.
LOG_STEM="$LOG_DIR/$(date +%Y%m%d-%H%M%S)-$name"

read -r -d '' PROMPT <<EOF
Implement the ticket at $TICKET.

Read the ticket first, along with any SPEC.md or README.md beside it or in its parent directory.
Those carry the vocabulary and the constraints the ticket was written against, and the ticket
assumes you have read them. Anything they mark as out of scope is load-bearing: it is there
because someone decided it should not be touched in passing.

Build exactly what the ticket specifies. Not the next ticket, not an improvement you noticed
along the way.

Verify your work by running: ${VERIFY:-<no verify command configured — find how this project checks itself and use that>}

When every acceptance checkbox genuinely holds, tick them in the ticket file, change its
**Status:** line to done, and commit on the current branch.

If an acceptance criterion will not hold, stop and leave Status untouched, and say plainly what
blocked you. Whoever runs this is chaining tickets on the assumption that "done" means done — a
ticket left honestly unfinished costs them one rerun, while one marked done that isn't costs
them the several tickets built on top of it before anyone notices.
EOF

echo "RUN   $name"
echo "      log: $LOG_STEM.jsonl"

claude -p "$PROMPT" \
  --permission-mode acceptEdits \
  ${MODEL:+--model "$MODEL"} \
  --output-format stream-json --verbose \
  > "$LOG_STEM.jsonl" 2>&1

# Surface the session's closing message so the caller sees the agent's own account of the work
# without having to parse the whole stream. This is the only part of the transcript the caller
# reads: the stream itself runs to megabytes because every tool result is in it verbatim, and
# pulling that into the calling session would undo the context isolation this script exists for.
if command -v jq >/dev/null 2>&1; then
  jq -r 'select(.type=="result") | .result' "$LOG_STEM.jsonl" 2>/dev/null | tail -20
fi

if [ -n "$VERIFY" ]; then
  if ! eval "$VERIFY" > "$LOG_STEM.verify.log" 2>&1; then
    echo "FAIL  $name — verify failed: $VERIFY"
    echo "      $LOG_STEM.verify.log"
    exit 3
  fi
fi

if ! grep -qiE '^\*\*Status:\*\*[[:space:]]*done' "$TICKET"; then
  echo "OPEN  $name — session ended without marking it done"
  exit 4
fi

echo "OK    $name"
exit 0
