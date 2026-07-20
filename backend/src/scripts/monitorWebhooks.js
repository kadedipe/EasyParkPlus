// parking-management/backend/src/scripts/monitorWebhooks.js
import { logger } from '../utils/logger.js';
import { webhookRetryService } from '../webhooks/webhookRetry.js';

async function monitorWebhooks() {
  try {
    logger.info('📊 Webhook Monitoring Report');
    logger.info('=' .repeat(50));
    
    const stats = await webhookRetryService.getWebhookStats();
    
    logger.info(`Total Webhooks: ${stats.total}`);
    logger.info(`✅ Completed: ${stats.completed}`);
    logger.info(`❌ Failed: ${stats.failed}`);
    logger.info(`⏳ Pending: ${stats.pending}`);
    logger.info(`📈 Success Rate: ${stats.successRate.toFixed(2)}%`);
    
    logger.info('\n📋 Queue Status:');
    logger.info(`⏳ Waiting: ${stats.queue.waiting}`);
    logger.info(`🔄 Processing: ${stats.queue.active}`);
    logger.info(`✅ Completed: ${stats.queue.completed}`);
    logger.info(`❌ Failed: ${stats.queue.failed}`);
    logger.info(`⏰ Delayed: ${stats.queue.delayed}`);
    
    logger.info('\n' + '=' .repeat(50));
    
    // Alert if success rate is low
    if (stats.successRate < 95) {
      logger.warn('⚠️ Webhook success rate is below 95%!');
    }
    
    // Alert if there are pending webhooks
    if (stats.pending > 10) {
      logger.warn(`⚠️ ${stats.pending} webhooks are pending!`);
    }
    
  } catch (error) {
    logger.error('Monitoring failed:', error);
  }
}

monitorWebhooks();