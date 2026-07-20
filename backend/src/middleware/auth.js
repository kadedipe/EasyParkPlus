// parking-management/backend/src/middleware/auth.js
import { PrismaClient } from '@prisma/client';
import jwt from 'jsonwebtoken';
import { logger } from '../utils/logger.js';

const prisma = new PrismaClient();

/**
 * Verify JWT token
 */
export const authenticate = async (req, res, next) => {
  try {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({
        error: 'UNAUTHORIZED',
        message: 'Authentication required',
      });
    }

    const token = authHeader.split(' ')[1];

    // Verify token
    const decoded = jwt.verify(token, process.env.JWT_SECRET);

    // Get user
    const user = await prisma.user.findUnique({
      where: { id: decoded.userId },
      select: {
        id: true,
        email: true,
        firstName: true,
        lastName: true,
        role: true,
        isEmailVerified: true,
      },
    });

    if (!user) {
      return res.status(401).json({
        error: 'UNAUTHORIZED',
        message: 'User not found',
      });
    }

    // Attach user to request
    req.user = user;
    next();
  } catch (error) {
    if (error.name === 'JsonWebTokenError') {
      return res.status(401).json({
        error: 'INVALID_TOKEN',
        message: 'Invalid token',
      });
    }

    if (error.name === 'TokenExpiredError') {
      return res.status(401).json({
        error: 'TOKEN_EXPIRED',
        message: 'Token expired',
      });
    }

    logger.error('Authentication error:', error);
    next(error);
  }
};

/**
 * Authorize user by role
 */
export const authorize = (...roles) => {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({
        error: 'UNAUTHORIZED',
        message: 'Authentication required',
      });
    }

    if (!roles.includes(req.user.role)) {
      return res.status(403).json({
        error: 'FORBIDDEN',
        message: 'You do not have permission to perform this action',
      });
    }

    next();
  };
};

/**
 * Check if user owns the resource
 */
export const checkOwnership = (model, idField = 'id') => {
  return async (req, res, next) => {
    try {
      const resourceId = req.params[idField] || req.body[idField];
      
      if (!resourceId) {
        return res.status(400).json({
          error: 'MISSING_ID',
          message: 'Resource ID is required',
        });
      }

      const resource = await prisma[model].findUnique({
        where: { id: resourceId },
      });

      if (!resource) {
        return res.status(404).json({
          error: 'NOT_FOUND',
          message: 'Resource not found',
        });
      }

      // Check if user owns the resource
      if (resource.userId !== req.user.id) {
        return res.status(403).json({
          error: 'FORBIDDEN',
          message: 'You do not have permission to access this resource',
        });
      }

      req.resource = resource;
      next();
    } catch (error) {
      logger.error('Ownership check error:', error);
      next(error);
    }
  };
};

/**
 * Rate limiting middleware
 */
export const rateLimit = {
  // Rate limit configuration
  login: {
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 5, // 5 attempts per window
  },
  register: {
    windowMs: 60 * 60 * 1000, // 1 hour
    max: 3, // 3 attempts per hour
  },
  forgotPassword: {
    windowMs: 60 * 60 * 1000, // 1 hour
    max: 3, // 3 attempts per hour
  },
};

export default {
  authenticate,
  authorize,
  checkOwnership,
  rateLimit,
};