/**
 * Razorpay Payment Capture — Node.js
 *
 * This is broken. Payments get stuck in "authorized" state.
 * The manual capture call throws: BAD_REQUEST_ERROR "The id provided does not exist"
 * Your job: find the bugs and fix the capture flow.
 *
 * Real issue: https://github.com/razorpay/razorpay-node/issues/42
 *             https://github.com/razorpay/razorpay-python/issues/131
 */

const Razorpay = require('razorpay');

const razorpay = new Razorpay({
  key_id: process.env.RAZORPAY_KEY_ID,
  key_secret: process.env.RAZORPAY_KEY_SECRET,
});

// Step 1: Create an order
async function createOrder(amountInRupees) {
  const order = await razorpay.orders.create({
    amount: amountInRupees * 100, // paise
    currency: 'INR',
    receipt: `receipt_${Date.now()}`,
    // BUG: payment_capture is not set — payments will require manual capture
    // but developer expects auto-capture
  });
  return order;
}

// Step 2: After checkout, capture the payment
// Called with the payment object from the Razorpay checkout callback
async function capturePayment(paymentData) {
  // BUG: paymentData is the full checkout response object,
  // but capture() expects a plain string payment ID
  // razorpay-node issue #42: passing object causes SDK to serialize it as "[object Object]"
  const captured = await razorpay.payments.capture(
    paymentData,           // BUG: should be paymentData.razorpay_payment_id (a string)
    paymentData.amount     // BUG: amount is undefined here — wrong property name
  );

  return captured;
}

// Step 3: Verify payment signature (called from your webhook or return URL handler)
async function verifyAndCapture(req) {
  const { razorpay_order_id, razorpay_payment_id, razorpay_signature } = req.body;

  // Signature check omitted for brevity — let's focus on capture

  const payment = await razorpay.payments.fetch(razorpay_payment_id);

  if (payment.status === 'authorized') {
    // BUG: capture() second argument should be amount in paise (integer),
    // but developer passes rupees (float), causing amount mismatch
    await capturePayment(payment); // passes whole payment object, not the ID string
  }
}

module.exports = { createOrder, capturePayment, verifyAndCapture };
