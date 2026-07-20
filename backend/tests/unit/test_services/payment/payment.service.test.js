// parking-management/backend/tests/unit/test_services/payment/payment.service.test.js
const PaymentService = require('../../../../src/services/payment.service');
const PaymentGateway = require('../../../../src/services/payment-gateway.service');
const EmailService = require('../../../../src/services/email.service');
const TestDataFactory = require('../helpers/test-data-factory');
const { Payment, Reservation } = require('../../../../src/models');

describe('PaymentService', () => {
  let paymentService;
  let paymentGateway;
  let emailService;
  
  beforeEach(() => {
    paymentGateway = new PaymentGateway();
    emailService = new EmailService();
    paymentService = new PaymentService(paymentGateway, emailService);
  });
  
  describe('processPayment', () => {
    let reservation;
    
    beforeEach(async () => {
      reservation = await Reservation.create(
        TestDataFactory.generateReservation(
          new mongoose.Types.ObjectId(),
          new mongoose.Types.ObjectId(),
          { totalAmount: 100 }
        )
      );
    });
    
    it('should process payment successfully', async () => {
      const paymentData = {
        reservationId: reservation._id,
        amount: 100,
        method: 'credit_card',
        cardDetails: {
          number: '4111111111111111',
          expiry: '12/25',
          cvv: '123',
          name: 'Test User'
        }
      };
      
      const result = await paymentService.processPayment(paymentData);
      
      expect(result).toHaveProperty('success', true);
      expect(result).toHaveProperty('transactionId');
      expect(result).toHaveProperty('amount', 100);
      
      // Verify payment record
      const payment = await Payment.findOne({ reservationId: reservation._id });
      expect(payment).toBeDefined();
      expect(payment.status).toBe('completed');
      expect(payment.transactionId).toBe(result.transactionId);
    });
    
    it('should handle payment failure', async () => {
      jest.spyOn(paymentGateway, 'charge').mockRejectedValue(new Error('Insufficient funds'));
      
      const paymentData = {
        reservationId: reservation._id,
        amount: 100,
        method: 'credit_card',
        cardDetails: {
          number: '4000000000000002', // Declined card
          expiry: '12/25',
          cvv: '123'
        }
      };
      
      await expect(paymentService.processPayment(paymentData))
        .rejects
        .toThrow('Payment failed');
      
      const payment = await Payment.findOne({ reservationId: reservation._id });
      expect(payment.status).toBe('failed');
    });
    
    it('should validate amount matches reservation', async () => {
      const paymentData = {
        reservationId: reservation._id,
        amount: 90, // Less than total
        method: 'credit_card'
      };
      
      await expect(paymentService.processPayment(paymentData))
        .rejects
        .toThrow('Amount does not match reservation');
    });
    
    it('should prevent duplicate payments', async () => {
      const paymentData = {
        reservationId: reservation._id,
        amount: 100,
        method: 'credit_card'
      };
      
      await paymentService.processPayment(paymentData);
      
      await expect(paymentService.processPayment(paymentData))
        .rejects
        .toThrow('Payment already processed');
    });
    
    it('should send receipt email', async () => {
      const paymentData = {
        reservationId: reservation._id,
        amount: 100,
        method: 'credit_card'
      };
      
      await paymentService.processPayment(paymentData);
      
      expect(emailService.sendPaymentReceipt).toHaveBeenCalled();
    });
  });
  
  describe('refundPayment', () => {
    let payment;
    let reservation;
    
    beforeEach(async () => {
      reservation = await Reservation.create(
        TestDataFactory.generateReservation(
          new mongoose.Types.ObjectId(),
          new mongoose.Types.ObjectId(),
          { totalAmount: 100 }
        )
      );
      
      payment = await Payment.create({
        reservationId: reservation._id,
        amount: 100,
        method: 'credit_card',
        status: 'completed',
        transactionId: 'txn_test_123'
      });
    });
    
    it('should refund payment successfully', async () => {
      const result = await paymentService.refundPayment(payment._id);
      
      expect(result).toHaveProperty('success', true);
      expect(result).toHaveProperty('refundId');
      
      const updatedPayment = await Payment.findById(payment._id);
      expect(updatedPayment.status).toBe('refunded');
      expect(updatedPayment.refundedAt).toBeDefined();
      expect(updatedPayment.refundId).toBe(result.refundId);
    });
    
    it('should calculate partial refund', async () => {
      const result = await paymentService.refundPayment(payment._id, 50);
      
      expect(result.refundAmount).toBe(50);
      
      const updatedPayment = await Payment.findById(payment._id);
      expect(updatedPayment.refundAmount).toBe(50);
      expect(updatedPayment.status).toBe('partially_refunded');
    });
    
    it('should not refund already refunded payment', async () => {
      payment.status = 'refunded';
      await payment.save();
      
      await expect(paymentService.refundPayment(payment._id))
        .rejects
        .toThrow('Payment already refunded');
    });
    
    it('should handle refund failure', async () => {
      jest.spyOn(paymentGateway, 'refund').mockRejectedValue(new Error('Refund failed'));
      
      await expect(paymentService.refundPayment(payment._id))
        .rejects
        .toThrow('Refund failed');
      
      const updatedPayment = await Payment.findById(payment._id);
      expect(updatedPayment.status).toBe('completed');
    });
  });
  
  describe('getPaymentStatus', () => {
    let payment;
    
    beforeEach(async () => {
      payment = await Payment.create({
        reservationId: new mongoose.Types.ObjectId(),
        amount: 100,
        method: 'credit_card',
        status: 'completed',
        transactionId: 'txn_test_123'
      });
    });
    
    it('should get payment status', async () => {
      const status = await paymentService.getPaymentStatus(payment._id);
      
      expect(status).toHaveProperty('status', 'completed');
      expect(status).toHaveProperty('amount', 100);
      expect(status).toHaveProperty('transactionId');
    });
    
    it('should verify with gateway', async () => {
      jest.spyOn(paymentGateway, 'getTransactionStatus').mockResolvedValue({
        status: 'settled',
        settledAt: new Date()
      });
      
      const status = await paymentService.getPaymentStatus(payment._id, { verify: true });
      
      expect(status.gatewayStatus).toBe('settled');
    });
  });
  
  describe('getPaymentAnalytics', () => {
    beforeEach(async () => {
      // Create multiple payments
      for (let i = 0; i < 10; i++) {
        await Payment.create({
          reservationId: new mongoose.Types.ObjectId(),
          amount: Math.random() * 100,
          method: ['credit_card', 'paypal', 'apple_pay'][i % 3],
          status: 'completed',
          createdAt: new Date(Date.now() - i * 86400000)
        });
      }
    });
    
    it('should calculate payment analytics', async () => {
      const analytics = await paymentService.getPaymentAnalytics(30);
      
      expect(analytics).toHaveProperty('totalRevenue');
      expect(analytics).toHaveProperty('totalTransactions');
      expect(analytics).toHaveProperty('averageTransactionValue');
      expect(analytics).toHaveProperty('methodBreakdown');
      expect(analytics).toHaveProperty('dailyRevenue');
    });
    
    it('should calculate success rate', async () => {
      // Create some failed payments
      for (let i = 0; i < 5; i++) {
        await Payment.create({
          reservationId: new mongoose.Types.ObjectId(),
          amount: 50,
          method: 'credit_card',
          status: 'failed'
        });
      }
      
      const analytics = await paymentService.getPaymentAnalytics(30);
      
      expect(analytics).toHaveProperty('successRate');
      expect(analytics.successRate).toBeLessThan(100);
      expect(analytics.successRate).toBeGreaterThan(0);
    });
  });
});