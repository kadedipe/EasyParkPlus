// parking-management/backend/tests/fixtures/models/payment.fixtures.js
const paymentFixtures = {
  // Successful credit card payment
  creditCardSuccess: {
    method: 'credit_card',
    amount: 50.00,
    status: 'completed',
    transactionId: 'txn_credit_123456',
    cardDetails: {
      last4: '4242',
      brand: 'visa',
      expiryMonth: 12,
      expiryYear: 2025
    },
    billingAddress: {
      line1: '123 Billing St',
      city: 'New York',
      state: 'NY',
      zipCode: '10001',
      country: 'USA'
    }
  },
  
  // PayPal payment
  paypal: {
    method: 'paypal',
    amount: 75.50,
    status: 'completed',
    transactionId: 'paypal_txn_789012',
    paypalDetails: {
      payerEmail: 'user@example.com',
      payerId: 'PAYER123456'
    }
  },
  
  // Apple Pay
  applePay: {
    method: 'apple_pay',
    amount: 30.00,
    status: 'completed',
    transactionId: 'apple_txn_345678',
    applePayDetails: {
      transactionIdentifier: 'APPLE_123456'
    }
  },
  
  // Pending payment
  pending: {
    method: 'credit_card',
    amount: 25.00,
    status: 'pending',
    transactionId: null
  },
  
  // Failed payment
  failed: {
    method: 'credit_card',
    amount: 40.00,
    status: 'failed',
    transactionId: null,
    failureReason: 'Insufficient funds'
  },
  
  // Refunded payment
  refunded: {
    method: 'credit_card',
    amount: 60.00,
    status: 'refunded',
    transactionId: 'txn_refund_567890',
    refundedAt: new Date(),
    refundAmount: 60.00,
    refundReason: 'Customer cancellation'
  },
  
  // Partial refund
  partialRefund: {
    method: 'credit_card',
    amount: 100.00,
    status: 'partially_refunded',
    transactionId: 'txn_partial_901234',
    refundedAt: new Date(),
    refundAmount: 50.00,
    remainingAmount: 50.00
  },
  
  // Multiple payments for same reservation
  multiplePayments: [
    {
      method: 'credit_card',
      amount: 50.00,
      status: 'completed',
      transactionId: 'txn_multi_1'
    },
    {
      method: 'credit_card',
      amount: 25.00,
      status: 'completed',
      transactionId: 'txn_multi_2'
    }
  ],
  
  // Test card numbers (for payment gateway mocking)
  testCards: {
    success: '4111111111111111',
    decline: '4000000000000002',
    insufficientFunds: '4000000000009995',
    invalidCvv: '4000000000000127',
    expired: '4000000000000069'
  },
  
  // Invalid payment data
  invalid: {
    negativeAmount: {
      method: 'credit_card',
      amount: -10.00
    },
    missingMethod: {
      amount: 50.00
    },
    invalidMethod: {
      method: 'crypto',
      amount: 50.00
    },
    mismatchedAmount: {
      method: 'credit_card',
      amount: 30.00,
      reservationAmount: 50.00
    }
  }
};

module.exports = paymentFixtures;