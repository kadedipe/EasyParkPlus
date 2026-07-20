// parking-management/backend/src/middleware/idempotency.js
import { logger } from '../utils/logger.js';
import { idempotencyService } from '../webhooks/idempotencyService.js';

/**
 * Idempotency middleware for API endpoints
 */
export const idempotencyMiddleware = (options = {}) => {
  const {
    header = 'Idempotency-Key',
    ttl = 86400, // 24 hours
    requireKey = false,
  } = options;

  return async (req, res, next) => {
    try {
      // Get idempotency key from header
      const idempotentKey = req.headers[header.toLowerCase()];

      // If key is required and missing, reject
      if (requireKey && !idempotentKey) {
        return res.status(400).json({
          error: 'MISSING_IDEMPOTENCY_KEY',
          message: 'Idempotency-Key header is required',
        });
      }

      // If no key provided, skip idempotency
      if (!idempotentKey) {
        return next();
      }

      // Check if request already exists
      const existing = await idempotencyService.checkIdempotency(
        idempotentKey,
        'api'
      );

      if (existing) {
        // Return cached response
        logger.info(`Idempotent request: ${idempotentKey}`);
        
        return res.status(existing.data?.status || 200).json({
          idempotent: true,
          data: existing.data?.response,
          message: 'Request already processed',
        });
      }

      // Store original response methods
      const originalSend = res.send;
      const originalJson = res.json;
      const originalStatus = res.status;

      // Track response
      let responseData = null;
      let responseStatus = 200;

      // Override status method
      res.status = function(statusCode) {
        responseStatus = statusCode;
        return originalStatus.call(this, statusCode);
      };

      // Override send method
      res.send = function(data) {
        responseData = data;
        return originalSend.call(this, data);
      };

      // Override json method
      res.json = function(data) {
        responseData = data;
        return originalJson.call(this, data);
      };

      // Continue processing
      await next();

      // Store response for future idempotent requests
      if (responseStatus < 500) {
        await idempotencyService.markIdempotent(
          idempotentKey,
          'api',
          {
            status: responseStatus,
            response: responseData,
            timestamp: new Date().toISOString(),
          }
        );
      }

    } catch (error) {
      logger.error('Idempotency middleware error:', error);
      next(error);
    }
  };
};

/**
 * Idempotency cleanup cron job
 */
export const cleanupIdempotency = async () => {
  try {
    const result = await idempotencyService.cleanupExpired();
    logger.info(`Idempotency cleanup completed: ${result.count} records deleted`);
  } catch (error) {
    logger.error('Idempotency cleanup failed:', error);
  }
};

export default idempotencyMiddleware;