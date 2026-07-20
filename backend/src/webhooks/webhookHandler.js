// parking-management/backend/src/webhooks/webhookHandler.js (Enhanced)
import { PrismaClient } from '@prisma/client';
import { logger } from '../utils/logger.js';
import { idempotencyService } from './idempotencyService.js';
import { paymentRecoveryService } from './paymentRecoveryService.js';
import { signatureVerifier } from './signatureVerifier.js';
import { webhookQueueService } from './webhookQueue.js';

const prisma = new PrismaClient();

export class WebhookHandler {
  /**
   * Handle incoming webhook with full validation
   */
  async handleWebhook(req, res) {
    try {
      // 1. Extract provider and raw body
      const provider = this.detectProvider(req);
      const rawBody = req.rawBody;
      const signature = req.headers[this.getSignatureHeader(provider)];

      // 2. Verify signature
      const isValid = await this.verifyWebhookSignature(
        provider,
        rawBody,
        signature,
        req.headers
      );

      if (!isValid) {
        logger.error('Webhook signature verification failed', {
          provider,
          ip: req.ip,
          headers: req.headers,
        });
        return res.status(401).json({
          error: 'INVALID_SIGNATURE',
          message: 'Webhook signature verification failed',
        });
      }

      // 3. Parse webhook event
      const event = this.parseEvent(rawBody, provider);
      
      // 4. Check idempotency
      const idempotentKey = event.id || event.eventId;
      const isDuplicate = await idempotencyService.checkIdempotency(
        idempotentKey,
        provider
      );

      if (isDuplicate) {
        logger.info(`Duplicate webhook received: ${idempotentKey}`);
        return res.status(200).json({
          received: true,
          duplicate: true,
          message: 'Webhook already processed',
        });
      }

      // 5. Store webhook event
      const webhookEvent = await this.storeWebhookEvent(provider, event);

      // 6. Process webhook
      const result = await this.processWebhookEvent(provider, event, webhookEvent);

      // 7. Mark as idempotent
      await idempotencyService.markIdempotent(idempotentKey, provider, {
        processed: true,
        timestamp: new Date().toISOString(),
        result,
      });

      // 8. Update webhook status
      await this.updateWebhookStatus(webhookEvent.id, 'COMPLETED');

      logger.info(`Webhook processed successfully: ${idempotentKey}`);
      
      return res.status(200).json({
        received: true,
        processed: true,
        eventId: idempotentKey,
        result,
      });

    } catch (error) {
      logger.error('Webhook handling error:', error);
      
      // Attempt recovery
      await this.handleWebhookFailure(error, req);
      
      // Return appropriate error response
      return res.status(500).json({
        error: 'PROCESSING_ERROR',
        message: 'Webhook processing failed',
      });
    }
  }

  /**
   * Detect webhook provider
   */
  detectProvider(req) {
    const userAgent = req.headers['user-agent'] || '';
    const signature = req.headers['stripe-signature'] || req.headers['paypal-auth-algo'];
    
    if (signature) {
      if (req.headers['stripe-signature']) return 'stripe';
      if (req.headers['paypal-auth-algo']) return 'paypal';
    }
    
    // Default to Stripe
    return 'stripe';
  }

  /**
   * Get signature header for provider
   */
  getSignatureHeader(provider) {
    const headers = {
      stripe: 'stripe-signature',
      paypal: 'paypal-auth-algo',
    };
    return headers[provider] || 'signature';
  }

  /**
   * Verify webhook signature
   */
  async verifyWebhookSignature(provider, payload, signature, headers) {
    try {
      // Validate headers first
      const hasValidHeaders = signatureVerifier.validateHeaders(headers, provider);
      if (!hasValidHeaders) {
        return false;
      }

      // Verify signature
      return signatureVerifier.verifySignature(
        provider,
        payload,
        signature,
        headers['timestamp'] || headers['x-request-timestamp']
      );

    } catch (error) {
      logger.error('Signature verification error:', error);
      return false;
    }
  }

  /**
   * Parse webhook event
   */
  parseEvent(rawBody, provider) {
    try {
      const event = JSON.parse(rawBody);
      
      // Normalize event structure
      return {
        id: event.id || event.eventId,
        type: event.type || event.eventType,
        data: event.data || event.payload,
        timestamp: event.created || event.timestamp || Date.now(),
        raw: event,
      };
    } catch (error) {
      logger.error('Event parsing error:', error);
      throw new Error('Invalid webhook payload');
    }
  }

  /**
   * Store webhook event in database
   */
  async storeWebhookEvent(provider, event) {
    try {
      return await prisma.webhookEvent.create({
        data: {
          source: provider,
          eventId: event.id,
          eventType: event.type,
          payload: event.raw,
          status: 'PENDING',
          retryCount: 0,
        },
      });
    } catch (error) {
      logger.error('Failed to store webhook event:', error);
      throw error;
    }
  }

  /**
   * Process webhook event
   */
  async processWebhookEvent(provider, event, webhookEvent) {
    // Route to appropriate handler based on event type
    switch (event.type) {
      case 'payment_intent.succeeded':
        return await this.handlePaymentSucceeded(event.data);
      case 'payment_intent.payment_failed':
        return await this.handlePaymentFailed(event.data);
      case 'charge.refunded':
        return await this.handleRefund(event.data);
      case 'customer.subscription.created':
        return await this.handleSubscriptionCreated(event.data);
      case 'customer.subscription.updated':
        return await this.handleSubscriptionUpdated(event.data);
      case 'customer.subscription.deleted':
        return await this.handleSubscriptionDeleted(event.data);
      default:
        logger.info(`Unhandled webhook type: ${event.type}`);
        return {
          handled: false,
          message: 'Unhandled webhook type',
        };
    }
  }

  /**
   * Update webhook status
   */
  async updateWebhookStatus(id, status, error = null) {
    try {
      await prisma.webhookEvent.update({
        where: { id },
        data: {
          status,
          processedAt: status === 'COMPLETED' ? new Date() : null,
          error,
          updatedAt: new Date(),
        },
      });
    } catch (error) {
      logger.error('Failed to update webhook status:', error);
    }
  }

  /**
   * Handle webhook failure
   */
  async handleWebhookFailure(error, req) {
    try {
      // Queue for retry
      await webhookQueueService.addWebhook({
        payload: req.rawBody,
        headers: req.headers,
        provider: this.detectProvider(req),
        attempts: 0,
      });

      // Log failure for monitoring
      logger.error('Webhook failure queued for retry:', {
        error: error.message,
        path: req.path,
        method: req.method,
      });

    } catch (retryError) {
      logger.error('Failed to queue webhook for retry:', retryError);
    }
  }

  /**
   * Handle payment succeeded event
   */
  async handlePaymentSucceeded(data) {
    const { id: paymentIntentId, object } = data;
    
    try {
      // Find payment
      const payment = await prisma.payment.findFirst({
        where: { stripeIntentId: paymentIntentId },
        include: {
          booking: {
            include: {
              user: true,
              parkingSpot: true,
            },
          },
        },
      });

      if (!payment) {
        logger.warn(`Payment not found for intent: ${paymentIntentId}`);
        return {
          processed: false,
          reason: 'Payment not found',
        };
      }

      // Update payment status
      await prisma.payment.update({
        where: { id: payment.id },
        data: {
          status: 'COMPLETED',
          stripePaymentId: object.charges?.data[0]?.id,
          updatedAt: new Date(),
        },
      });

      // Update booking status
      await prisma.booking.update({
        where: { id: payment.bookingId },
        data: {
          status: 'CONFIRMED',
          updatedAt: new Date(),
        },
      });

      // Update parking spot
      await prisma.parkingSpot.update({
        where: { id: payment.booking.parkingId },
        data: {
          status: 'OCCUPIED',
          updatedAt: new Date(),
        },
      });

      // Send confirmation (handle async)
      await this.sendConfirmation(payment.booking);

      return {
        processed: true,
        paymentId: payment.id,
        bookingId: payment.bookingId,
        status: 'COMPLETED',
      };

    } catch (error) {
      logger.error('Payment succeeded handling error:', error);
      throw error;
    }
  }

  /**
   * Handle payment failed event
   */
  async handlePaymentFailed(data) {
    const { id: paymentIntentId, object } = data;
    
    try {
      const payment = await prisma.payment.findFirst({
        where: { stripeIntentId: paymentIntentId },
        include: {
          booking: {
            include: {
              user: true,
            },
          },
        },
      });

      if (!payment) {
        logger.warn(`Payment not found for failed intent: ${paymentIntentId}`);
        return {
          processed: false,
          reason: 'Payment not found',
        };
      }

      // Update payment status
      await prisma.payment.update({
        where: { id: payment.id },
        data: {
          status: 'FAILED',
          updatedAt: new Date(),
        },
      });

      // Attempt recovery
      await paymentRecoveryService.recoverFailedPayment(payment);

      return {
        processed: true,
        paymentId: payment.id,
        bookingId: payment.bookingId,
        status: 'FAILED',
        recoveryAttempted: true,
      };

    } catch (error) {
      logger.error('Payment failed handling error:', error);
      throw error;
    }
  }

  /**
   * Handle refund event
   */
  async handleRefund(data) {
    const { id: chargeId, object } = data;
    
    try {
      const payment = await prisma.payment.findFirst({
        where: { stripePaymentId: chargeId },
        include: {
          booking: {
            include: {
              user: true,
            },
          },
        },
      });

      if (!payment) {
        logger.warn(`Payment not found for refund: ${chargeId}`);
        return {
          processed: false,
          reason: 'Payment not found',
        };
      }

      // Update payment status
      await prisma.payment.update({
        where: { id: payment.id },
        data: {
          status: 'REFUNDED',
          refundAmount: object.amount_refunded / 100,
          refundReason: 'Webhook refund',
          updatedAt: new Date(),
        },
      });

      // Update booking
      await prisma.booking.update({
        where: { id: payment.bookingId },
        data: {
          status: 'CANCELLED',
          updatedAt: new Date(),
        },
      });

      return {
        processed: true,
        paymentId: payment.id,
        bookingId: payment.bookingId,
        status: 'REFUNDED',
      };

    } catch (error) {
      logger.error('Refund handling error:', error);
      throw error;
    }
  }

  /**
   * Send confirmation notification
   */
  async sendConfirmation(booking) {
    // Implementation for sending email/SMS notifications
    // This would integrate with your notification service
    logger.info(`Sending confirmation for booking: ${booking.id}`);
  }
}

export const webhookHandler = new WebhookHandler();
export default webhookHandler;