// parking-management/backend/src/webhooks/stripeWebhook.js
import crypto from 'crypto';
import express from 'express';
import { WebhookEventModel } from '../models/WebhookEvent.js';
import { logger } from '../utils/logger.js';
import { webhookQueueService } from './webhookQueue.js';

const router = express.Router();

// Stripe webhook endpoint
router.post('/stripe', express.raw({ type: 'application/json' }), async (req, res) => {
  try {
    const signature = req.headers['stripe-signature'];
    const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
    
    if (!signature) {
      logger.warn('No Stripe signature found in webhook request');
      return res.status(400).json({ error: 'Missing signature' });
    }

    // Verify webhook signature
    const payload = req.body;
    const isValid = verifyStripeSignature(payload, signature, webhookSecret);
    
    if (!isValid) {
      logger.warn('Invalid Stripe webhook signature');
      return res.status(401).json({ error: 'Invalid signature' });
    }

    // Parse event
    const event = JSON.parse(payload.toString());
    const eventId = event.id;
    const eventType = event.type;
    
    logger.info(`Received Stripe webhook: ${eventId}`, { eventType });

    // Check for duplicate webhook
    const existingEvent = await WebhookEventModel.findByEventId(eventId);
    if (existingEvent) {
      logger.warn(`Duplicate Stripe webhook: ${eventId}`);
      return res.status(200).json({ received: true, duplicate: true });
    }

    // Add to queue for processing
    await webhookQueueService.addWebhook({
      eventId,
      eventType,
      payload: event,
      source: 'stripe',
    });

    // Acknowledge receipt
    res.status(200).json({ 
      received: true, 
      eventId,
      eventType,
      queued: true,
    });

  } catch (error) {
    logger.error('Stripe webhook error:', error);
    res.status(500).json({ error: 'Webhook processing failed' });
  }
});

/**
 * Verify Stripe webhook signature
 */
function verifyStripeSignature(payload, signature, secret) {
  try {
    const timestamp = parseInt(signature.split(',')[0].split('=')[1]);
    const signatureHash = signature.split(',')[1].split('=')[1];
    
    const signedPayload = `${timestamp}.${payload.toString()}`;
    const expectedSignature = crypto
      .createHmac('sha256', secret)
      .update(signedPayload)
      .digest('hex');
    
    return crypto.timingSafeEqual(
      Buffer.from(signatureHash),
      Buffer.from(expectedSignature)
    );
  } catch (error) {
    logger.error('Signature verification error:', error);
    return false;
  }
}

export default router;