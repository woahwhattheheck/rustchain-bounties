# Bug Hunter report: Grazer emits truncated, non-NIP-19 Nostr event URLs

## Bounty

- Sponsor bounty: `Scottcjn/rustchain-bounties#520` — Bug Hunter, 3 RTC, multi-claim
- Target repository: `Scottcjn/grazer-skill`
- Target commit tested: `1167938eb96c57eb8718c09b13b720fdd645fb1f`
- Target file: `grazer/nostr_grazer.py`
- Function: `_normalize_event()`
- Report status: public fallback artifact only; **no sponsor acceptance or payout is asserted**

## Summary

`_normalize_event()` throws away most of every Nostr event ID when it creates the user-facing event URL:

```python
"url": f"https://nostr.band/note{event_id[:8]}" if event_id else "",
```

A Nostr event ID is a 32-byte / 64-hex identifier. The code keeps only the first 8 hex characters (32 bits), discarding the remaining 28 bytes. It then prefixes those raw hex characters with `note`, but NIP-19 defines user-facing note IDs as **bech32 `note1...` identifiers derived from the full 32-byte event ID**.

The result is both lossy and non-standard: distinct Nostr events can normalize to the same URL, and the URL does not carry a valid NIP-19 note identifier.

## Deterministic reproduction

Environment:

- Linux x86_64
- Python 3.13.5
- Source pinned to `Scottcjn/grazer-skill@1167938eb96c57eb8718c09b13b720fdd645fb1f`
- Offline reproduction; no API/network dependency required

Two distinct valid-length event IDs with the same first eight hex characters are enough:

```python
from grazer.nostr_grazer import _normalize_event

first = "deadbeef" + "00" * 28
second = "deadbeef" + "11" * 28

print(len(first), first)
print(_normalize_event({"id": first})["url"])
print(len(second), second)
print(_normalize_event({"id": second})["url"])
print(
    _normalize_event({"id": first})["url"]
    == _normalize_event({"id": second})["url"]
)
```

Observed from the current implementation:

```text
64 deadbeef00000000000000000000000000000000000000000000000000000000
https://nostr.band/notedeadbeef
64 deadbeef11111111111111111111111111111111111111111111111111111111
https://nostr.band/notedeadbeef
True
```

The two different 256-bit event identities collapse to exactly the same exported URL.

## Expected behavior

A user-facing Nostr event link must preserve the complete event identity. For a NIP-19 note identifier, the full event ID should be bech32-encoded with the `note` prefix, producing a `note1...` value. NIP-19 is explicit that `note` represents note/event IDs:

- https://github.com/nostr-protocol/nips/blob/master/19.md

Using another documented nostr.band route would also be fine if it preserves the full event ID. The key requirement is that normalization must not discard 224 of the 256 identifier bits.

## User impact

- Grazer discovery/export results can contain Nostr URLs that do not identify the discovered event.
- Different events sharing a 32-bit prefix receive the same URL.
- Downstream agents or humans following the normalized URL cannot reliably navigate back to the source event.
- Any cache/deduplication keyed by the normalized URL can incorrectly merge distinct events.

This is a functional identity/linking bug; the reproduction does not require attacking a remote service.

## Existing test gap

`tests/test_new_plugins.py::test_normalize_nostr_event` checks content, pubkey, kind, hashtags, and only that `"nostr.band"` appears in `event["url"]`. It never verifies that the URL retains the event's full identity or that a NIP-19 identifier is valid. That allows the truncation to pass the test suite.

A useful regression test would construct two 64-hex event IDs with an identical 8-hex prefix and assert:

1. their normalized URLs differ;
2. each URL encodes the complete event identity;
3. if NIP-19 is used, the path identifier is a valid `note1...` encoding.

## Suggested repair

Encode `bytes.fromhex(event_id)` with a NIP-19/bech32 implementation and use the resulting full `note1...` identifier in the link, or use a documented full-ID nostr.band route. Validate malformed/non-64-hex IDs separately so a bad upstream record cannot turn into a misleading link.

## Duplicate check

Before publication, searches were run against current `Scottcjn/grazer-skill` issues and pull requests for Nostr event URL / `note1` / `event_id` / `nostr.band/note` reports. No report of this truncation/identity-collision defect was found. Slack coordination/delegation searches likewise found no owner for this exact lane.

## Submission-path receipt

A direct attempt to create the proper bug issue in `Scottcjn/grazer-skill` returned:

```text
403 Resource not accessible by integration
```

The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents publication in a controlled repository, followed by a link or file PR, as accepted fallback paths for this GitHub-App limitation. This file is the public, timestamped fallback artifact. A sponsor-side issue/comment still needs to be created through an authorized user/PAT (or another sponsor-documented route) before counting the 3 RTC as accepted.
