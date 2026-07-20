// parking-management/backend/src/webhooks/signatureVerifier.js
import crypto from 'crypto';
import { logger } from '../utils/logger.js';

class SignatureVerifier {
  constructor() {
    this.providers = {
      stripe: {
        header: 'stripe-signature',
        secret: process.env.STRIPE_WEBHOOK_SECRET,
        algorithm: 'sha256',
        tolerance: 300, // 5 minutes tolerance
      },
      paypal: {
        header: 'paypal-auth-algo',
        secret: process.env.PAYPAL_WEBHOOK_SECRET,
        algorithm: 'sha256',
        tolerance: 300,
      },
    };
  }

  /**
   * Verify webhook signature based on provider
   */
  verifySignature(provider, payload, signature, timestamp = null) {
    const config = this.providers[provider];
    
    if (!config) {
      throw new Error(`Unknown webhook provider: ${provider}`);
    }

    switch (provider) {
      case 'stripe':
        return this.verifyStripeSignature(payload, signature, config);
      case 'paypal':
        return this.verifyPaypalSignature(payload, signature, timestamp, config);
      default:
        return this.verifyGenericSignature(payload, signature, config);
    }
  }

  /**
   * Verify Stripe webhook signature
   */
  verifyStripeSignature(payload, signature, config) {
    try {
      // Parse signature header
      const signatureParts = signature.split(',');
      const timestamp = signatureParts.find(p => p.startsWith('t='))?.split('=')[1];
      const signatureHash = signatureParts.find(p => p.startsWith('v1='))?.split('=')[1];

      if (!timestamp || !signatureHash) {
        logger.error('Invalid Stripe signature format');
        return false;
      }

      // Check timestamp tolerance
      const signatureTime = parseInt(timestamp);
      const currentTime = Math.floor(Date.now() / 1000);
      
      if (Math.abs(currentTime - signatureTime) > config.tolerance) {
        logger.warn('Stripe webhook timestamp outside tolerance', {
          signatureTime,
          currentTime,
          tolerance: config.tolerance,
        });
        return false;
      }

      // Construct signed payload
      const signedPayload = `${timestamp}.${payload}`;
      
      // Calculate expected signature
      const expectedSignature = crypto
        .createHmac(config.algorithm, config.secret)
        .update(signedPayload)
        .digest('hex');

      // Compare signatures (constant time comparison)
      return crypto.timingSafeEqual(
        Buffer.from(signatureHash),
        Buffer.from(expectedSignature)
      );

    } catch (error) {
      logger.error('Stripe signature verification error:', error);
      return false;
    }
  }

  /**
   * Verify PayPal webhook signature
   */
  verifyPaypalSignature(payload, signature, timestamp, config) {
    try {
      // PayPal uses a different format
      const signedPayload = `${timestamp}.${payload}`;
      
      const expectedSignature = crypto
        .createHmac(config.algorithm, config.secret)
        .update(signedPayload)
        .digest('hex');

      return crypto.timingSafeEqual(
        Buffer.from(signature),
        Buffer.from(expectedSignature)
      );

    } catch (error) {
      logger.error('PayPal signature verification error:', error);
      return false;
    }
  }

  /**
   * Generic signature verification
   */
  verifyGenericSignature(payload, signature, config) {
    try {
      const expectedSignature = crypto
        .createHmac(config.algorithm, config.secret)
        .update(payload)
        .digest('hex');

      return crypto.timingSafeEqual(
        Buffer.from(signature),
        Buffer.from(expectedSignature)
      );

    } catch (error) {
      logger.error('Generic signature verification error:', error);
      return false;
    }
  }

  /**
   * Generate signature for outgoing webhooks
   */
  generateSignature(payload, provider = 'stripe') {
    const config = this.providers[provider];
    
    if (!config) {
      throw new Error(`Unknown webhook provider: ${provider}`);
    }

    const timestamp = Math.floor(Date.now() / 1000);
    const signedPayload = `${timestamp}.${payload}`;
    
    const signature = crypto
      .createHmac(config.algorithm, config.secret)
      .update(signedPayload)
      .digest('hex');

    return {
      signature: `t=${timestamp},v1=${signature}`,
      timestamp,
    };
  }

  /**
   * Validate webhook headers
   */
  validateHeaders(headers, provider) {
    const config = this.providers[provider];
    
    if (!config) {
      throw new Error(`Unknown webhook provider: ${provider}`);
    }

    const signatureHeader = headers[config.header];
    
    if (!signatureHeader) {
      logger.error(`Missing signature header: ${config.header}`);
      return false;
    }

    return true;
  }

  /**
   * Get webhook verification middleware
   */
  createVerificationMiddleware(provider) {
    return (req, res, next) => {
      try {
        // Get raw body
        const payload = req.rawBody || JSON.stringify(req.body);
        const signature = req.headers[this.providers[provider].header];
        
        if (!signature) {
          logger.error('Missing webhook signature');
          return res.status(401).json({
            error: 'MISSING_SIGNATURE',
            message: 'Webhook signature is required',
          });
        }

        // Verify signature
        const isValid = this.verifySignature(
          provider,
          payload,
          signature
        );

        if (!isValid) {
          logger.error('Invalid webhook signature');
          return res.status(401).json({
            error: 'INVALID_SIGNATURE',
            message: 'Webhook signature verification failed',
          });
        }

        // Log successful verification
        logger.info(`Webhook signature verified: ${provider}`);

        next();
      } catch (error) {
        logger.error('Webhook verification middleware error:', error);
        return res.status(500).json({
          error: 'VERIFICATION_ERROR',
          message: 'Webhook verification failed',
        });
      }
    };
  }
}

export const signatureVerifier = new SignatureVerifier();
export default signatureVerifier;