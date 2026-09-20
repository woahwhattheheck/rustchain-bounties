"""Beacon-facing RIP-302 Agent Economy tools.

The integration deliberately keeps signing keys out of model/tool arguments.
Signed job creation reads the Ed25519 private key from process environment and
only emits the public key, signature, nonce, and derived wallet address.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import secrets
from dataclasses import dataclass
from typing import Any, Callable, Mapping, MutableMapping, Optional
from urllib.parse import quote

import requests
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

DEFAULT_BASE_URL = "https://50.28.86.131"
PRIVATE_KEY_ENV = "RUSTCHAIN_AGENT_ECONOMY_PRIVATE_KEY_HEX"
CATEGORIES = {
    "research",
    "code",
    "video",
    "audio",
    "writing",
    "translation",
    "data",
    "design",
    "testing",
    "other",
}

ACTION_SCHEMAS: dict[str, dict[str, Any]] = {
    "browse_jobs": {
        "description": "Browse RIP-302 Agent Economy jobs.",
        "properties": {
            "status": {"type": "string", "default": "open"},
            "category": {"type": ["string", "null"]},
            "min_reward": {"type": "number", "minimum": 0},
            "limit": {"type": "integer", "minimum": 0, "maximum": 100},
            "offset": {"type": "integer", "minimum": 0},
        },
    },
    "get_job": {
        "description": "Fetch one Agent Economy job and its activity.",
        "properties": {"job_id": {"type": "string"}},
        "required": ["job_id"],
    },
    "post_job": {
        "description": (
            "Post a signed Agent Economy job. The signing key is read from "
            f"the {PRIVATE_KEY_ENV} environment variable and is never a tool argument."
        ),
        "properties": {
            "title": {"type": "string", "minLength": 5},
            "description": {"type": "string", "minLength": 20},
            "reward_rtc": {"type": "number", "minimum": 0.01, "maximum": 10000},
            "category": {"type": "string", "enum": sorted(CATEGORIES)},
            "ttl_seconds": {"type": "integer", "minimum": 1},
            "tags": {"type": "array", "items": {"type": "string"}},
            "poster_wallet": {"type": ["string", "null"]},
        },
        "required": ["title", "description", "reward_rtc"],
    },
    "claim_job": {
        "description": "Claim an open Agent Economy job for a worker wallet.",
        "properties": {
            "job_id": {"type": "string"},
            "worker_wallet": {"type": "string"},
        },
        "required": ["job_id", "worker_wallet"],
    },
    "deliver_job": {
        "description": "Submit a deliverable URL and/or result summary for a claimed job.",
        "properties": {
            "job_id": {"type": "string"},
            "worker_wallet": {"type": "string"},
            "deliverable_url": {"type": ["string", "null"]},
            "deliverable_hash": {"type": ["string", "null"]},
            "result_summary": {"type": ["string", "null"]},
        },
        "required": ["job_id", "worker_wallet"],
    },
    "get_reputation": {
        "description": "Read Agent Economy reputation for a wallet.",
        "properties": {"wallet": {"type": "string"}},
        "required": ["wallet"],
    },
    "get_stats": {
        "description": "Read Agent Economy marketplace statistics.",
        "properties": {},
    },
}


class AgentEconomyError(RuntimeError):
    """Base error for the Beacon Agent Economy integration."""


class AgentEconomyHTTPError(AgentEconomyError):
    """HTTP failure with the complete decoded server body preserved."""

    def __init__(self, *, status: int, path: str, body: Any):
        self.status = status
        self.path = path
        self.body = body
        self.code = body.get("code") if isinstance(body, dict) else None
        server_error = body.get("error") if isinstance(body, dict) else None
        message = f"HTTP {status}"
        if self.code and server_error:
            message = f"{self.code}: {server_error}"
        elif server_error:
            message = str(server_error)
        super().__init__(f"RIP-302 {path}: {message}")


@dataclass(frozen=True)
class SigningIdentity:
    private_key: Ed25519PrivateKey
    public_key_hex: str
    wallet: str


def _require_text(value: str, name: str, min_len: int = 1) -> str:
    if not isinstance(value, str):
        raise AgentEconomyError(f"{name} must be a string")
    value = value.strip()
    if len(value) < min_len:
        raise AgentEconomyError(
            f"{name} must be at least {min_len} non-whitespace characters"
        )
    return value


def _reward(value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or value < 0.01 or value > 10_000:
        raise AgentEconomyError(
            "reward_rtc must be finite and between 0.01 and 10000"
        )
    return value


def _category(value: str) -> str:
    value = _require_text(value, "category").lower()
    if value not in CATEGORIES:
        raise AgentEconomyError(
            f"category must be one of: {', '.join(sorted(CATEGORIES))}"
        )
    return value


def rtc_address_from_public_key(public_key: bytes) -> str:
    """Derive the RustChain RTC address from the raw Ed25519 public key."""
    return "RTC" + hashlib.sha256(public_key).hexdigest()[:40]


def canonical_create_message(
    poster_wallet: str,
    category: str,
    reward_rtc: float,
    nonce: str,
) -> bytes:
    """Return the canonical RIP-302 signed-create byte string."""
    payload = {
        "action": "agent_post_job",
        "category": _category(category),
        "nonce": _require_text(nonce, "nonce"),
        "poster": _require_text(poster_wallet, "poster_wallet"),
        "reward_rtc": _reward(reward_rtc),
    }
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _identity_from_environment(
    environ: Mapping[str, str],
) -> SigningIdentity:
    raw = environ.get(PRIVATE_KEY_ENV, "").strip()
    if not raw:
        raise AgentEconomyError(
            f"signed job posting requires {PRIVATE_KEY_ENV} in the process environment"
        )
    try:
        key_bytes = bytes.fromhex(raw)
    except ValueError as exc:
        raise AgentEconomyError(f"{PRIVATE_KEY_ENV} must be hex") from exc
    if len(key_bytes) != 32:
        raise AgentEconomyError(
            f"{PRIVATE_KEY_ENV} must contain exactly 32 bytes"
        )
    private_key = Ed25519PrivateKey.from_private_bytes(key_bytes)
    public_key = private_key.public_key().public_bytes(
        Encoding.Raw, PublicFormat.Raw
    )
    return SigningIdentity(
        private_key=private_key,
        public_key_hex=public_key.hex(),
        wallet=rtc_address_from_public_key(public_key),
    )


class BeaconAgentEconomySkill:
    """Small Beacon-compatible tool surface for RIP-302 Agent Economy."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        timeout_s: float = 20.0,
        verify_tls: bool = True,
        session: Optional[requests.Session] = None,
        environ: Optional[Mapping[str, str]] = None,
        nonce_factory: Optional[Callable[[], str]] = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("RUSTCHAIN_AGENT_ECONOMY_URL")
            or DEFAULT_BASE_URL
        ).rstrip("/")
        if not self.base_url.startswith(("https://", "http://")):
            raise AgentEconomyError("base_url must use http or https")
        if not math.isfinite(float(timeout_s)) or float(timeout_s) <= 0:
            raise AgentEconomyError("timeout_s must be positive and finite")
        self.timeout_s = float(timeout_s)
        self.verify_tls = bool(verify_tls)
        self.session = session or requests.Session()
        self.environ = environ if environ is not None else os.environ
        self.nonce_factory = nonce_factory or (lambda: secrets.token_hex(16))
        self.session.headers.update(
            {"User-Agent": "Beacon-Agent-Economy/0.1"}
        )

    @staticmethod
    def action_schemas() -> dict[str, dict[str, Any]]:
        """Return action declarations safe to expose to an agent."""
        return json.loads(json.dumps(ACTION_SCHEMAS))

    def invoke(
        self, action: str, **arguments: Any
    ) -> dict[str, Any]:
        """Invoke an allowlisted Agent Economy action by skill/tool name."""
        dispatch = {
            "browse_jobs": self.browse_jobs,
            "get_job": self.get_job,
            "post_job": self.post_job,
            "claim_job": self.claim_job,
            "deliver_job": self.deliver_job,
            "get_reputation": self.get_reputation,
            "get_stats": self.get_stats,
        }
        try:
            method = dispatch[action]
        except KeyError as exc:
            raise AgentEconomyError(
                f"unknown Agent Economy action: {action}"
            ) from exc
        return method(**arguments)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[MutableMapping[str, Any]] = None,
        json_body: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        response = self.session.request(
            method,
            f"{self.base_url}{path}",
            params=params,
            json=json_body,
            timeout=self.timeout_s,
            verify=self.verify_tls,
        )
        try:
            body: Any = response.json()
        except Exception:
            body = {"raw": response.text}
        if response.status_code >= 400:
            raise AgentEconomyHTTPError(
                status=response.status_code, path=path, body=body
            )
        if not isinstance(body, dict):
            raise AgentEconomyError(
                f"RIP-302 {path}: expected a JSON object response"
            )
        return body

    def browse_jobs(
        self,
        status: str = "open",
        category: Optional[str] = None,
        min_reward: float = 0.0,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        status = _require_text(status, "status")
        min_reward = float(min_reward)
        if not math.isfinite(min_reward) or min_reward < 0:
            raise AgentEconomyError(
                "min_reward must be non-negative and finite"
            )
        if not isinstance(limit, int) or not 0 <= limit <= 100:
            raise AgentEconomyError(
                "limit must be an integer from 0 to 100"
            )
        if not isinstance(offset, int) or offset < 0:
            raise AgentEconomyError(
                "offset must be a non-negative integer"
            )
        params: dict[str, Any] = {
            "status": status,
            "min_reward": min_reward,
            "limit": limit,
            "offset": offset,
        }
        if category is not None:
            params["category"] = _category(category)
        return self._request("GET", "/agent/jobs", params=params)

    def get_job(self, job_id: str) -> dict[str, Any]:
        job = quote(_require_text(job_id, "job_id"), safe="")
        return self._request("GET", f"/agent/jobs/{job}")

    def post_job(
        self,
        title: str,
        description: str,
        reward_rtc: float,
        category: str = "other",
        ttl_seconds: int = 604_800,
        tags: Optional[list[str]] = None,
        poster_wallet: Optional[str] = None,
    ) -> dict[str, Any]:
        """Post a signed job; the Ed25519 private key comes from environment."""
        title = _require_text(title, "title", 5)
        description = _require_text(description, "description", 20)
        reward_rtc = _reward(reward_rtc)
        category = _category(category)
        if not isinstance(ttl_seconds, int) or ttl_seconds <= 0:
            raise AgentEconomyError(
                "ttl_seconds must be a positive integer"
            )
        tags = [] if tags is None else list(tags)
        if not all(
            isinstance(tag, str) and tag.strip() for tag in tags
        ):
            raise AgentEconomyError(
                "tags must contain non-empty strings"
            )

        identity = _identity_from_environment(self.environ)
        if poster_wallet is None:
            poster_wallet = identity.wallet
        else:
            poster_wallet = _require_text(
                poster_wallet, "poster_wallet"
            )
            if (
                poster_wallet.startswith("RTC")
                and poster_wallet.lower()
                != identity.wallet.lower()
            ):
                raise AgentEconomyError(
                    "poster_wallet does not match the configured signing key"
                )

        nonce = _require_text(self.nonce_factory(), "nonce")
        message = canonical_create_message(
            poster_wallet, category, reward_rtc, nonce
        )
        signature = identity.private_key.sign(message).hex()
        body = {
            "poster_wallet": poster_wallet,
            "title": title,
            "description": description,
            "reward_rtc": reward_rtc,
            "category": category,
            "ttl_seconds": ttl_seconds,
            "tags": tags,
            "nonce": nonce,
            "poster_pubkey": identity.public_key_hex,
            "poster_sig": signature,
        }
        return self._request(
            "POST", "/agent/jobs", json_body=body
        )

    def claim_job(
        self, job_id: str, worker_wallet: str
    ) -> dict[str, Any]:
        job = quote(_require_text(job_id, "job_id"), safe="")
        body = {
            "worker_wallet": _require_text(
                worker_wallet, "worker_wallet"
            )
        }
        return self._request(
            "POST", f"/agent/jobs/{job}/claim", json_body=body
        )

    def deliver_job(
        self,
        job_id: str,
        worker_wallet: str,
        deliverable_url: Optional[str] = None,
        deliverable_hash: Optional[str] = None,
        result_summary: Optional[str] = None,
    ) -> dict[str, Any]:
        if not deliverable_url and not result_summary:
            raise AgentEconomyError(
                "deliverable_url or result_summary is required"
            )
        job = quote(_require_text(job_id, "job_id"), safe="")
        body: dict[str, Any] = {
            "worker_wallet": _require_text(
                worker_wallet, "worker_wallet"
            )
        }
        if deliverable_url:
            body["deliverable_url"] = _require_text(
                deliverable_url, "deliverable_url"
            )
        if deliverable_hash:
            body["deliverable_hash"] = _require_text(
                deliverable_hash, "deliverable_hash"
            )
        if result_summary:
            body["result_summary"] = _require_text(
                result_summary, "result_summary"
            )
        return self._request(
            "POST", f"/agent/jobs/{job}/deliver", json_body=body
        )

    def get_reputation(
        self, wallet: str
    ) -> dict[str, Any]:
        wallet = quote(_require_text(wallet, "wallet"), safe="")
        return self._request(
            "GET", f"/agent/reputation/{wallet}"
        )

    def get_stats(self) -> dict[str, Any]:
        return self._request("GET", "/agent/stats")
