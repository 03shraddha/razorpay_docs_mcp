"""
Razorpay Subscription Setup — Python / Flask

This is broken. Customers get:
  "Customer payment not allowed for the subscription at this stage"

Your job: find the bug and fix the subscription creation.

Real issue: https://github.com/razorpay/razorpay-android-sample-app/issues/154
"""

import razorpay
import hmac
import hashlib
from flask import Flask, request, jsonify

app = Flask(__name__)

client = razorpay.Client(
    auth=(
        "rzp_test_YOUR_KEY_ID",
        "YOUR_KEY_SECRET",
    )
)

PLAN_ID = "plan_YOUR_PLAN_ID"  # ₹999/month plan you created in the dashboard
WEBHOOK_SECRET = "YOUR_WEBHOOK_SECRET"


def create_subscription(customer_email: str, customer_contact: str) -> dict:
    """
    Create a monthly subscription for a new customer.
    BUG: total_count=1 is invalid — subscriptions require total_count > 1.
    Razorpay allows creation but silently blocks payment at checkout.
    """
    subscription = client.subscription.create({
        "plan_id": PLAN_ID,
        "total_count": 1,      # BUG: must be >= 2; use 12 for annual, 120 for 10-year
        "quantity": 1,
        "customer_notify": 1,
        "notes": {
            "email": customer_email,
        },
    })
    return subscription


def get_checkout_options(subscription_id: str, customer_email: str, customer_contact: str) -> dict:
    """Options to pass to Razorpay Checkout on the frontend."""
    return {
        "key": "rzp_test_YOUR_KEY_ID",
        "subscription_id": subscription_id,
        "name": "My SaaS App",
        "description": "Monthly Subscription — ₹999/month",
        "prefill": {
            "email": customer_email,
            "contact": customer_contact,
        },
        # BUG: amount should NOT be passed when using subscription_id.
        # Razorpay derives amount from the plan. Passing it causes conflicts.
        "amount": 99900,
    }


@app.route("/create-subscription", methods=["POST"])
def create_subscription_endpoint():
    data = request.json
    subscription = create_subscription(
        customer_email=data["email"],
        customer_contact=data["contact"],
    )
    options = get_checkout_options(
        subscription_id=subscription["id"],
        customer_email=data["email"],
        customer_contact=data["contact"],
    )
    return jsonify({"subscription_id": subscription["id"], "checkout_options": options})


@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle subscription.charged events."""
    payload = request.get_data(as_text=True)
    signature = request.headers.get("X-Razorpay-Signature")

    # BUG: using key_secret instead of webhook_secret for verification
    expected = hmac.new(
        key=client.auth[1].encode(),  # BUG: should be WEBHOOK_SECRET, not API key secret
        msg=payload.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return jsonify({"error": "Invalid signature"}), 400

    event = request.json
    if event.get("event") == "subscription.charged":
        subscription_id = event["payload"]["subscription"]["entity"]["id"]
        payment_id = event["payload"]["payment"]["entity"]["id"]
        print(f"Subscription charged: {subscription_id}, payment: {payment_id}")
        # Update your database here...

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
