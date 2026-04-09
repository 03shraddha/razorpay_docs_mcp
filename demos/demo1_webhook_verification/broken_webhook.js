/**
 * Razorpay Webhook Handler — Express.js
 *
 * This is broken. Signatures always fail in production.
 * Your job: find the bugs and fix them.
 *
 * Real issue: https://github.com/razorpay/razorpay-node/issues/434
 *             https://github.com/razorpay/razorpay-php/issues/48
 */

const express = require('express');
const Razorpay = require('razorpay');

const app = express();

// BUG AREA: standard JSON body parser — processes body before webhook handler sees it
app.use(express.json());

const razorpay = new Razorpay({
  key_id: process.env.RAZORPAY_KEY_ID,
  key_secret: process.env.RAZORPAY_KEY_SECRET,  // BUG: this is the API secret, not the webhook secret
});

app.post('/webhook', (req, res) => {
  const signature = req.headers['x-razorpay-signature'];
  const webhookSecret = process.env.RAZORPAY_KEY_SECRET; // BUG: should be RAZORPAY_WEBHOOK_SECRET

  try {
    // BUG: req.body is already a parsed JS object here — JSON.stringify re-encodes it,
    // which may not match the exact bytes Razorpay signed (key ordering, whitespace, floats)
    const isValid = razorpay.webhooks.verify(
      JSON.stringify(req.body),
      signature,
      webhookSecret
    );

    if (!isValid) {
      console.log('Signature verification failed');
      return res.status(400).json({ error: 'Invalid signature' });
    }

    const event = req.body.event;

    if (event === 'payment.captured') {
      const payment = req.body.payload.payment.entity;
      console.log(`Payment captured: ${payment.id}, amount: ${payment.amount}`);
      // Update order status in database...
    }

    res.status(200).json({ status: 'ok' });
  } catch (err) {
    console.error('Webhook error:', err);
    res.status(500).json({ error: 'Internal error' });
  }
});

app.listen(3000, () => console.log('Listening on port 3000'));
