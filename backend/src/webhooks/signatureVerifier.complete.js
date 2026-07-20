// parking-management/backend/src/webhooks/signatureVerifier.complete.js
import crypto from 'crypto';
import { logger } from '../utils/logger.js';

class CompleteSignatureVerifier {
  constructor() {
    this.providers = {
      stripe: {
        header: 'stripe-signature',
        secret: process.env.STRIPE_WEBHOOK_SECRET,
        algorithm: 'sha256',
        tolerance: 300, // 5 minutes
        version: 'v1',
      },
      paypal: {
        header: 'paypal-auth-algo',
        secret: process.env.PAYPAL_WEBHOOK_SECRET,
        algorithm: 'sha256',
        tolerance: 300,
        version: 'v2',
      },
      github: {
        header: 'x-hub-signature-256',
        secret: process.env.GITHUB_WEBHOOK_SECRET,
        algorithm: 'sha256',
        tolerance: 300,
        version: 'v1',
      },
      slack: {
        header: 'x-slack-signature',
        secret: process.env.SLACK_WEBHOOK_SECRET,
        algorithm: 'sha256',
        tolerance: 300,
        version: 'v0',
      },
    };
    
    this.verificationCache = new Map();
    this.cacheTTL = 60000; // 1 minute
  }

  /**
   * Verify webhook signature with comprehensive validation
   */
  verifySignature(provider, payload, signature, timestamp = null, headers = {}) {
    try {
      const config = this.providers[provider];
      if (!config) {
        throw new Error(`Unknown webhook provider: ${provider}`);
      }

      // Check for replay attacks
      if (this.isReplayAttack(provider, signature, timestamp)) {
        logger.warn(`Replay attack detected for ${provider} webhook`);
        return {
          valid: false,
          error: 'REPLAY_ATTACK_DETECTED',
          message: 'Webhook signature replay detected',
        };
      }

      // Verify based on provider
      let result;
      switch (provider) {
        case 'stripe':
          result = this.verifyStripeSignature(payload, signature, config);
          break;
        case 'paypal':
          result = this.verifyPaypalSignature(payload, signature, headers, config);
          break;
        case 'github':
          result = this.verifyGithubSignature(payload, signature, config);
          break;
        case 'slack':
          result = this.verifySlackSignature(payload, signature, timestamp, config);
          break;
        default:
          result = this.verifyGenericSignature(payload, signature, config);
      }

      // Cache successful verifications
      if (result.valid) {
        this.cacheVerification(provider, signature, result);
      }

      return result;
    } catch (error) {
      logger.error('Signature verification error:', error);
      return {
        valid: false,
        error: 'VERIFICATION_ERROR',
        message: error.message,
      };
    }
  }

  /**
   * Verify Stripe webhook signature
   */
  verifyStripeSignature(payload, signature, config) {
    try {
      // Parse signature header
      const parts = signature.split(',');
      const timestamp = parts.find(p => p.startsWith('t='))?.split('=')[1];
      const signatureHash = parts.find(p => p.startsWith('v1='))?.split('=')[1];

      if (!timestamp || !signatureHash) {
        return {
          valid: false,
          error: 'INVALID_SIGNATURE_FORMAT',
          message: 'Invalid Stripe signature format',
        };
      }

      // Check timestamp tolerance
      const signatureTime = parseInt(timestamp);
      const currentTime = Math.floor(Date.now() / 1000);
      
      if (Math.abs(currentTime - signatureTime) > config.tolerance) {
        return {
          valid: false,
          error: 'TIMESTAMP_OUT_OF_TOLERANCE',
          message: `Timestamp ${signatureTime} is outside tolerance of ${config.tolerance}s`,
          details: { signatureTime, currentTime, tolerance: config.tolerance },
        };
      }

      // Construct signed payload
      const signedPayload = `${timestamp}.${payload}`;
      
      // Calculate expected signature
      const expectedSignature = crypto
        .createHmac(config.algorithm, config.secret)
        .update(signedPayload)
        .digest('hex');

      // Compare signatures
      const isValid = crypto.timingSafeEqual(
        Buffer.from(signatureHash),
        Buffer.from(expectedSignature)
      );

      return {
        valid: isValid,
        provider: 'stripe',
        timestamp: signatureTime,
        algorithm: config.algorithm,
      };
    } catch (error) {
      logger.error('Stripe signature verification error:', error);
      return {
        valid: false,
        error: 'STRIPE_VERIFICATION_ERROR',
        message: error.message,
      };
    }
  }

  /**
   * Verify PayPal webhook signature
   */
  verifyPaypalSignature(payload, signature, headers, config) {
    try {
      // PayPal uses multiple headers
      const authAlgo = headers['paypal-auth-algo'];
      const certUrl = headers['paypal-cert-url'];
      const transmissionId = headers['paypal-transmission-id'];
      const transmissionTime = headers['paypal-transmission-time'];

      if (!authAlgo || !certUrl || !transmissionId || !transmissionTime) {
        return {
          valid: false,
          error: 'MISSING_PAYPAL_HEADERS',
          message: 'Missing required PayPal webhook headers',
        };
      }

      // Build the string to sign
      const signedPayload = [
        transmissionId,
        transmissionTime,
        authAlgo,
        crypto.createHash('sha256').update(payload).digest('hex'),
        certUrl,
      ].join('|');

      const expectedSignature = crypto
        .createHmac(config.algorithm, config.secret)
        .update(signedPayload)
        .digest('hex');

      // Verify signature
      const isValid = crypto.timingSafeEqual(
        Buffer.from(signature),
        Buffer.from(expectedSignature)
      );

      return {
        valid: isValid,
        provider: 'paypal',
        transmissionId,
        transmissionTime,
        algorithm: config.algorithm,
      };
    } catch (error) {
      logger.error('PayPal signature verification error:', error);
      return {
        valid: false,
        error: 'PAYPAL_VERIFICATION_ERROR',
        message: error.message,
      };
    }
  }

  /**
   * Verify GitHub webhook signature
   */
  verifyGithubSignature(payload, signature, config) {
    try {
      // GitHub uses 'sha256=...' format
      const signatureHash = signature.replace('sha256=', '');
      
      const expectedSignature = crypto
        .createHmac(config.algorithm, config.secret)
        .update(payload)
        .digest('hex');

      const isValid = crypto.timingSafeEqual(
        Buffer.from(signatureHash),
        Buffer.from(expectedSignature)
      );

      return {
        valid: isValid,
        provider: 'github',
        algorithm: config.algorithm,
      };
    } catch (error) {
      logger.error('GitHub signature verification error:', error);
      return {
        valid: false,
        error: 'GITHUB_VERIFICATION_ERROR',
        message: error.message,
      };
    }
  }

  /**
   * Verify Slack webhook signature
   */
  verifySlackSignature(payload, signature, timestamp, config) {
    try {
      if (!timestamp) {
        return {
          valid: false,
          error: 'MISSING_TIMESTAMP',
          message: 'Slack webhook requires timestamp',
        };
      }

      // Check timestamp (prevent replay attacks)
      const requestTime = parseInt(timestamp);
      const currentTime = Math.floor(Date.now() / 1000);
      
      if (Math.abs(currentTime - requestTime) > config.tolerance) {
        return {
          valid: false,
          error: 'TIMESTAMP_OUT_OF_TOLERANCE',
          message: `Timestamp ${requestTime} is outside tolerance of ${config.tolerance}s`,
        };
      }

      // Build the string to sign
      const signedPayload = `v0:${timestamp}:${payload}`;
      
      const expectedSignature = crypto
        .createHmac(config.algorithm, config.secret)
        .update(signedPayload)
        .digest('hex');

      const isValid = crypto.timingSafeEqual(
        Buffer.from(signature),
        Buffer.from(`v0=${expectedSignature}`)
      );

      return {
        valid: isValid,
        provider: 'slack',
        timestamp: requestTime,
        algorithm: config.algorithm,
      };
    } catch (error) {
      logger.error('Slack signature verification error:', error);
      return {
        valid: false,
        error: 'SLACK_VERIFICATION_ERROR',
        message: error.message,
      };
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

      const isValid = crypto.timingSafeEqual(
        Buffer.from(signature),
        Buffer.from(expectedSignature)
      );

      return {
        valid: isValid,
        provider: 'generic',
        algorithm: config.algorithm,
      };
    } catch (error) {
      logger.error('Generic signature verification error:', error);
      return {
        valid: false,
        error: 'GENERIC_VERIFICATION_ERROR',
        message: error.message,
      };
    }
  }

  /**
   * Check for replay attacks
   */
  isReplayAttack(provider, signature, timestamp) {
    const cacheKey = `${provider}:${signature}`;
    const cached = this.verificationCache.get(cacheKey);
    
    if (cached) {
      // If we've seen this signature within the tolerance window
      if (Date.now() - cached < this.cacheTTL) {
        return true;
      }
      this.verificationCache.delete(cacheKey);
    }
    
    return false;
  }

  /**
   * Cache successful verification
   */
  cacheVerification(provider, signature, result) {
    const cacheKey = `${provider}:${signature}`;
    this.verificationCache.set(cacheKey, {
      verified: true,
      timestamp: Date.now(),
      result,
    });
    
    // Clean old cache entries periodically
    if (this.verificationCache.size > 1000) {
      this.cleanCache();
    }
  }

  /**
   * Clean verification cache
   */
  cleanCache() {
    const now = Date.now();
    for (const [key, value] of this.verificationCache.entries()) {
      if (now - value.timestamp > this.cacheTTL) {
        this.verificationCache.delete(key);
      }
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
      provider,
    };
  }

  /**
   * Validate webhook headers
   */
  validateWebhookHeaders(headers, provider) {
    const config = this.providers[provider];
    if (!config) {
      return {
        valid: false,
        error: 'UNKNOWN_PROVIDER',
        message: `Unknown webhook provider: ${provider}`,
      };
    }

    const signature = headers[config.header.toLowerCase()];
    if (!signature) {
      return {
        valid: false,
        error: 'MISSING_SIGNATURE',
        message: `Missing signature header: ${config.header}`,
        expected: config.header,
        received: Object.keys(headers),
      };
    }

    return {
      valid: true,
      signature,
      provider,
    };
  }

  /**
   * Get webhook verification middleware
   */
  createVerificationMiddleware(provider) {
    return (req, res, next) => {
      try {
        // Get raw body
        const payload = req.rawBody || JSON.stringify(req.body);
        const headers = req.headers;
        
        // Validate headers
        const headerValidation = this.validateWebhookHeaders(headers, provider);
        if (!headerValidation.valid) {
          logger.error('Webhook header validation failed:', headerValidation);
          return res.status(400).json({
            error: headerValidation.error,
            message: headerValidation.message,
          });
        }

        // Verify signature
        const result = this.verifySignature(
          provider,
          payload,
          headerValidation.signature,
          headers['timestamp'] || headers['x-request-timestamp'],
          headers
        );

        if (!result.valid) {
          logger.error('Webhook signature verification failed:', {
            provider,
            error: result.error,
            message: result.message,
          });
          
          return res.status(401).json({
            error: 'INVALID_SIGNATURE',
            message: 'Webhook signature verification failed',
            details: result.error,
          });
        }

        // Add verification result to request
        req.webhook = {
          provider,
          verified: true,
          timestamp: result.timestamp,
          algorithm: result.algorithm,
        };

        logger.info(`Webhook signature verified: ${provider}`, {
          timestamp: result.timestamp,
          algorithm: result.algorithm,
        });

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

  /**
   * Get verification statistics
   */
  getVerificationStats() {
    return {
      cacheSize: this.verificationCache.size,
      providers: Object.keys(this.providers),
      cacheTTL: this.cacheTTL,
      configuredProviders: Object.keys(this.providers).filter(
        provider => this.providers[provider].secret
      ),
    };
  }
}

export const signatureVerifier = new CompleteSignatureVerifier();
export default signatureVerifier;