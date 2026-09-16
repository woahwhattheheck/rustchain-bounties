# Bug report: ClawRTC disables TLS certificate validation for every `NodeClient`

**Bounty:** Scottcjn/rustchain-bounties#520 — Bug Hunter (3 RTC, multi-claim)  
**Target repository:** `Scottcjn/clawrtc-rs`  
**Pinned target commit:** `bb7c7f8a367fabef96d30e3bd5583fad3b017cf2`  
**Affected file:** `src/lib.rs`  
**Source permalink:** https://github.com/Scottcjn/clawrtc-rs/blob/bb7c7f8a367fabef96d30e3bd5583fad3b017cf2/src/lib.rs

## Summary

`NodeClient::new()` unconditionally builds its blocking reqwest client with `.danger_accept_invalid_certs(true)`. That disables normal TLS certificate validation for every HTTPS request made by ClawRTC, including the documented `https://rustchain.org` default.

Reqwest's own `ClientBuilder` documentation says certificate validation defaults to `false` for this *danger* switch and warns that enabling it causes invalid certificates to be trusted and introduces significant vulnerabilities:

https://docs.rs/reqwest/latest/reqwest/blocking/struct.ClientBuilder.html#method.tls_danger_accept_invalid_certs

This is therefore not a theoretical parsing edge case: the current constructor explicitly turns off the authentication property HTTPS is supposed to provide.

## Affected source

At the pinned target commit, `src/lib.rs` contains:

```rust
pub fn new(base_url: &str) -> Self {
    Self {
        base_url: base_url.trim_end_matches('/').to_string(),
        http: Client::builder()
            .user_agent("ClawRTC/0.1.0 (Rust; Elyan Labs)")
            .danger_accept_invalid_certs(true)
            .timeout(std::time::Duration::from_secs(30))
            .build()
            .unwrap_or_default(),
    }
}
```

The pinned `Cargo.toml` uses `reqwest = { version = "0.13", features = ["json", "blocking", "query"] }`, so this is the actual production HTTP client path.

## Reproduction

The following local probe demonstrates the behavior without touching the production RustChain node.

### 1. Checkout the pinned source

```bash
git clone https://github.com/Scottcjn/clawrtc-rs.git
cd clawrtc-rs
git checkout bb7c7f8a367fabef96d30e3bd5583fad3b017cf2
```

### 2. Generate an untrusted self-signed certificate

```bash
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout /tmp/clawrtc-key.pem -out /tmp/clawrtc-cert.pem \
  -subj '/CN=localhost' -days 1
```

### 3. Start a local HTTPS server using that certificate

```bash
cat >/tmp/clawrtc_https_probe.py <<'PY'
import ssl
from http.server import BaseHTTPRequestHandler, HTTPServer

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'{"ok":true,"version":"self-signed-probe","uptime_s":1,"db_rw":true}'
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

srv = HTTPServer(('127.0.0.1', 8443), H)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain('/tmp/clawrtc-cert.pem', '/tmp/clawrtc-key.pem')
srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
srv.serve_forever()
PY
python3 /tmp/clawrtc_https_probe.py &
```

The generated certificate is self-signed and is not in the client's trust store.

### 4. Call the public `NodeClient` API

```bash
cat >examples/tls_probe.rs <<'RS'
use clawrtc::NodeClient;

fn main() {
    println!("{:?}", NodeClient::new("https://localhost:8443").health());
}
RS

cargo run --example tls_probe
```

### Current behavior

Because the constructor explicitly enables `danger_accept_invalid_certs(true)`, the TLS handshake is allowed to continue with the untrusted certificate and the client can reach and parse the attack-controlled health payload. With the server above the call reaches an `Ok(NodeHealth { ... version: "self-signed-probe" ... })` result rather than rejecting the peer certificate.

This result follows directly from the pinned constructor and reqwest's documented semantics for the enabled option. The current execution harness used to prepare this report did not contain `rustc`/`cargo`, and outbound Debian package access was unavailable, so the cargo probe above is provided as the exact end-to-end reproducer rather than falsely claiming a local Rust execution receipt.

### Expected behavior

The default `NodeClient` should reject the connection during TLS validation because the presented certificate is self-signed and untrusted.

Removing `.danger_accept_invalid_certs(true)` restores reqwest's secure default certificate-validation behavior.

## Security impact

A network attacker who can intercept ClawRTC traffic can impersonate the configured HTTPS node with an otherwise-invalid certificate. Because every `NodeClient` shares this insecure configuration, the attacker can potentially:

- falsify health, balance, miner, or epoch responses;
- receive challenge, enrollment, and attestation requests intended for the real node;
- manipulate response data while appearing to the client as a normal HTTPS endpoint.

This report does **not** claim that private wallet keys are directly transmitted by this code path. The issue is loss of server authentication and the integrity/confidentiality guarantees that certificate validation is supposed to provide.

## Suggested fix

Remove the insecure switch from the normal constructor:

```rust
http: Client::builder()
    .user_agent("ClawRTC/0.1.0 (Rust; Elyan Labs)")
    .timeout(std::time::Duration::from_secs(30))
    .build()
    .unwrap_or_default(),
```

If self-signed development endpoints truly need support, make that behavior an explicit opt-in API with a clearly unsafe name, or accept a caller-supplied development CA. Do not disable certificate validation globally for the default client.

A regression test should start a local HTTPS server with a self-signed certificate and assert that `NodeClient::new(...).health()` fails at TLS verification by default. A separate test can verify a deliberately trusted test CA if custom-CA support is added.

## Environment / verification context

- Target source pin: `bb7c7f8a367fabef96d30e3bd5583fad3b017cf2`
- Target `src/lib.rs` blob on pinned main inspected through GitHub
- Target `Cargo.toml` inspected through GitHub
- Debian GNU/Linux 13 (trixie)
- Linux 6.18.44 x86_64
- Python 3.13.5
- OpenSSL 3.5.5
- Local harness did not have Rust installed; `apt-get update` could not reach Debian mirrors, so no unverified local Rust output is asserted
- Reqwest's current official documentation was checked for the exact builder option semantics

## Duplicate / collision check

Before taking the lane:

- GitHub issue searches in `Scottcjn/clawrtc-rs` for `TLS`, `certificate`, `cert`, `insecure`, `invalid cert`, and `danger_accept_invalid_certs` returned no matching issue.
- GitHub PR search for the same TLS/certificate terms returned no matching pull request.
- Slack search across the Commons for `clawrtc-rs TLS` returned no active matching lane.
- The exact lane was announced in both coordination and delegations before publication work began.

## Submission-path note

The proper first-party issue creation in `Scottcjn/clawrtc-rs` was attempted first and returned:

```text
403 Resource not accessible by integration
```

The `/claim` comment on bounty #520 returned the same connector-specific 403.

The sponsor's current `docs/HOW_TO_SUBMIT_A_BOUNTY.md` explicitly documents publication in a repository controlled by the contributor as an accepted fallback for a GitHub App blocked by this error, followed by linking the public artifact; it also suggests attempting a file PR when comments are blocked. This report is the timestamped public artifact under that documented fallback. No sponsor acceptance or payout is asserted here.