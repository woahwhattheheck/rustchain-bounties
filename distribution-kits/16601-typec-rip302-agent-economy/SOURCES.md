# Sources and claim map

Canonical source repository: `Scottcjn/Rustchain`  
Pinned source commit: `aa584b344a766f6c0f8613ba7198d1cc7ffbae35`

Primary file:  
https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/rip302_agent_economy.py

Secondary demo reference:  
https://github.com/Scottcjn/Rustchain/blob/aa584b344a766f6c0f8613ba7198d1cc7ffbae35/agent_sdk_demo.py

## Claim map

### “RIP-302 code turns RTC into a job-marketplace payment flow for agents.”
The module docstring says RIP-302 transforms RTC from a mining reward token into native currency for an autonomous agent-to-agent job marketplace.

### “Posting locks the reward plus a five-percent platform fee in internal escrow.”
In `rip302_agent_economy.py`:
- `PLATFORM_FEE_RATE = 0.05`
- `ESCROW_WALLET = "agent_escrow"`
- `platform_fee_i64 = int(reward_i64 * PLATFORM_FEE_RATE)`
- `escrow_i64 = reward_i64 + platform_fee_i64`
- posting debits the poster and credits `ESCROW_WALLET` before inserting the open job.

### “The lifecycle includes open, claimed, delivered, completed.”
The source declares the status constants `STATUS_OPEN`, `STATUS_CLAIMED`, `STATUS_DELIVERED`, and `STATUS_COMPLETED`, and the associated routes transition jobs through those states.

### “Acceptance pays the worker and routes the platform fee separately.”
The `/agent/jobs/<job_id>/accept` route is explicitly labeled “Accept delivery (releases escrow)”. Its successful JSON response reports `status: completed`, `reward_paid_rtc`, and `platform_fee_rtc`; the implementation adjusts the worker and platform-fee balances from escrow before committing.

### “Expired open or claimed jobs have a refund path.”
`_expire_refundable_job` only handles `open` or `claimed` jobs past `expires_at`, changes their status to `expired`, calls `_refund_escrow`, updates reputation, and logs the expiration. The module constants set a default TTL of seven days and a maximum of thirty days.

### “The code tracks marketplace reputation/accounting.”
The `agent_reputation` table includes posted/completed/disputed/expired counts, total RTC paid/earned, average rating, rating count, and activity timestamps.

## Deliberately not claimed

This package does **not** claim that:
- every deployed RustChain node is running this exact commit;
- every live Agent Economy transaction is independently verified here;
- the escrow mechanism is trustless or a smart contract;
- RIP-302 is free of security defects;
- RTC has any guaranteed external price, profit, or liquidity.

Those statements would require evidence beyond the pinned implementation source and are intentionally excluded.
