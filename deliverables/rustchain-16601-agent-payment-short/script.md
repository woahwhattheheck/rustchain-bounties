# Script

**Hook / first frame:** This is an AI agent paying another AI agent — without a checkout page.

Beacon's RustChain transport can create an Ed25519 wallet and derive an `RTC` address from its public key. The payment command is one line: `beacon rustchain pay <RTC address> 1.5 --memo "bounty: #21"`.

Under the hood, the client builds the sender, recipient, amount, memo, and nonce; serializes that data deterministically; signs it with Ed25519; then posts the signed payload to `/wallet/transfer/signed`.

The private key stays local. So an agent can put the job reference in the memo and send RTC programmatically.

Agent-to-agent coordination is already an economic protocol, not just chat.
