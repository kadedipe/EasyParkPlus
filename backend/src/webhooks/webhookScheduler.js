// parking-management/backend/src/webhooks/webhookScheduler.js
import cron from 'node-cron';
import { logger } from '../utils/logger.js';
import { webhookRetryService } from './webhookRetry.js';

class WebhookScheduler {
  constructor() {
    this.jobs = [];
  }

  /**
   * Start all scheduled jobs
   */
  start() {
    // Retry failed webhooks every 5 minutes
    this.scheduleJob('*/5 * * * *', async () => {
      logger.info('Running scheduled webhook retry...');
      try {
        const result = await webhookRetryService.processFailedWebhooks();
        logger.info('Scheduled retry completed:', result);
      } catch (error) {
        logger.error('Scheduled retry failed:', error);
      }
    });

    // Process webhook batches every minute
    this.scheduleJob('* * * * *', async () => {
      try {
        const result = await webhookRetryService.processBatch(25);
        if (result.processed > 0 || result.failed > 0) {
          logger.info('Batch processing completed:', result);
        }
      } catch (error) {
        logger.error('Batch processing failed:', error);
      }
    });

    // Cleanup old events daily at 2 AM
    this.scheduleJob('0 2 * * *', async () => {
      logger.info('Running webhook cleanup...');
      try {
        const result = await webhookRetryService.cleanupOldEvents(30);
        logger.info('Cleanup completed:', result);
      } catch (error) {
        logger.error('Cleanup failed:', error);
      }
    });

    // Log webhook metrics every hour
    this.scheduleJob('0 * * * *', async () => {
      try {
        const metrics = await webhookRetryService.getRetryMetrics();
        logger.info('Webhook metrics:', metrics);
        
        // Alert if success rate drops below 95%
        if (metrics.successRate < 95) {
          logger.warn(`Webhook success rate is ${metrics.successRate.toFixed(2)}% - below threshold!`);
        }
      } catch (error) {
        logger.error('Failed to get webhook metrics:', error);
      }
    });

    logger.info(`Started ${this.jobs.length} scheduled jobs`);
  }

  /**
   * Schedule a cron job
   */
  scheduleJob(cronExpression, callback) {
    const job = cron.schedule(cronExpression, callback);
    this.jobs.push(job);
    return job;
  }

  /**
   * Stop all scheduled jobs
   */
  stop() {
    this.jobs.forEach(job => job.stop());
    this.jobs = [];
    logger.info('All scheduled jobs stopped');
  }
}

export const webhookScheduler = new WebhookScheduler();

// Start scheduler in production
if (process.env.NODE_ENV === 'production') {
  webhookScheduler.start();
}

export default webhookScheduler;