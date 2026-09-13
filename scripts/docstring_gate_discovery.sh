#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Fail-closed candidate discovery for the scheduled docstring-bounty sweep.
#
# A failed GitHub search is not evidence that there are zero claims to process.
# Keep the raw CLI diagnostic suppressed so authentication/provider details are
# never echoed into Actions logs; emit only a bounded, operator-safe error.
set -uo pipefail

: "${GH_REPO:?GH_REPO is required}"

search_claims() {
  local kind="$1"
  local query="$2"
  local result

  if ! result=$(gh api -X GET search/issues \
      -f "q=${query}" \
      -f per_page=60 \
      --jq '.items[].number' 2>/dev/null); then
    echo "::error title=Docstring gate candidate discovery failed::could not enumerate ${kind} claims; scheduled adjudication is incomplete" >&2
    return 1
  fi
  printf '%s\n' "$result"
}

held=$(search_claims \
  "awaiting-merge" \
  "repo:${GH_REPO} is:issue is:open label:awaiting-merge") || exit 1
fresh=$(search_claims \
  "fresh" \
  "repo:${GH_REPO} is:issue is:open -label:bounty-eligible -label:awaiting-merge -label:needs-human docstring") || exit 1

printf '%s\n%s\n' "$held" "$fresh" | sed '/^$/d' | sort -un
