# Demo 3 — Presenter Reference

## Bugs planted (real issues from GitHub)

| # | Bug | Source |
|---|-----|--------|
| 1 | `total_count: 1` — subscriptions require `total_count >= 2`. Silently blocks payment at checkout with cryptic error | razorpay-android-sample-app #154 |
| 2 | `amount` passed to checkout options alongside `subscription_id` — conflicts with plan-defined amount | Razorpay docs |
| 3 | API key secret used for webhook signature instead of webhook secret | razorpay-python #286, razorpay-php #48 |
| 4 | `hmac.new()` — Python's hmac module uses `hmac.new()` not `hmac.HMAC()`, but the signature is `hmac.new(key, msg, digestmod)` — correct here, but easy to get wrong | — |

## What the MCP should return

Search 1: `"subscription total_count recurring payment"`

Docs return: subscription creation parameters — `total_count` minimum value, what it controls, valid ranges.

Search 2: `"subscription checkout options subscription_id amount"`

Docs return: when using `subscription_id` in checkout, `amount` is derived from the plan — do not pass it.

## Fixed code

```python
subscription = client.subscription.create({
    "plan_id": PLAN_ID,
    "total_count": 12,     # 12 monthly billing cycles (1 year)
    "quantity": 1,
    "customer_notify": 1,
})

# Checkout options — NO amount field when subscription_id is set
options = {
    "key": "rzp_test_YOUR_KEY_ID",
    "subscription_id": subscription["id"],
    "name": "My SaaS App",
    "description": "Monthly — ₹999/month",
    "prefill": {"email": email, "contact": contact},
    # amount intentionally omitted
}
```

## Demo talking points

- "This error appears nowhere in the error message — Razorpay says 'payment not allowed at this stage' not 'total_count is invalid'"
- "The model has never seen this constraint in training data — it doesn't exist in any popular blog post or Stack Overflow answer"
- "The MCP returns the subscription API docs with total_count requirements in the first result — 30 seconds vs 2 hours of debugging"
- "This is the exact pattern this MCP was built for: silent constraints that only exist in official docs"
