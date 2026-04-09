# End-to-End Demo Scenarios

Three real bugs from real GitHub issues — reproduced as minimal broken implementations. Each one demonstrates a case where an AI coding agent using training data alone would write broken Razorpay code with full confidence, and the MCP fixes it in seconds.

---

## How to run a demo

**Prerequisites:**
1. MCP server running and registered with your Claude Code / Cursor session
2. Fresh Claude Code session with the MCP active (so the agent starts with no Razorpay-specific context)

**Steps:**
1. Open a fresh Claude Code session
2. Copy-paste the `PROBLEM.md` from the demo folder as your first message
3. Watch the agent:
   - Call `search_razorpay_docs` to look up the relevant API
   - Read the broken code file
   - Identify the bugs using the doc content
   - Fix the code with citations

**Presenter note:** Each `solution_hint.md` lists the exact bugs planted, the MCP search that surfaces them, and talking points. Read it before the demo.

---

## Demo 1 — Webhook Signature Verification Always Fails (Node.js)

**Real issue:** [razorpay-node #434](https://github.com/razorpay/razorpay-node/issues/434), [razorpay-php #48](https://github.com/razorpay/razorpay-php/issues/48)

**The trap:** `express.json()` parses the body before the webhook handler. `JSON.stringify(req.body)` re-encodes it — but Razorpay signed the original bytes. Plus the developer is using the API key secret instead of the webhook-specific secret.

**Why models get this wrong:** The `JSON.stringify(req.body)` pattern appears in thousands of Express tutorials. The distinction between API key secret and webhook secret is nowhere in generic Express/Razorpay blog posts.

```
demos/demo1_webhook_verification/
  PROBLEM.md          ← paste this into Claude Code
  broken_webhook.js   ← the code to fix
  solution_hint.md    ← presenter reference
```

---

## Demo 2 — Payments Stuck in "Authorized", Never Captured (Node.js)

**Real issue:** [razorpay-node #42](https://github.com/razorpay/razorpay-node/issues/42), [razorpay-python #131](https://github.com/razorpay/razorpay-python/issues/131)

**The trap:** Missing `payment_capture: 1` on order creation. Manual capture call passes a full object where the SDK expects a plain string payment ID — silently serializes as `[object Object]`, returns "payment not found".

**Why models get this wrong:** Stripe auto-captures by default. Razorpay's two-step authorized → captured model is Razorpay-specific behavior that models trained on Stripe patterns get wrong.

```
demos/demo2_payment_capture/
  PROBLEM.md          ← paste this into Claude Code
  broken_capture.js   ← the code to fix
  solution_hint.md    ← presenter reference
```

---

## Demo 3 — Subscription Error: "Customer payment not allowed at this stage" (Python)

**Real issue:** [razorpay-android-sample-app #154](https://github.com/razorpay/razorpay-android-sample-app/issues/154)

**The trap:** `total_count: 1` is silently invalid — Razorpay subscriptions require `total_count >= 2`. The subscription is created without error, but payment is blocked at checkout with a cryptic message. Additionally, passing `amount` in checkout options when using `subscription_id` causes a conflict.

**Why models get this wrong:** The constraint isn't in any error message, isn't in any blog post, and wasn't in training data. It's only in the official API docs. This is the canonical example of the MCP's value.

```
demos/demo3_subscription_setup/
  PROBLEM.md              ← paste this into Claude Code
  broken_subscription.py  ← the code to fix
  solution_hint.md        ← presenter reference
```

---

## What the interviewer sees

Each demo follows the same arc:

1. **Problem in:** Real bug from a real GitHub issue. Developer frustrated for hours.
2. **Agent reads PROBLEM.md** — understands the task, no Razorpay-specific knowledge yet.
3. **Agent calls `search_razorpay_docs`** — gets official docs with exact constraints.
4. **Agent reads broken code** — cross-references against doc content.
5. **Agent fixes it** — with a citation to `razorpay.com/docs/...` in the response.
6. **Fix is verifiably correct** — click the URL, it's the official Razorpay page.

Without the MCP: the agent writes code that looks right, passes quick review, and breaks silently in production.  
With the MCP: 30 seconds to the right answer with a citable source.
