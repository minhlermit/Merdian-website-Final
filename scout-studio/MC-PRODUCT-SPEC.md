# MC — product concept, not a live token

This document turns the current **Get MC** interface into an implementation brief. No contract address, supply, pricing, custody, subscription processor or entitlement service has been chosen. The UI never invents a wallet balance or starts a payment.

## Package ideas

| Tier | Access | Illustrative monthly MC | Proposed benefit |
|---|---|---:|---|
| Explorer | Free | 0 | Public six-hour candidate board and evidence reading. |
| Researcher | Premium | 300 | Targeted research jobs and memo history. |
| Studio | Team | 1,200 | Shared allocation, batch work and collaboration. |

Illustrative quotes displayed in the UI: targeted scan **4 MC**, deep investigation **18 MC**, full investor memo **30 MC**. These values are UX placeholders, not a sale offer or on-chain fee schedule. Set prices only after measuring the cost of actual Scout jobs and choosing an economic model.

## Intended customer flow

1. Connect wallet; separately sign in with a server-issued, one-use nonce bound to domain, chain, address and expiry. Server verifies the signature and issues a secure session. A changed address or chain invalidates the session.
2. Subscribe through the chosen billing provider or choose a wallet top-up. Show currency, amount, network, gas/approval implications and the exact MC delivered before any signature or transaction. No automatic wallet debit when MC runs out.
3. For a research command, show the exact MC quote and scope. User confirms. Reserve available MC against an idempotent job ID so concurrent jobs cannot overspend.
4. Run the original Scout pipeline and verify the output, completion gate and cost. On success, settle once and burn the quoted MC under the chosen token contract mechanism. On failure/cancellation, release the reservation; do not burn. Record tx hash and job receipt, and expose status to the user.
5. When the available amount is insufficient, pause the job and offer a new top-up with explicit wallet confirmation. Let the user cancel.

The premium monthly grant and direct wallet top-up need a single audited entitlement ledger, reconciliation and refund policy. Decide whether MC lives on-chain in users' wallets or in a custodial/off-chain account backed by on-chain burns. Those models have different gas, trust and compliance costs. The current UI intentionally does not choose one.

## Build gates before launch

- Specify contract address, decimals, chain, issuer, supply, mint/grant and burn authority; audit the contract and quote/burn code.
- Server-side sign-in (EIP-4361 style) with nonce replay prevention, domain binding, session expiry, CSRF protection and account-change handling.
- Metered job API with authentication, rate limits, idempotency keys, completion verification, reservation/burn/reversal ledger and monitoring.
- Subscription billing, wallet top-up checkout, receipts, tax/terms and failure/refund states.
- Fresh candidate publication after each six-hour Scout run, with snapshots labeled by source and time. Static hosting alone only resets the visible board; it does not produce live candidates.

The site currently implements only the interaction preview: injected wallet connection, a browser-local signature check, Robinhood Chain switch, clear MC package concepts, and the fictional research walkthrough. It contains no payment endpoints, private keys, token write calls or hidden token allocation.
