# Demo 3 — Subscription Payment Blocked: "Customer payment not allowed at this stage"

## Your situation

You're building a SaaS app with monthly billing using Razorpay Subscriptions. You created the subscription plan, created a subscription, passed the `subscription_id` to the checkout — and your customer gets this error the moment they try to pay:

```
Customer payment not allowed for the subscription at this stage
```

You Googled it. Nothing. You checked the Razorpay docs. The setup looks exactly like the example. The subscription ID is valid — you can see it in the dashboard. But it refuses to let the customer pay.

## The broken code

See `broken_subscription.py` in this directory.

## Your task

1. Find out why the subscription is blocking payment.
2. Fix the subscription creation so the checkout flow works end-to-end.
3. Add a basic webhook handler for `subscription.charged` events.

## Constraints

- Python backend (Flask)
- Using the `razorpay` Python SDK
- Monthly billing plan: ₹999/month
- Customer should be able to pay immediately (no trial period needed)

## What "working" looks like

- Subscription is created in a state that allows immediate payment
- Customer can complete payment through Razorpay Checkout
- `subscription.charged` webhook fires and updates your database
