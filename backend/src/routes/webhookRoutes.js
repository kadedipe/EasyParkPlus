// parking-management/backend/src/routes/webhookRoutes.js
import express from 'express';
import { authenticate, authorize } from '../middleware/auth.js';
import { logger } from '../utils/logger.js';
import stripeWebhook from '../webhooks/stripeWebhook.js';
import { webhookRetryService } from '../webhooks/webhookRetry.js';

const router = express.Router();

// Stripe webhook endpoint (no auth, uses signature verification)
router.use('/stripe', stripeWebhook);

// Webhook management endpoints (require admin auth)
router.get('/stats', authenticate, authorize('ADMIN', 'SUPER_ADMIN'), async (req, res) => {
  try {
    const stats = await webhookRetryService.getWebhookStats();
    res.json({
      success: true,
      data: stats,
    });
  } catch (error) {
    logger.error('Failed to get webhook stats:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get webhook stats',
    });
  }
});

router.post('/retry', authenticate, authorize('ADMIN', 'SUPER_ADMIN'), async (req, res) => {
  try {
    const result = await webhookRetryService.retryFailedWebhooks();
    res.json({
      success: true,
      data: result,
    });
  } catch (error) {
    logger.error('Failed to retry webhooks:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to retry webhooks',
    });
  }
});

router.delete('/cleanup', authenticate, authorize('ADMIN', 'SUPER_ADMIN'), async (req, res) => {
  try {
    const { days = 30 } = req.query;
    const result = await webhookRetryService.cleanupOldEvents(parseInt(days));
    res.json({
      success: true,
      data: result,
    });
  } catch (error) {
    logger.error('Failed to cleanup webhooks:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to cleanup webhooks',
    });
  }
});

export default router;