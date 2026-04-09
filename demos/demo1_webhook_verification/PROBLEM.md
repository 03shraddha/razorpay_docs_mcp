# Demo 1 — Webhook Signature Verification Always Fails

## Your situation

You're a backend developer at a SaaS company. You just integrated Razorpay payments and set up a webhook endpoint to handle `payment.captured` events. Your webhook handler passes all your unit tests.

But in production, **every single webhook request is rejected** with "Invalid signature." Payments are going through on Razorpay's side — your orders table just never gets updated.

You've been staring at this for 2 hours. The code looks right to you.

## The broken code

See `broken_webhook.js` in this directory.

## Your task

1. Figure out what's wrong with the webhook handler.
2. Fix it so signatures verify correctly.
3. Make sure the fix handles the raw body correctly for Express apps.

## Constraints

- Node.js / Express backend
- Using the `razorpay` npm package
- The webhook secret is configured in your Razorpay Dashboard under Settings → Webhooks

## What "working" looks like

- `POST /webhook` returns `200 OK` for valid Razorpay webhook payloads
- `POST /webhook` returns `400` for tampered/invalid payloads
- The `payment.captured` event triggers an order status update in the database
