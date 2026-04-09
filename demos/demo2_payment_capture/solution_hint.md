# Demo 2 — Presenter Reference

## Bugs planted (real issues from GitHub)

| # | Bug | Source |
|---|-----|--------|
| 1 | No `payment_capture: 1` on order — payments require manual capture but flow assumes auto | razorpay-python #131 |
| 2 | `capturePayment(paymentData)` passes full object to `.capture()` — SDK silently uses `[object Object]` as the ID | razorpay-node #42 |
| 3 | Amount passed as rupees (float) to capture — should be paise (integer) | razorpay-node #42 comments |

## What the MCP should return

Search: `"capture payment after authorization order creation"`

The docs will return:
- Order creation: `payment_capture: 1` auto-captures on authorization
- Manual capture: `payments.capture(payment_id_string, amount_in_paise)`
- The 2-step model: authorized → captured is explicit, not automatic unless set

## Fixed code (option A: auto-capture)

```js
const order = await razorpay.orders.create({
  amount: 50000,  // paise
  currency: 'INR',
  receipt: `receipt_${Date.now()}`,
  payment_capture: 1,  // auto-captures on authorization
});
```

## Fixed code (option B: manual capture)

```js
// payment_id must be a plain string
const captured = await razorpay.payments.capture(
  razorpay_payment_id,   // string from checkout callback
  50000                  // amount in paise — must match original order amount
);
```

## Demo talking points

- "The authorized → captured distinction is unique to Razorpay — models trained on Stripe or PayPal docs get this wrong every time"
- "The object-vs-string bug is invisible — no type error, no crash, just a 400 saying 'payment not found'"
- "Three lines from the docs and the whole flow is clear — payment_capture:1 on order creation is the simplest path"
