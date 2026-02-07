const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const Stripe = require('stripe');
const paypal = require('@paypal/checkout-server-sdk');
const { 
  metrics, 
  metricsMiddleware, 
  createPaymentProcessorWrapper,
  createFraudDetectionWrapper,
  createSettlementProcessorWrapper,
  createWebhookProcessorWrapper,
  updateQueueMetrics,
  getMetrics 
} = require('./metrics');

const app = express();

// Security middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", "'unsafe-inline'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      imgSrc: ["'self'", "data:", "https:"],
      connectSrc: ["'self'", "https://api.stripe.com", "https://api.paypal.com"]
    }
  }
}));
app.use(cors());
app.use(compression());

// Rate limiting
const paymentLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many payment requests from this IP, please try again after 15 minutes'
});

// Apply rate limiting to payment endpoints
app.use('/api/v1/payments/process', paymentLimiter);
app.use('/api/v1/payments/refund', paymentLimiter);

// Metrics middleware
app.use(metricsMiddleware());

// Body parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Request logging middleware
app.use((req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`[Payment] ${req.method} ${req.originalUrl} ${res.statusCode} ${duration}ms`);
  });
  
  next();
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Payment Service Error:', err);
  
  // Increment error metrics
  metrics.transactionErrorsTotal.inc({
    error_type: err.name || 'UnknownError',
    gateway: req.headers['x-payment-gateway'] || 'unknown',
    payment_method: req.body?.payment_method || 'unknown'
  });

  res.status(err.status || 500).json({
    error: err.name || 'PaymentError',
    message: err.message || 'An error occurred while processing your payment',
    code: err.code || 'INTERNAL_ERROR',
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
  });
});

// Initialize payment gateways
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
const paypalClient = new paypal.core.PayPalHttpClient(
  new paypal.core.SandboxEnvironment(
    process.env.PAYPAL_CLIENT_ID,
    process.env.PAYPAL_CLIENT_SECRET
  )
);

// Create wrapped payment processors
const stripeProcessor = createPaymentProcessorWrapper('stripe', {
  charge: async (paymentData) => {
    const { amount, currency, paymentMethod, description, metadata } = paymentData;
    
    const paymentIntent = await stripe.paymentIntents.create({
      amount: Math.round(amount * 100), // Convert to cents
      currency,
      payment_method: paymentMethod,
      confirm: true,
      description,
      metadata
    });

    return {
      id: paymentIntent.id,
      status: paymentIntent.status,
      clientSecret: paymentIntent.client_secret,
      amount: paymentIntent.amount / 100,
      currency: paymentIntent.currency
    };
  },

  refund: async (paymentIntentId, amount, reason) => {
    const refund = await stripe.refunds.create({
      payment_intent: paymentIntentId,
      amount: Math.round(amount * 100),
      reason: reason || 'requested_by_customer'
    });

    return refund;
  },

  createToken: async (cardData) => {
    const token = await stripe.tokens.create({
      card: {
        number: cardData.number,
        exp_month: cardData.exp_month,
        exp_year: cardData.exp_year,
        cvc: cardData.cvc
      }
    });

    return token;
  }
});

const paypalProcessor = createPaymentProcessorWrapper('paypal', {
  charge: async (paymentData) => {
    const { amount, currency, description } = paymentData;
    
    const request = new paypal.orders.OrdersCreateRequest();
    request.prefer("return=representation");
    request.requestBody({
      intent: 'CAPTURE',
      purchase_units: [{
        amount: {
          currency_code: currency,
          value: amount.toString()
        },
        description
      }]
    });

    const order = await paypalClient.execute(request);
    
    return {
      id: order.result.id,
      status: order.result.status,
      links: order.result.links
    };
  },

  refund: async (captureId, amount, reason) => {
    const request = new paypal.payments.CapturesRefundRequest(captureId);
    request.requestBody({
      amount: {
        value: amount.toString(),
        currency_code: 'USD'
      },
      note_to_payer: reason
    });

    const refund = await paypalClient.execute(request);
    return refund;
  },

  createToken: async () => {
    // PayPal doesn't use tokens in the same way as Stripe
    return { type: 'paypal', token: null };
  }
});

// Fraud detection
const fraudDetector = createFraudDetectionWrapper({
  type: 'advanced',
  check: async (transactionData) => {
    // Implement fraud detection logic
    const { amount, ipAddress, email, billingAddress } = transactionData;
    
    // Simple risk calculation
    let riskScore = 0;
    
    if (amount > 1000) riskScore += 20;
    if (ipAddress && isHighRiskIP(ipAddress)) riskScore += 30;
    if (email && isSuspiciousEmail(email)) riskScore += 25;
    
    const riskLevel = riskScore > 50 ? 'high' : riskScore > 20 ? 'medium' : 'low';
    
    return {
      riskScore,
      riskLevel,
      recommendations: riskLevel === 'high' ? ['require_manual_review'] : []
    };
  }
});

// Webhook processor
const webhookProcessor = createWebhookProcessorWrapper({
  process: async (gateway, type, payload) => {
    switch (type) {
      case 'payment_intent.succeeded':
        await handleSuccessfulPayment(payload);
        break;
      case 'payment_intent.failed':
        await handleFailedPayment(payload);
        break;
      case 'charge.refunded':
        await handleRefund(payload);
        break;
      case 'charge.dispute.created':
        await handleChargeback(payload);
        break;
      default:
        console.log(`Unhandled webhook type: ${type}`);
    }
    
    return { processed: true };
  }
});

// Payment endpoints
app.post('/api/v1/payments/process', async (req, res, next) => {
  try {
    const {
      amount,
      currency = 'USD',
      payment_method,
      gateway = 'stripe',
      description,
      metadata = {},
      customer_id,
      billing_address,
      shipping_address
    } = req.body;

    // Validate input
    if (!amount || !payment_method) {
      throw new Error('Amount and payment method are required');
    }

    if (amount <= 0) {
      throw new Error('Amount must be greater than 0');
    }

    // Check fraud risk
    const fraudCheck = await fraudDetector.check({
      amount,
      ipAddress: req.ip,
      email: metadata.email,
      billingAddress: billing_address
    });

    if (fraudCheck.riskLevel === 'high') {
      return res.status(400).json({
        error: 'HighRiskTransaction',
        message: 'This transaction requires manual review',
        fraudCheck
      });
    }

    // Process payment based on gateway
    let result;
    switch (gateway) {
      case 'stripe':
        result = await stripeProcessor.charge({
          amount,
          currency,
          paymentMethod: payment_method,
          description,
          metadata: {
            ...metadata,
            customer_id,
            fraud_risk: fraudCheck.riskLevel
          }
        });
        break;
      case 'paypal':
        result = await paypalProcessor.charge({
          amount,
          currency,
          description,
          metadata
        });
        break;
      default:
        throw new Error(`Unsupported payment gateway: ${gateway}`);
    }

    // Record transaction in database
    const transaction = await saveTransaction({
      transaction_id: result.id,
      gateway,
      amount,
      currency,
      payment_method,
      status: result.status,
      customer_id,
      billing_address,
      shipping_address,
      fraud_check: fraudCheck,
      metadata
    });

    res.json({
      success: true,
      transaction: {
        id: transaction.id,
        transaction_id: transaction.transaction_id,
        gateway,
        amount,
        currency,
        status: transaction.status,
        fraud_check: fraudCheck,
        created_at: transaction.created_at
      },
      ...(result.clientSecret && { client_secret: result.clientSecret }),
      ...(result.links && { links: result.links })
    });
  } catch (error) {
    next(error);
  }
});

app.post('/api/v1/payments/refund', async (req, res, next) => {
  try {
    const {
      transaction_id,
      amount,
      reason = 'customer_request',
      gateway = 'stripe'
    } = req.body;

    if (!transaction_id || !amount) {
      throw new Error('Transaction ID and amount are required');
    }

    // Get original transaction
    const originalTransaction = await getTransaction(transaction_id);
    if (!originalTransaction) {
      throw new Error('Transaction not found');
    }

    if (originalTransaction.status !== 'succeeded') {
      throw new Error('Only successful transactions can be refunded');
    }

    // Process refund based on gateway
    let refundResult;
    switch (gateway) {
      case 'stripe':
        refundResult = await stripeProcessor.refund(
          originalTransaction.gateway_transaction_id,
          amount,
          reason
        );
        break;
      case 'paypal':
        refundResult = await paypalProcessor.refund(
          originalTransaction.gateway_transaction_id,
          amount,
          reason
        );
        break;
      default:
        throw new Error(`Unsupported payment gateway: ${gateway}`);
    }

    // Record refund in database
    const refund = await saveRefund({
      transaction_id: originalTransaction.id,
      gateway,
      amount,
      reason,
      gateway_refund_id: refundResult.id,
      status: refundResult.status
    });

    res.json({
      success: true,
      refund: {
        id: refund.id,
        transaction_id: refund.transaction_id,
        amount,
        reason,
        status: refund.status,
        created_at: refund.created_at
      }
    });
  } catch (error) {
    next(error);
  }
});

app.post('/api/v1/payments/tokenize', async (req, res, next) => {
  try {
    const {
      gateway = 'stripe',
      card_data,
      customer_id
    } = req.body;

    if (!card_data) {
      throw new Error('Card data is required');
    }

    let token;
    switch (gateway) {
      case 'stripe':
        token = await stripeProcessor.createToken(card_data);
        break;
      default:
        throw new Error(`Tokenization not supported for gateway: ${gateway}`);
    }

    // Save token securely
    const savedToken = await savePaymentToken({
      gateway,
      token_id: token.id,
      customer_id,
      token_type: 'card',
      last_four: card_data.number.slice(-4),
      expiry_month: card_data.exp_month,
      expiry_year: card_data.exp_year
    });

    res.json({
      success: true,
      token: {
        id: savedToken.id,
        token_id: savedToken.token_id,
        gateway,
        last_four: savedToken.last_four,
        expiry: `${savedToken.expiry_month}/${savedToken.expiry_year}`
      }
    });
  } catch (error) {
    next(error);
  }
});

// Webhook endpoints
app.post('/webhooks/stripe', express.raw({ type: 'application/json' }), async (req, res) => {
  const sig = req.headers['stripe-signature'];
  
  try {
    const event = stripe.webhooks.constructEvent(
      req.body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );

    await webhookProcessor.process('stripe', event.type, event.data.object);
    
    res.json({ received: true });
  } catch (error) {
    console.error('Stripe webhook error:', error);
    res.status(400).send(`Webhook Error: ${error.message}`);
  }
});

app.post('/webhooks/paypal', async (req, res) => {
  try {
    const { event_type, resource } = req.body;
    
    await webhookProcessor.process('paypal', event_type, resource);
    
    res.json({ received: true });
  } catch (error) {
    console.error('PayPal webhook error:', error);
    res.status(400).json({ error: 'Webhook processing failed' });
  }
});

// Settlement endpoints
app.post('/api/v1/payments/settlements/process', async (req, res, next) => {
  try {
    const { gateway, date = new Date().toISOString().split('T')[0] } = req.body;

    // Process settlement
    const settlementProcessor = createSettlementProcessorWrapper({
      processSettlement: async (gateway, date) => {
        // Implement settlement processing logic
        // This would typically involve:
        // 1. Fetching transactions from the gateway
        // 2. Reconciling with our records
        // 3. Generating settlement report
        // 4. Updating database
        
        return {
          gateway,
          date,
          amount: 10000, // Example amount
          currency: 'USD',
          transaction_count: 150
        };
      }
    });

    const settlement = await settlementProcessor.processSettlement(gateway, date);

    res.json({
      success: true,
      settlement
    });
  } catch (error) {
    next(error);
  }
});

// Health check endpoint
app.get('/health', async (req, res) => {
  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    gateways: {
      stripe: await checkStripeHealth(),
      paypal: await checkPaypalHealth()
    },
    database: await checkDatabaseHealth(),
    redis: await checkRedisHealth()
  };

  res.json(health);
});

// Metrics endpoint (Prometheus format)
app.get('/metrics', async (req, res) => {
  try {
    res.set('Content-Type', 'text/plain');
    res.end(await getMetrics());
  } catch (error) {
    res.status(500).end();
  }
});

// Admin endpoints
app.get('/api/v1/admin/transactions/summary', async (req, res, next) => {
  try {
    const { start_date, end_date, gateway, currency } = req.query;
    
    const summary = await getTransactionSummary({
      start_date,
      end_date,
      gateway,
      currency
    });

    res.json(summary);
  } catch (error) {
    next(error);
  }
});

app.get('/api/v1/admin/fraud/report', async (req, res, next) => {
  try {
    const { start_date, end_date } = req.query;
    
    const report = await getFraudReport({
      start_date,
      end_date
    });

    res.json(report);
  } catch (error) {
    next(error);
  }
});

// Helper functions
async function checkStripeHealth() {
  try {
    await stripe.balance.retrieve();
    return { status: 'healthy' };
  } catch (error) {
    return { status: 'unhealthy', error: error.message };
  }
}

async function checkPaypalHealth() {
  try {
    // Simple PayPal health check
    return { status: 'healthy' };
  } catch (error) {
    return { status: 'unhealthy', error: error.message };
  }
}

async function checkDatabaseHealth() {
  try {
    // Check database connection
    return { status: 'connected' };
  } catch (error) {
    return { status: 'disconnected', error: error.message };
  }
}

async function checkRedisHealth() {
  try {
    // Check Redis connection
    return { status: 'connected' };
  } catch (error) {
    return { status: 'disconnected', error: error.message };
  }
}

async function saveTransaction(data) {
  // Save transaction to database
  // This is a mock implementation
  return {
    id: 'txn_' + Date.now(),
    ...data,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };
}

async function getTransaction(id) {
  // Get transaction from database
  // This is a mock implementation
  return null;
}

async function saveRefund(data) {
  // Save refund to database
  // This is a mock implementation
  return {
    id: 'ref_' + Date.now(),
    ...data,
    created_at: new Date().toISOString()
  };
}

async function savePaymentToken(data) {
  // Save payment token to database
  // This is a mock implementation
  return {
    id: 'tok_' + Date.now(),
    ...data,
    created_at: new Date().toISOString()
  };
}

async function getTransactionSummary(params) {
  // Get transaction summary from database
  // This is a mock implementation
  return {
    total_transactions: 1000,
    total_amount: 50000,
    successful_transactions: 980,
    failed_transactions: 20,
    average_amount: 50,
    by_gateway: {
      stripe: { count: 700, amount: 35000 },
      paypal: { count: 300, amount: 15000 }
    },
    by_currency: {
      USD: { count: 800, amount: 40000 },
      EUR: { count: 200, amount: 10000 }
    }
  };
}

async function getFraudReport(params) {
  // Get fraud report from database
  // This is a mock implementation
  return {
    total_checks: 1000,
    high_risk: 10,
    medium_risk: 50,
    low_risk: 940,
    blocked_transactions: 5,
    saved_amount: 5000
  };
}

async function handleSuccessfulPayment(payload) {
  // Handle successful payment webhook
  console.log('Payment successful:', payload.id);
  
  // Update transaction status in database
  // Send confirmation email
  // Trigger fulfillment process
}

async function handleFailedPayment(payload) {
  // Handle failed payment webhook
  console.log('Payment failed:', payload.id);
  
  // Update transaction status in database
  // Send failure notification
  // Trigger retry logic if applicable
}

async function handleRefund(payload) {
  // Handle refund webhook
  console.log('Refund processed:', payload.id);
  
  // Update refund status in database
  // Send refund confirmation
}

async function handleChargeback(payload) {
  // Handle chargeback webhook
  console.log('Chargeback received:', payload.id);
  
  metrics.chargebacksTotal.inc({
    gateway: 'stripe',
    reason: payload.reason || 'unknown'
  });
  
  // Update transaction status
  // Notify customer support
  // Start dispute process
}

function isHighRiskIP(ipAddress) {
  // Simple IP risk check
  // In production, use a service like MaxMind
  return false;
}

function isSuspiciousEmail(email) {
  // Simple email risk check
  const suspiciousDomains = ['tempmail.com', 'mailinator.com', 'guerrillamail.com'];
  const domain = email.split('@')[1];
  return suspiciousDomains.includes(domain);
}

// Start periodic metric updates
setInterval(() => {
  // Update queue metrics if using a queue system
  // updateQueueMetrics(paymentQueue);
}, 30000); // Update every 30 seconds

module.exports = {
  app,
  stripeProcessor,
  paypalProcessor,
  fraudDetector,
  webhookProcessor
};
