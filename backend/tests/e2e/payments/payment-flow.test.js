// parking-management/backend/tests/e2e/payments/payment-flow.test.js
const E2EClient = require('../helpers/e2e-client');
const TestDataFactory = require('../helpers/test-data-factory');

describe('Payment E2E Flow', () => {
  let client;
  let adminClient;
  let testSpot;
  let testReservation;
  
  beforeEach(async () => {
    client = new E2EClient();
    adminClient = new E2EClient();
    
    // Create admin
    const adminData = TestDataFactory.generateUser({ role: 'admin' });
    await adminClient.register(adminData);
    
    // Create regular user
    const userData = TestDataFactory.generateUser();
    await client.register(userData);
    
    // Create test parking spot
    const spotData = TestDataFactory.generateParkingSpot();
    const spotResponse = await adminClient.createParkingSpot(spotData);
    testSpot = spotResponse.body.data;
    
    // Create reservation
    const startTime = new Date(Date.now() + 86400000);
    const endTime = new Date(Date.now() + 90000000);
    
    const reservationResponse = await client.createReservation({
      spotId: testSpot._id,
      startTime: startTime.toISOString(),
      endTime: endTime.toISOString(),
      vehicleNumber: 'ABC123'
    });
    
    testReservation = reservationResponse.body.data;
  });
  
  describe('Complete Payment Processing Flow', () => {
    it('should process payment for reservation', async () => {
      // Step 1: Process payment
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
      
      const paymentResponse = await client.processPayment(paymentData);
      
      expect(paymentResponse.status).toBe(201);
      expect(paymentResponse.body.data).toHaveProperty('status', 'completed');
      expect(paymentResponse.body.data).toHaveProperty('transactionId');
      expect(paymentResponse.body.data).toHaveProperty('amount', testReservation.totalAmount);
      
      // Step 2: Get payment status
      const paymentId = paymentResponse.body.data._id;
      const statusResponse = await client.getPaymentStatus(paymentId);
      
      expect(statusResponse.status).toBe(200);
      expect(statusResponse.body.data).toHaveProperty('status', 'completed');
      expect(statusResponse.body.data).toHaveProperty('reservation');
      
      // Step 3: Verify reservation status updated
      const reservation = await client.getReservationById(testReservation._id);
      expect(reservation.body.data).toHaveProperty('paymentStatus', 'paid');
    });
    
    it('should handle payment failure and retry', async () => {
      // Step 1: Attempt payment with insufficient funds
      const paymentData = {
        reservationId: testReservation._id,
        amount: testReservation.totalAmount,
        method: 'credit_card',
        cardDetails: {
          number: '4000000000000002', // Declined card
          expiry: '12/25',
          cvv: '123',
          name: 'Test User'
        }
      };
      
      const failedPayment = await client.processPayment(paymentData);
      
      expect(failedPayment.status).toBe(402);
      expect(failedPayment.body).toHaveProperty('message', 'Payment declined');
      
      // Step 2: Retry with different card
      const retryData = {
        ...paymentData,
        cardDetails: {
          number: '4111111111111111',
          expiry: '12/25',
          cvv: '123',
          name: 'Test User'
        }
      };
      
      const successPayment = await client.processPayment(retryData);
      
      expect(successPayment.status).toBe(201);
      expect(successPayment.body.data).toHaveProperty('status', 'completed');
    });
    
    it('should process refund', async () => {
      // Step 1: Process initial payment
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
      
      const paymentResponse = await client.processPayment(paymentData);
      const paymentId = paymentResponse.body.data._id;
      
      // Step 2: Cancel reservation (should trigger refund)
      const cancelResponse = await client.cancelReservation(testReservation._id);
      
      expect(cancelResponse.status).toBe(200);
      expect(cancelResponse.body.data).toHaveProperty('refund');
      expect(cancelResponse.body.data.refund).toHaveProperty('amount', testReservation.totalAmount);
      
      // Step 3: Verify payment status updated
      const paymentStatus = await client.getPaymentStatus(paymentId);
      expect(paymentStatus.body.data.status).toBe('refunded');
    });
    
    it('should handle partial refund', async () => {
      // Step 1: Process payment
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
      
      const paymentResponse = await client.processPayment(paymentData);
      const paymentId = paymentResponse.body.data._id;
      
      // Step 2: Process partial refund via admin
      const refundResponse = await client.refundPayment(paymentId, {
        amount: testReservation.totalAmount / 2,
        reason: 'Customer partial cancellation'
      });
      
      expect(refundResponse.status).toBe(200);
      expect(refundResponse.body.data).toHaveProperty('refundAmount', testReservation.totalAmount / 2);
      expect(refundResponse.body.data).toHaveProperty('status', 'partially_refunded');
      
      // Step 3: Verify remaining balance
      const paymentStatus = await client.getPaymentStatus(paymentId);
      expect(paymentStatus.body.data.refundAmount).toBe(testReservation.totalAmount / 2);
      expect(paymentStatus.body.data.remainingAmount).toBe(testReservation.totalAmount / 2);
    });
  });
});