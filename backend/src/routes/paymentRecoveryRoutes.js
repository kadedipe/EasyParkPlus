// parking-management/backend/src/routes/paymentRecoveryRoutes.js
import express from 'express';
import { authenticate, authorize } from '../middleware/auth.js';
import { logger } from '../utils/logger.js';
import { paymentRecoveryService } from '../webhooks/paymentRecoveryService.js';

const router = express.Router();

// Trigger manual recovery for a payment
router.post('/recover/:paymentId', authenticate, async (req, res) => {
  try {
    const { paymentId } = req.params;
    
    const payment = await prisma.payment.findUnique({
      where: { id: paymentId },
      include: {
        booking: {
          include: {
            user: true,
          },
        },
      },
    });

    if (!payment) {
      return res.status(404).json({
        error: 'PAYMENT_NOT_FOUND',
        message: 'Payment not found',
      });
    }

    // Check if user owns this payment
    if (payment.booking.userId !== req.user.id && req.user.role !== 'ADMIN') {
      return res.status(403).json({
        error: 'FORBIDDEN',
        message: 'You do not have permission to recover this payment',
      });
    }

    const result = await paymentRecoveryService.recoverFailedPayment(payment);
    
    res.json({
      success: true,
      data: result,
    });
  } catch (error) {
    logger.error('Payment recovery error:', error);
    res.status(500).json({
      error: 'RECOVERY_ERROR',
      message: 'Failed to recover payment',
    });
  }
});

// Process all failed payments (admin only)
router.post('/process-all', authenticate, authorize('ADMIN'), async (req, res) => {
  try {
    const result = await paymentRecoveryService.processFailedPayments();
    
    res.json({
      success: true,
      data: result,
    });
  } catch (error) {
    logger.error('Batch recovery error:', error);
    res.status(500).json({
      error: 'BATCH_RECOVERY_ERROR',
      message: 'Failed to process batch recovery',
    });
  }
});

// Get payment recovery status
router.get('/status/:paymentId', authenticate, async (req, res) => {
  try {
    const { paymentId } = req.params;
    
    const payment = await prisma.payment.findUnique({
      where: { id: paymentId },
      select: {
        id: true,
        status: true,
        failureReason: true,
        recoveryAttempts: true,
        createdAt: true,
        updatedAt: true,
      },
    });

    if (!payment) {
      return res.status(404).json({
        error: 'PAYMENT_NOT_FOUND',
        message: 'Payment not found',
      });
    }

    res.json({
      success: true,
      data: payment,
    });
  } catch (error) {
    logger.error('Payment status error:', error);
    res.status(500).json({
      error: 'STATUS_ERROR',
      message: 'Failed to get payment status',
    });
  }
});

// Get recovery statistics (admin only)
router.get('/stats', authenticate, authorize('ADMIN'), async (req, res) => {
  try {
    const stats = await prisma.$queryRaw`
      SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as recovered,
        SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
        AVG(recovery_attempts) as avg_attempts
      FROM payments
      WHERE recovery_attempts > 0
        AND created_at > NOW() - INTERVAL '7 days'
    `;

    res.json({
      success: true,
      data: stats[0],
    });
  } catch (error) {
    logger.error('Recovery stats error:', error);
    res.status(500).json({
      error: 'STATS_ERROR',
      message: 'Failed to get recovery statistics',
    });
  }
});

export default router;