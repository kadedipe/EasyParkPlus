// parking-management/backend/src/routes/index.js
import express from 'express';
import {
    adminRateLimiter,
    authRateLimiter,
    bookingRateLimiter,
    paymentRateLimiter,
    registrationRateLimiter,
    resetPasswordRateLimiter,
    searchRateLimiter
} from '../middleware/rateLimit.js';
import adminRoutes from './adminRoutes.js';
import authRoutes from './authRoutes.js';
import bookingRoutes from './bookingRoutes.js';
import parkingRoutes from './parkingRoutes.js';
import paymentRoutes from './paymentRoutes.js';
import userRoutes from './userRoutes.js';

const router = express.Router();

// Apply rate limiting to all routes
router.use('/auth/login', authRateLimiter);
router.use('/auth/register', registrationRateLimiter);
router.use('/auth/forgot-password', resetPasswordRateLimiter);
router.use('/auth/reset-password', resetPasswordRateLimiter);

// API routes with general rate limiting
router.use('/parking', searchRateLimiter);
router.use('/parking/search', searchRateLimiter);

// Booking routes
router.use('/bookings', bookingRateLimiter);

// Payment routes
router.use('/payments', paymentRateLimiter);

// Admin routes
router.use('/admin', adminRateLimiter);

// Mount routes
router.use('/auth', authRoutes);
router.use('/parking', parkingRoutes);
router.use('/bookings', bookingRoutes);
router.use('/payments', paymentRoutes);
router.use('/users', userRoutes);
router.use('/admin', adminRoutes);

export default router;