# Demo 1 — Presenter Reference

## Bugs planted (real issues from GitHub)

| # | Bug | Source |
|---|-----|--------|
| 1 | `express.json()` parses body before webhook handler — raw bytes are gone | razorpay-node #434 |
| 2 | `JSON.stringify(req.body)` re-encodes parsed object — byte order/floats differ | Medium article, multiple SO posts |
| 3 | `RAZORPAY_KEY_SECRET` (API secret) used instead of `RAZORPAY_WEBHOOK_SECRET` | razorpay-php #48 |

## What the MCP should return

Search: `"webhook signature verification node.js raw body"`

The docs will return the webhooks page with:
- Explicit warning: capture raw body before any body-parser middleware
- Separate webhook secret (configured in Dashboard → Settings → Webhooks)
- `validateWebhookSignature(rawBody, signature, webhookSecret)` exact signature

## Fixed code pattern

```js
// 1. Capture raw body BEFORE JSON parsing
app.use('/webhook', express.raw({ type: 'application/json' }));

// 2. Use WEBHOOK secret (not API key secret)
const webhookSecret = process.env.RAZORPAY_WEBHOOK_SECRET;

// 3. Pass raw bytes as string, not re-serialized JSON
const isValid = Razorpay.validateWebhookSignature(
  req.body.toString(),   // raw body buffer → string
  signature,
  webhookSecret          // webhook-specific secret from Dashboard
);
```

## Demo talking points

- "The model would have written `JSON.stringify(req.body)` with total confidence — it's seen that pattern everywhere"
- "But Razorpay signs the exact bytes it sends. Re-encoding parsed JSON changes byte order and float representation"
- "The MCP returns the official docs with the raw body warning right at the top — no guessing"
- "The webhook secret vs API secret is a genuinely confusing distinction that the docs clarify in one sentence"
