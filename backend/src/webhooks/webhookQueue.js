// parking-management/backend/src/webhooks/webhookQueue.js
import { Queue, Worker } from 'bullmq';
import Redis from 'ioredis';
import { logger } from '../utils/logger.js';
import { webhookHandler } from './webhookHandler.js';

const redisConnection = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: process.env.REDIS_PORT || 6379,
  password: process.env.REDIS_PASSWORD,
});

// Webhook queue
export const webhookQueue = new Queue('webhook-queue', {
  connection: redisConnection,
  defaultJobOptions: {
    attempts: 3,
    backoff: {
      type: 'exponential',
      delay: 1000,
    },
    removeOnComplete: true,
    removeOnFail: false,
  },
});

// Webhook worker
export const webhookWorker = new Worker(
  'webhook-queue',
  async (job) => {
    const { eventId, eventType, payload, source } = job.data;
    
    logger.info(`Processing webhook job: ${eventId}`, { eventType, source });
    
    try {
      await webhookHandler.handleWebhook({
        eventId,
        eventType,
        payload,
        source,
      });
      
      logger.info(`Webhook processed successfully: ${eventId}`);
      return { success: true };
    } catch (error) {
      logger.error(`Webhook processing failed: ${eventId}`, error);
      throw error;
    }
  },
  {
    connection: redisConnection,
    concurrency: 5,
    limiter: {
      max: 100,
      duration: 1000,
    },
  }
);

// Handle worker errors
webhookWorker.on('failed', (job, error) => {
  logger.error(`Webhook job failed: ${job.id}`, error);
});

webhookWorker.on('completed', (job) => {
  logger.info(`Webhook job completed: ${job.id}`);
});

webhookWorker.on('error', (error) => {
  logger.error('Webhook worker error:', error);
});

export const webhookQueueService = {
  /**
   * Add webhook to queue
   */
  async addWebhook(eventData) {
    try {
      const job = await webhookQueue.add(
        `webhook-${eventData.eventId}`,
        eventData,
        {
          jobId: eventData.eventId,
          removeOnComplete: true,
          removeOnFail: false,
        }
      );
      
      logger.info(`Webhook added to queue: ${eventData.eventId}`);
      return job;
    } catch (error) {
      logger.error('Failed to add webhook to queue:', error);
      throw error;
    }
  },

  /**
   * Get queue stats
   */
  async getQueueStats() {
    const [waiting, active, completed, failed, delayed] = await Promise.all([
      webhookQueue.getWaitingCount(),
      webhookQueue.getActiveCount(),
      webhookQueue.getCompletedCount(),
      webhookQueue.getFailedCount(),
      webhookQueue.getDelayedCount(),
    ]);

    return {
      waiting,
      active,
      completed,
      failed,
      delayed,
      total: waiting + active + completed + failed + delayed,
    };
  },

  /**
   * Retry failed webhooks
   */
  async retryFailedWebhooks() {
    const failedJobs = await webhookQueue.getFailed();
    
    for (const job of failedJobs) {
      try {
        await job.retry();
        logger.info(`Retrying failed webhook: ${job.id}`);
      } catch (error) {
        logger.error(`Failed to retry webhook ${job.id}:`, error);
      }
    }
    
    return failedJobs.length;
  },

  /**
   * Cleanup old jobs
   */
  async cleanup(olderThan = 7) {
    const days = olderThan * 24 * 60 * 60 * 1000;
    const cutoff = new Date(Date.now() - days);
    
    // Clean completed and failed jobs
    await webhookQueue.clean(0, 100, 'completed');
    await webhookQueue.clean(0, 100, 'failed');
    
    logger.info(`Cleaned up webhook jobs older than ${olderThan} days`);
  },
};

export default webhookQueueService;