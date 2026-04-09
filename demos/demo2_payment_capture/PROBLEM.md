# Demo 2 — Payments Stuck in "Authorized" State, Never Captured

## Your situation

You built a checkout flow for an e-commerce platform. Orders are created, customers pay, Razorpay's checkout UI says "Payment Successful" — but when you check your Razorpay dashboard, payments are sitting in **"authorized"** state instead of **"captured"**. Revenue isn't actually settling.

You've been debugging for a day. You tried setting `payment_capture: 1` on the order. Didn't help. You tried calling the capture API manually — it throws a 400 error claiming the payment ID doesn't exist.

## The broken code

See `broken_capture.js` in this directory.

## Your task

1. Identify why payments are stuck in "authorized" state.
2. Fix the order creation so auto-capture works correctly — OR implement the manual capture flow correctly if auto-capture isn't the right pattern here.
3. Make sure the capture API call uses the right parameters.

## Constraints

- Node.js backend
- Using the `razorpay` npm package v2.x
- Payment amount: ₹500 (50000 paise)
- You want to capture immediately after payment authorization

## What "working" looks like

- Orders are created correctly with proper capture settings
- After a payment is authorized, it transitions to "captured" state
- Settlement proceeds normally
