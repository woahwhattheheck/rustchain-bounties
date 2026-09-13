#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -uo pipefail

: "${GH_REPO:?GH_REPO is required}"

mode="${1:-}"
case "$mode" in
  held)
    query="repo:${GH_REPO} is:issue is:open label:awaiting-merge"
    ;;
  fresh)
    query="repo:${GH_REPO} is:issue is:open -label:bounty-eligible -label:awaiting-merge -label:needs-human docstring"
    ;;
  *)
    echo "usage: $0 {held|fresh}" >&2
    exit 64
    ;;
esac

timeout_seconds="${DOCSTRING_DISCOVERY_TIMEOUT_SECONDS:-45}"
max_error_bytes="${DOCSTRING_DISCOVERY_ERROR_BYTES:-2000}"
error_file="$(mktemp)"
trap 'rm -f "$error_file"' EXIT

rc=0
output="$(timeout "${timeout_seconds}s" gh api -X GET search/issues \
  -f "q=${query}" \
  -f per_page=60 \
  --jq '.items[].number' 2>"$error_file")" || rc=$?

if [ "$rc" -ne 0 ]; then
  echo "::error title=Docstring candidate discovery failed::${mode} GitHub search exited ${rc}; candidate set is unknown, refusing to report zero work." >&2
  if [ -s "$error_file" ]; then
    echo "gh stderr (bounded to ${max_error_bytes} bytes):" >&2
    head -c "$max_error_bytes" "$error_file" >&2
    echo >&2
  fi
  exit "$rc"
fi

printf '%s\n' "$output"
