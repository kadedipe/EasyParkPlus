// parking-management/backend/src/scripts/testWebhook.js
import { logger } from '../utils/logger.js';
import { webhookHandler } from '../webhooks/webhookHandler.js';
import { webhookQueueService } from '../webhooks/webhookQueue.js';

// Test data
const testWebhookData = {
  eventId: 'test-ev-123456',
  eventType: 'payment_intent.succeeded',
  source: 'stripe',
  payload: {
    id: 'evt_test_123456',
    type: 'payment_intent.succeeded',
    data: {
      object: {
        id: 'pi_test_123456',
        object: 'payment_intent',
        amount: 2000,
        currency: 'usd',
        status: 'succeeded',
        charges: {
          data: [
            {
              id: 'ch_test_123456',
              amount: 2000,
              status: 'succeeded',
            },
          ],
        },
      },
    },
  },
};

async function testWebhook() {
  logger.info('Testing webhook handling...');
  
  try {
    // 1. Test webhook handler
    const result = await webhookHandler.handleWebhook(testWebhookData);
    logger.info('Webhook handler result:', result);
    
    // 2. Test queue
    const job = await webhookQueueService.addWebhook(testWebhookData);
    logger.info('Webhook queued:', job.id);
    
    // 3. Test queue stats
    const stats = await webhookQueueService.getQueueStats();
    logger.info('Queue stats:', stats);
    
    logger.info('Webhook tests completed successfully');
  } catch (error) {
    logger.error('Webhook test failed:', error);
  }
}

// Run test
testWebhook();