// parking-management/backend/tests/unit/test_api/payments/payments.test.js
const APIClient = require('../helpers/api-client');
const TestDataGenerator = require('../helpers/test-data');
const { Payment } = require('../../../../src/models');

describe('Payment API', () => {
  let apiClient;
  let testUser;
  let testAdmin;
  let testSpot;
  let testReservation;
  
  beforeEach(async () => {
    apiClient = new APIClient();
    
    // Create regular user
    const userData = TestDataGenerator.generateUser();
    const userResponse = await apiClient.register(userData);
    testUser = {
      id: userResponse.body.data.user._id,
      token: userResponse.body.data.token,
      email: userData.email
    };
    
    // Create admin user
    const adminData = TestDataGenerator.generateAdmin();
    const adminResponse = await apiClient.register(adminData);
    testAdmin = {
      id: adminResponse.body.data.user._id,
      token: adminResponse.body.data.token
    };
    
    apiClient.setAuthToken(testUser.token);
    
    // Create test parking spot
    const spotData = TestDataGenerator.generateParkingSpot();
    apiClient.setAdminToken(testAdmin.token);
    const spotResponse = await apiClient.createParkingSpot(spotData);
    testSpot = spotResponse.body.data;
    
    apiClient.setAuthToken(testUser.token);
    
    // Create test reservation
    const startTime = new Date(Date.now() + 3600000);
    const endTime = new Date(Date.now() + 7200000);
    
    const reservationResponse = await apiClient.createReservation({
      spotId: testSpot._id,
      startTime: startTime.toISOString(),
      endTime: endTime.toISOString(),
      vehicleNumber: 'ABC123'
    });
    
    testReservation = reservationResponse.body.data;
  });
  
  describe('POST /api/payments', () => {
    it('should process payment successfully', async () => {
      const paymentData = {
        reservationId: testReservation._id,
        amount: testReservation.totalAmount,
        method: 'credit_card',
        cardDetails: {
          number: '4111111111111111',
          expiry: '12/25',
          cvv: '123',
          name: 'Test User'
        }
      };
      
      const response = await apiClient.processPayment(paymentData);
      
      expect(response.status).toBe(201);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body.data).toHaveProperty('status', 'completed');
      expect(response.body.data).toHaveProperty('transactionId');
      expect(response.body.data).toHaveProperty('amount', testReservation.totalAmount);
      
      // Verify payment in database
      const payment = await Payment.findOne({ reservationId: testReservation._id });
      expect(payment).toBeTruthy();
      expect(payment.status).toBe('completed');
    });
    
    it('should process payment with different methods', async () => {
      const methods = ['paypal', 'apple_pay', 'google_pay'];
      
      for (const method of methods) {
        const paymentData = {
          reservationId: testReservation._id,
          amount: testReservation.totalAmount,
          method,
          ...(method === 'paypal' ? { email: 'user@example.com' } : {})
        };
        
        const response = await apiClient.processPayment(paymentData);
        
        expect(response.status).toBe(201);
        expect(response.body.data.method).toBe(method);
      }
    });
    
    it('should validate payment amount matches reservation', async () => {
      const paymentData = {
        reservationId: testReservation._id,
        amount: testReservation.totalAmount - 10,
        method: 'credit_card',
        cardDetails: {
          number: '4111111111111111',
          expiry: '12/25',
          cvv: '123'
        }
      };
      
      const response = await apiClient.processPayment(paymentData);
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Payment amount does not match reservation total');
    });
    
    it('should not process duplicate payment', async () => {
      const paymentData = {
        reservationId: testReservation._id,
        amount: testReservation.totalAmount,
        method: 'credit_card',
        cardDetails: {
          number: '4111111111111111',
          expiry: '12/25',
          cvv: '123'
        }
      };
      
      await apiClient.processPayment(paymentData);
      const response = await apiClient.processPayment(paymentData);
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Payment already processed for this reservation');
    });
    
    it('should handle invalid card details', async () => {
      const paymentData = {
        reservationId: testReservation._id,
        amount: testReservation.totalAmount,
        method: 'credit_card',
        cardDetails: {
          number: '1234567890123456',
          expiry: '12/25',
          cvv: '123'
        }
      };
      
      const response = await apiClient.processPayment(paymentData);
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Invalid card details');
    });
    
    it('should handle payment gateway errors', async () => {
      const paymentData = {
        reservationId: testReservation._id,
        amount: testReservation.totalAmount,
        method: 'credit_card',
        cardDetails: {
          number: '4000000000000002', // Card that declines
          expiry: '12/25',
          cvv: '123'
        }
      };
      
      const response = await apiClient.processPayment(paymentData);
      
      expect(response.status).toBe(402);
      expect(response.body).toHaveProperty('message', 'Payment declined');
    });
    
    it('should require authentication', async () => {
      apiClient.setAuthToken(null);
      const response = await apiClient.processPayment({
        reservationId: testReservation._id,
        amount: testReservation.totalAmount,
        method: 'credit_card'
      });
      
      expect(response.status).toBe(401);
    });
  });
  
  describe('GET /api/payments/:id', () => {
    let testPayment;
    
    beforeEach(async () => {
      const paymentData = {
        reservationId: testReservation._id,
        amount: testReservation.totalAmount,
        method: 'credit_card',
        cardDetails: {
          number: '4111111111111111',
          expiry: '12/25',
          cvv: '123'
        }
      };
      
      const response = await apiClient.processPayment(paymentData);
      testPayment = response.body.data;
    });
    
    it('should get payment status', async () => {
      const response = await apiClient.getPaymentStatus(testPayment._id);
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('status', 'completed');
      expect(response.body.data).toHaveProperty('amount', testReservation.totalAmount);
      expect(response.body.data).toHaveProperty('transactionId');
      expect(response.body.data).toHaveProperty('reservation');
    });
    
    it('should return 403 for other user payment', async () => {
      const { token } = await apiClient.register(TestDataGenerator.generateUser());
      apiClient.setAuthToken(token);
      
      const response = await apiClient.getPaymentStatus(testPayment._id);
      
      expect(response.status).toBe(403);
    });
    
    it('should return 404 for non-existent payment', async () => {
      const response = await apiClient.getPaymentStatus('507f1f77bcf86cd799439011');
      
      expect(response.status).toBe(404);
    });
  });
  
  describe('POST /api/payments/:id/refund', () => {
    let testPayment;
    
    beforeEach(async () => {
      const paymentData = {
        reservationId: testReservation._id,
        amount: testReservation.totalAmount,
        method: 'credit_card',
        cardDetails: {
          number: '4111111111111111',
          expiry: '12/25',
          cvv: '123'
        }
      };
      
      const response = await apiClient.processPayment(paymentData);
      testPayment = response.body.data;
    });
    
    it('should refund payment', async () => {
      const response = await apiClient.refundPayment(testPayment._id);
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('status', 'refunded');
      expect(response.body.data).toHaveProperty('refundedAt');
      expect(response.body.data).toHaveProperty('refundAmount', testPayment.amount);
      
      // Verify database
      const payment = await Payment.findById(testPayment._id);
      expect(payment.status).toBe('refunded');
    });
    
    it('should not refund already refunded payment', async () => {
      await apiClient.refundPayment(testPayment._id);
      const response = await apiClient.refundPayment(testPayment._id);
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Payment already refunded');
    });
    
    it('should not refund pending payment', async () => {
      // Create pending payment
      const pendingPayment = await Payment.create({
        reservationId: testReservation._id,
        amount: testReservation.totalAmount,
        method: 'credit_card',
        status: 'pending',
        transactionId: 'pending_txn'
      });
      
      const response = await apiClient.refundPayment(pendingPayment._id);
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Cannot refund pending payment');
    });
    
    it('should require admin or owner for refund', async () => {
      const { token } = await apiClient.register(TestDataGenerator.generateUser());
      apiClient.setAuthToken(token);
      
      const response = await apiClient.refundPayment(testPayment._id);
      
      expect(response.status).toBe(403);
    });
    
    it('should allow admin to refund any payment', async () => {
      apiClient.setAdminToken(testAdmin.token);
      const response = await apiClient.refundPayment(testPayment._id);
      
      expect(response.status).toBe(200);
    });
  });
  
  describe('GET /api/payments', () => {
    beforeEach(async () => {
      // Create multiple payments
      const reservation2 = await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: new Date(Date.now() + 86400000).toISOString(),
        endTime: new Date(Date.now() + 90000000).toISOString(),
        vehicleNumber: 'XYZ789'
      });
      
      const paymentData = {
        reservationId: reservation2.body.data._id,
        amount: reservation2.body.data.totalAmount,
        method: 'credit_card'
      };
      
      await apiClient.processPayment(paymentData);
      await apiClient.processPayment({
        ...paymentData,
        reservationId: testReservation._id
      });
    });
    
    it('should list payments for user', async () => {
      const response = await apiClient.get('/api/payments');
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('payments');
      expect(response.body.data.payments.length).toBeGreaterThanOrEqual(2);
      expect(response.body.data).toHaveProperty('pagination');
    });
    
    it('should filter payments by status', async () => {
      const response = await apiClient.get('/api/payments?status=completed');
      
      expect(response.status).toBe(200);
      expect(response.body.data.payments.every(p => p.status === 'completed')).toBe(true);
    });
    
    it('should filter payments by date range', async () => {
      const startDate = new Date();
      startDate.setHours(0, 0, 0, 0);
      
      const endDate = new Date();
      endDate.setDate(endDate.getDate() + 1);
      
      const response = await apiClient.get('/api/payments', {
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString()
      });
      
      expect(response.status).toBe(200);
      expect(response.body.data.payments.length).toBeGreaterThanOrEqual(2);
    });
    
    it('should show only admin total amounts', async () => {
      const response = await apiClient.get('/api/payments');
      
      expect(response.body.data).toHaveProperty('summary');
      expect(response.body.data.summary).toHaveProperty('totalAmount');
      expect(response.body.data.summary).toHaveProperty('count');
    });
  });
});