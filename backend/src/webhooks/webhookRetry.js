// parking-management/backend/src/webhooks/webhookRetry.js
import { WebhookEventModel } from '../models/WebhookEvent.js';
import { logger } from '../utils/logger.js';
import { webhookQueueService } from './webhookQueue.js';

export class WebhookRetryService {
  constructor() {
    this.maxRetries = 5;
    this.retryDelays = [60, 120, 300, 600, 1800]; // seconds
    this.batchSize = 50;
    this.isProcessing = false;
  }

  /**
   * Process failed webhooks with retry logic
   */
  async processFailedWebhooks() {
    if (this.isProcessing) {
      logger.info('Webhook retry already in progress');
      return;
    }

    this.isProcessing = true;
    logger.info('Starting webhook retry process...');

    try {
      // Get failed webhooks ready for retry
      const failedWebhooks = await WebhookEventModel.getPendingEvents(this.batchSize);
      
      if (failedWebhooks.length === 0) {
        logger.info('No failed webhooks to retry');
        this.isProcessing = false;
        return;
      }

      logger.info(`Found ${failedWebhooks.length} webhooks to retry`);

      let successCount = 0;
      let failureCount = 0;
      let exhaustedCount = 0;

      for (const webhook of failedWebhooks) {
        try {
          // Check if max retries exceeded
          if (webhook.retryCount >= this.maxRetries) {
            await WebhookEventModel.updateStatus(
              webhook.id,
              'FAILED',
              'Max retry attempts exceeded'
            );
            exhaustedCount++;
            continue;
          }

          // Add back to queue with delay
          const delay = this.retryDelays[webhook.retryCount] || this.retryDelays[this.retryDelays.length - 1];
          const nextRetryAt = new Date(Date.now() + delay * 1000);

          await WebhookEventModel.markForRetry(webhook.id, nextRetryAt);

          // Add to queue
          await webhookQueueService.addWebhook({
            eventId: webhook.eventId,
            eventType: webhook.eventType,
            payload: webhook.payload,
            source: webhook.source,
            delay,
          });

          successCount++;
          logger.info(`Webhook ${webhook.id} scheduled for retry in ${delay}s (attempt ${webhook.retryCount + 1}/${this.maxRetries})`);

        } catch (error) {
          logger.error(`Failed to process webhook ${webhook.id}:`, error);
          failureCount++;
          
          // Update failure status
          await WebhookEventModel.updateStatus(
            webhook.id,
            'FAILED',
            error.message
          );
        }
      }

      logger.info(`Webhook retry completed: ${successCount} success, ${failureCount} failed, ${exhaustedCount} exhausted`);

      return {
        success: successCount,
        failed: failureCount,
        exhausted: exhaustedCount,
        total: failedWebhooks.length,
      };

    } catch (error) {
      logger.error('Webhook retry service error:', error);
      throw error;
    } finally {
      this.isProcessing = false;
    }
  }

  /**
   * Schedule webhook retry with exponential backoff
   */
  async scheduleRetry(webhookId, error = null) {
    try {
      const webhook = await WebhookEventModel.findById(webhookId);
      
      if (!webhook) {
        logger.error(`Webhook ${webhookId} not found`);
        return;
      }

      const retryCount = webhook.retryCount + 1;

      if (retryCount > this.maxRetries) {
        await WebhookEventModel.updateStatus(
          webhookId,
          'FAILED',
          error?.message || 'Max retry attempts exceeded'
        );
        logger.error(`Webhook ${webhookId} failed after ${this.maxRetries} attempts`);
        return;
      }

      const delay = this.calculateBackoff(retryCount);
      const nextRetryAt = new Date(Date.now() + delay * 1000);

      await WebhookEventModel.markForRetry(webhookId, nextRetryAt);

      // Add to queue with delay
      await webhookQueueService.addWebhook({
        eventId: webhook.eventId,
        eventType: webhook.eventType,
        payload: webhook.payload,
        source: webhook.source,
        delay,
      });

      logger.info(`Webhook ${webhookId} scheduled for retry in ${delay}s (attempt ${retryCount}/${this.maxRetries})`);

    } catch (error) {
      logger.error(`Failed to schedule retry for webhook ${webhookId}:`, error);
    }
  }

  /**
   * Calculate backoff delay with jitter
   */
  calculateBackoff(attempt) {
    const baseDelay = this.retryDelays[attempt - 1] || this.retryDelays[this.retryDelays.length - 1];
    
    // Add jitter to prevent thundering herd
    const jitter = Math.random() * 0.3 + 0.85; // 85-115% of base delay
    return Math.floor(baseDelay * jitter);
  }

  /**
   * Process webhooks in batch
   */
  async processBatch(batchSize = 50) {
    try {
      const webhooks = await WebhookEventModel.getPendingEvents(batchSize);
      
      if (webhooks.length === 0) {
        return { processed: 0 };
      }

      logger.info(`Processing ${webhooks.length} webhooks in batch`);

      let processed = 0;
      let failed = 0;

      for (const webhook of webhooks) {
        try {
          await WebhookEventModel.updateStatus(webhook.id, 'PROCESSING');
          
          // Process webhook logic
          await this.processWebhook(webhook);
          
          await WebhookEventModel.updateStatus(webhook.id, 'COMPLETED');
          processed++;
        } catch (error) {
          logger.error(`Batch processing failed for webhook ${webhook.id}:`, error);
          failed++;
          
          // Schedule retry
          await this.scheduleRetry(webhook.id, error);
        }
      }

      return {
        processed,
        failed,
        total: webhooks.length,
      };

    } catch (error) {
      logger.error('Batch processing error:', error);
      throw error;
    }
  }

  /**
   * Process individual webhook
   */
  async processWebhook(webhook) {
    // Implement webhook processing logic here
    // This would call the appropriate handler based on event type
    const { webhookHandler } = await import('./webhookHandler.js');
    
    return webhookHandler.handleWebhook({
      eventId: webhook.eventId,
      eventType: webhook.eventType,
      payload: webhook.payload,
      source: webhook.source,
    });
  }

  /**
   * Get webhook processing statistics
   */
  async getWebhookStats() {
    try {
      const stats = await WebhookEventModel.getStats();
      
      // Get queue stats
      const queueStats = await webhookQueueService.getQueueStats();
      
      // Get retry stats
      const retryStats = await WebhookEventModel.getRetryStats();
      
      return {
        ...stats,
        queue: queueStats,
        retry: retryStats,
      };
    } catch (error) {
      logger.error('Failed to get webhook stats:', error);
      throw error;
    }
  }

  /**
   * Cleanup old webhook events
   */
  async cleanupOldEvents(days = 30) {
    try {
      const cutoff = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
      
      // Get old completed events
      const oldEvents = await WebhookEventModel.findMany({
        where: {
          status: 'COMPLETED',
          createdAt: { lt: cutoff },
        },
        take: 1000,
      });

      let deleted = 0;
      for (const event of oldEvents) {
        await WebhookEventModel.delete(event.id);
        deleted++;
        
        if (deleted % 100 === 0) {
          logger.info(`Cleaned up ${deleted} webhook events`);
        }
      }
      
      logger.info(`Cleanup completed: ${deleted} events removed`);
      return { deleted };
    } catch (error) {
      logger.error('Cleanup error:', error);
      throw error;
    }
  }

  /**
   * Get retry metrics
   */
  async getRetryMetrics() {
    try {
      const [total, succeeded, failed, pending] = await Promise.all([
        WebhookEventModel.count(),
        WebhookEventModel.count({ where: { status: 'COMPLETED' } }),
        WebhookEventModel.count({ where: { status: 'FAILED' } }),
        WebhookEventModel.count({ 
          where: { 
            status: { in: ['PENDING', 'RETRYING', 'PROCESSING'] } 
          } 
        }),
      ]);

      const retryDistribution = await WebhookEventModel.groupBy('retryCount');

      return {
        total,
        succeeded,
        failed,
        pending,
        successRate: total > 0 ? (succeeded / total) * 100 : 0,
        retryDistribution: retryDistribution.map(item => ({
          attempts: item.retryCount,
          count: item._count,
        })),
        averageRetries: await WebhookEventModel.avg('retryCount'),
      };
    } catch (error) {
      logger.error('Failed to get retry metrics:', error);
      throw error;
    }
  }
}

export const webhookRetryService = new WebhookRetryService();
export default webhookRetryService;