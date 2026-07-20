// parking-management/backend/tests/unit/test_api/webhooks/webhooks.test.js
const APIClient = require('../helpers/api-client');
const TestDataGenerator = require('../helpers/test-data');
const crypto = require('crypto');

describe('Webhook API', () => {
  let apiClient;
  let webhookSecret;
  let testReservation;
  let testPayment;
  
  beforeEach(async () => {
    apiClient = new APIClient();
    
    // Generate webhook secret
    webhookSecret = crypto.randomBytes(32).toString('hex');
    process.env.WEBHOOK_SECRET = webhookSecret;
    
    // Create test data
    const userData = TestDataGenerator.generateUser();
    const userResponse = await apiClient.register(userData);
    
    const spotData = TestDataGenerator.generateParkingSpot();
    apiClient.setAdminToken((await apiClient.register(TestDataGenerator.generateAdmin())).body.data.token);
    const spotResponse = await apiClient.createParkingSpot(spotData);
    
    apiClient.setAuthToken(userResponse.body.data.token);
    
    const startTime = new Date(Date.now() + 3600000);
    const endTime = new Date(Date.now() + 7200000);
    
    const reservationResponse = await apiClient.createReservation({
      spotId: spotResponse.body.data._id,
      startTime: startTime.toISOString(),
      endTime: endTime.toISOString(),
      vehicleNumber: 'ABC123'
    });
    
    testReservation = reservationResponse.body.data;
    
    const paymentResponse = await apiClient.processPayment({
      reservationId: testReservation._id,
      amount: testReservation.totalAmount,
      method: 'credit_card',
      cardDetails: {
        number: '4111111111111111',
        expiry: '12/25',
        cvv: '123'
      }
    });
    
    testPayment = paymentResponse.body.data;
  });
  
  describe('POST /webhooks/payment', () => {
    it('should handle payment success webhook', async () => {
      const payload = {
        event: 'payment.success',
        data: {
          transactionId: testPayment.transactionId,
          status: 'completed',
          amount: testPayment.amount,
          timestamp: new Date().toISOString()
        }
      };
      
      const signature = generateWebhookSignature(payload, webhookSecret);
      
      const response = await apiClient.post('/webhooks/payment', payload, {
        headers: {
          'X-Webhook-Signature': signature
        }
      });
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('received', true);
    });
    
    it('should handle payment failure webhook', async () => {
      const payload = {
        event: 'payment.failed',
        data: {
          transactionId: testPayment.transactionId,
          error: 'Insufficient funds',
          timestamp: new Date().toISOString()
        }
      };
      
      const signature = generateWebhookSignature(payload, webhookSecret);
      
      const response = await apiClient.post('/webhooks/payment', payload, {
        headers: {
          'X-Webhook-Signature': signature
        }
      });
      
      expect(response.status).toBe(200);
      
      // Verify payment status updated
      const payment = await apiClient.getPaymentStatus(testPayment._id);
      expect(payment.body.data.status).toBe('failed');
    });
    
    it('should verify webhook signature', async () => {
      const payload = {
        event: 'payment.success',
        data: {
          transactionId: testPayment.transactionId
        }
      };
      
      const response = await apiClient.post('/webhooks/payment', payload);
      
      expect(response.status).toBe(401);
      expect(response.body).toHaveProperty('message', 'Invalid webhook signature');
    });
    
    it('should handle unknown event types', async () => {
      const payload = {
        event: 'unknown.event',
        data: {}
      };
      
      const signature = generateWebhookSignature(payload, webhookSecret);
      
      const response = await apiClient.post('/webhooks/payment', payload, {
        headers: {
          'X-Webhook-Signature': signature
        }
      });
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('received', true);
    });
    
    it('should process webhook asynchronously', async () => {
      const payload = {
        event: 'payment.success',
        data: {
          transactionId: testPayment.transactionId
        }
      };
      
      const signature = generateWebhookSignature(payload, webhookSecret);
      
      const startTime = Date.now();
      const response = await apiClient.post('/webhooks/payment', payload, {
        headers: {
          'X-Webhook-Signature': signature
        }
      });
      const endTime = Date.now();
      
      expect(response.status).toBe(202);
      expect(endTime - startTime).toBeLessThan(100); // Should return quickly
    });
  });
  
  describe('POST /webhooks/parking', () => {
    it('should handle parking spot status update', async () => {
      const payload = {
        event: 'spot.status_changed',
        data: {
          spotId: testSpot._id,
          oldStatus: 'available',
          newStatus: 'occupied',
          timestamp: new Date().toISOString()
        }
      };
      
      const signature = generateWebhookSignature(payload, webhookSecret);
      
      const response = await apiClient.post('/webhooks/parking', payload, {
        headers: {
          'X-Webhook-Signature': signature
        }
      });
      
      expect(response.status).toBe(200);
      
      // Verify spot status updated
      const spot = await apiClient.getParkingSpotById(testSpot._id);
      expect(spot.body.data.status).toBe('occupied');
    });
    
    it('should handle sensor data', async () => {
      const payload = {
        event: 'sensor.data',
        data: {
          spotId: testSpot._id,
          occupancy: true,
          timestamp: new Date().toISOString(),
          sensorId: 'sensor_123'
        }
      };
      
      const signature = generateWebhookSignature(payload, webhookSecret);
      
      const response = await apiClient.post('/webhooks/parking', payload, {
        headers: {
          'X-Webhook-Signature': signature
        }
      });
      
      expect(response.status).toBe(200);
    });
  });
  
  describe('POST /webhooks/notification', () => {
    it('should handle notification delivery status', async () => {
      const payload = {
        event: 'notification.delivered',
        data: {
          notificationId: 'notif_123',
          status: 'delivered',
          timestamp: new Date().toISOString()
        }
      };
      
      const signature = generateWebhookSignature(payload, webhookSecret);
      
      const response = await apiClient.post('/webhooks/notification', payload, {
        headers: {
          'X-Webhook-Signature': signature
        }
      });
      
      expect(response.status).toBe(200);
    });
    
    it('should handle notification failure', async () => {
      const payload = {
        event: 'notification.failed',
        data: {
          notificationId: 'notif_123',
          error: 'Invalid recipient',
          timestamp: new Date().toISOString()
        }
      };
      
      const signature = generateWebhookSignature(payload, webhookSecret);
      
      const response = await apiClient.post('/webhooks/notification', payload, {
        headers: {
          'X-Webhook-Signature': signature
        }
      });
      
      expect(response.status).toBe(200);
    });
  });
  
  describe('Webhook retry mechanism', () => {
    it('should retry failed webhook deliveries', async () => {
      // Simulate webhook endpoint that fails first time
      let attemptCount = 0;
      
      const mockWebhookHandler = jest.fn().mockImplementation(() => {
        attemptCount++;
        if (attemptCount === 1) {
          throw new Error('Temporary failure');
        }
        return { status: 200 };
      });
      
      // Register webhook endpoint
      const webhookUrl = 'https://example.com/webhook';
      const response = await apiClient.post('/api/admin/webhooks', {
        url: webhookUrl,
        events: ['payment.success']
      });
      
      // Trigger webhook
      const payload = {
        event: 'payment.success',
        data: { transactionId: testPayment.transactionId }
      };
      
      // Should retry 3 times
      await apiClient.post('/webhooks/trigger', {
        webhookId: response.body.data.id,
        payload
      });
      
      // Wait for retries
      await new Promise(resolve => setTimeout(resolve, 5000));
      
      expect(mockWebhookHandler).toHaveBeenCalledTimes(3);
    });
  });
});

// Helper function to generate webhook signature
function generateWebhookSignature(payload, secret) {
  const timestamp = Math.floor(Date.now() / 1000);
  const payloadString = JSON.stringify(payload);
  const signaturePayload = `${timestamp}.${payloadString}`;
  const signature = crypto
    .createHmac('sha256', secret)
    .update(signaturePayload)
    .digest('hex');
  
  return `t=${timestamp},v1=${signature}`;
}