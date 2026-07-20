// parking-management/backend/src/middleware/rateLimit.js
import rateLimit from 'express-rate-limit';
import RedisStore from 'rate-limit-redis';
import { createClient } from 'redis';
import { logger } from '../utils/logger.js';

// Redis client for distributed rate limiting
const redisClient = createClient({
  url: process.env.REDIS_URL || 'redis://localhost:6379',
  password: process.env.REDIS_PASSWORD,
});

redisClient.on('error', (err) => {
  logger.error('Redis rate limit error:', err);
});

redisClient.connect().catch((err) => {
  logger.error('Redis connection error:', err);
});

// Create Redis store
const store = new RedisStore({
  sendCommand: (...args) => redisClient.sendCommand(args),
  prefix: 'rl:',
});

// Rate limit configurations by endpoint type
export const rateLimitConfigs = {
  // Authentication endpoints - strict limits
  auth: {
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 5, // 5 attempts
    message: {
      error: 'AUTH_RATE_LIMIT_EXCEEDED',
      message: 'Too many authentication attempts. Please try again after 15 minutes.',
    },
    standardHeaders: true,
    legacyHeaders: false,
    skipSuccessfulRequests: true,
  },

  // Registration endpoints - very strict
  registration: {
    windowMs: 60 * 60 * 1000, // 1 hour
    max: 3, // 3 attempts
    message: {
      error: 'REGISTRATION_RATE_LIMIT_EXCEEDED',
      message: 'Too many registration attempts. Please try again after 1 hour.',
    },
    standardHeaders: true,
    legacyHeaders: false,
    skipSuccessfulRequests: true,
  },

  // Password reset endpoints
  resetPassword: {
    windowMs: 60 * 60 * 1000, // 1 hour
    max: 3,
    message: {
      error: 'RESET_PASSWORD_RATE_LIMIT_EXCEEDED',
      message: 'Too many password reset attempts. Please try again after 1 hour.',
    },
    standardHeaders: true,
    legacyHeaders: false,
    skipSuccessfulRequests: true,
  },

  // API endpoints - moderate limits
  api: {
    windowMs: 60 * 1000, // 1 minute
    max: 100, // 100 requests per minute
    message: {
      error: 'API_RATE_LIMIT_EXCEEDED',
      message: 'Too many API requests. Please slow down.',
    },
    standardHeaders: true,
    legacyHeaders: false,
  },

  // Payment endpoints - stricter limits
  payment: {
    windowMs: 60 * 1000, // 1 minute
    max: 10, // 10 payment attempts per minute
    message: {
      error: 'PAYMENT_RATE_LIMIT_EXCEEDED',
      message: 'Too many payment attempts. Please try again later.',
    },
    standardHeaders: true,
    legacyHeaders: false,
  },

  // Booking endpoints - moderate limits
  booking: {
    windowMs: 60 * 1000, // 1 minute
    max: 20, // 20 booking operations per minute
    message: {
      error: 'BOOKING_RATE_LIMIT_EXCEEDED',
      message: 'Too many booking operations. Please slow down.',
    },
    standardHeaders: true,
    legacyHeaders: false,
  },

  // Search endpoints - generous limits
  search: {
    windowMs: 60 * 1000, // 1 minute
    max: 50, // 50 searches per minute
    message: {
      error: 'SEARCH_RATE_LIMIT_EXCEEDED',
      message: 'Too many search requests. Please wait a moment.',
    },
    standardHeaders: true,
    legacyHeaders: false,
  },

  // Admin endpoints - very strict
  admin: {
    windowMs: 60 * 1000, // 1 minute
    max: 30, // 30 admin operations per minute
    message: {
      error: 'ADMIN_RATE_LIMIT_EXCEEDED',
      message: 'Too many admin operations. Please slow down.',
    },
    standardHeaders: true,
    legacyHeaders: false,
  },
};

// Create rate limiters
export const createRateLimiter = (config) => {
  return rateLimit({
    store,
    windowMs: config.windowMs,
    max: config.max,
    message: config.message,
    standardHeaders: config.standardHeaders || true,
    legacyHeaders: config.legacyHeaders || false,
    skipSuccessfulRequests: config.skipSuccessfulRequests || false,
    keyGenerator: (req) => {
      // Use user ID if authenticated, otherwise IP
      return req.user?.id || req.ip;
    },
    skip: (req) => {
      // Skip rate limiting for health checks
      return req.path === '/health';
    },
    handler: (req, res, next, options) => {
      logger.warn('Rate limit exceeded', {
        ip: req.ip,
        path: req.path,
        method: req.method,
        userId: req.user?.id,
      });
      
      res.status(429).json({
        success: false,
        error: options.message.error || 'RATE_LIMIT_EXCEEDED',
        message: options.message.message || 'Too many requests',
        retryAfter: Math.ceil(options.windowMs / 1000),
        timestamp: new Date().toISOString(),
      });
    },
  });
};

// Export individual rate limiters
export const authRateLimiter = createRateLimiter(rateLimitConfigs.auth);
export const registrationRateLimiter = createRateLimiter(rateLimitConfigs.registration);
export const resetPasswordRateLimiter = createRateLimiter(rateLimitConfigs.resetPassword);
export const apiRateLimiter = createRateLimiter(rateLimitConfigs.api);
export const paymentRateLimiter = createRateLimiter(rateLimitConfigs.payment);
export const bookingRateLimiter = createRateLimiter(rateLimitConfigs.booking);
export const searchRateLimiter = createRateLimiter(rateLimitConfigs.search);
export const adminRateLimiter = createRateLimiter(rateLimitConfigs.admin);

// Dynamic rate limiter for custom limits
export const dynamicRateLimiter = (windowMs, max, message) => {
  return createRateLimiter({
    windowMs,
    max,
    message: {
      error: 'CUSTOM_RATE_LIMIT_EXCEEDED',
      message: message || 'Too many requests',
    },
  });
};

// Rate limit middleware with skip logic
export const rateLimitMiddleware = (config) => {
  const limiter = createRateLimiter(config);
  
  return async (req, res, next) => {
    // Check if user is whitelisted
    if (req.user?.role === 'SUPER_ADMIN' || req.user?.role === 'ADMIN') {
      return next();
    }
    
    // Apply rate limit
    return limiter(req, res, next);
  };
};

// Get rate limit status for client
export const getRateLimitStatus = async (identifier) => {
  try {
    const keys = await redisClient.keys(`rl:${identifier}*`);
    const status = {};
    
    for (const key of keys) {
      const count = await redisClient.get(key);
      const ttl = await redisClient.ttl(key);
      const parts = key.split(':');
      const type = parts[parts.length - 1];
      
      status[type] = {
        count: parseInt(count) || 0,
        remaining: Math.max(0, 100 - (parseInt(count) || 0)),
        resetIn: ttl > 0 ? ttl : 0,
      };
    }
    
    return status;
  } catch (error) {
    logger.error('Error getting rate limit status:', error);
    return null;
  }
};

export default {
  authRateLimiter,
  registrationRateLimiter,
  resetPasswordRateLimiter,
  apiRateLimiter,
  paymentRateLimiter,
  bookingRateLimiter,
  searchRateLimiter,
  adminRateLimiter,
  dynamicRateLimiter,
  rateLimitMiddleware,
  getRateLimitStatus,
  rateLimitConfigs,
};