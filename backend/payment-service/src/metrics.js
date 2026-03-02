const prometheus = require('prom-client');
const responseTime = require('response-time');

// Create a Registry which registers the metrics
const register = new prometheus.Registry();

// Add default metrics
prometheus.collectDefaultMetrics({ register });

// Custom metrics for Payment Service
const metrics = {
  // Transaction metrics
  transactionsTotal: new prometheus.Counter({
    name: 'payment_service_transactions_total',
    help: 'Total number of payment transactions',
    labelNames: ['gateway', 'payment_method', 'status', 'currency', 'amount_range'],
    registers: [register]
  }),

  transactionDurationSeconds: new prometheus.Histogram({
    name: 'payment_service_transaction_duration_seconds',
    help: 'Payment transaction processing duration in seconds',
    labelNames: ['gateway', 'payment_method', 'status'],
    buckets: [0.1, 0.5, 1, 2, 5, 10],
    registers: [register]
  }),

  // Revenue metrics
  revenueTotal: new prometheus.Counter({
    name: 'payment_service_revenue_total',
    help: 'Total revenue processed',
    labelNames: ['gateway', 'currency', 'payment_method'],
    registers: [register]
  }),

  // Gateway metrics
  gatewayCallsTotal: new prometheus.Counter({
    name: 'payment_service_gateway_calls_total',
    help: 'Total number of payment gateway API calls',
    labelNames: ['gateway', 'endpoint', 'status'],
    registers: [register]
  }),

  gatewayResponseTimeSeconds: new prometheus.Histogram({
    name: 'payment_service_gateway_response_time_seconds',
    help: 'Payment gateway API response time in seconds',
    labelNames: ['gateway', 'endpoint'],
    buckets: [0.01, 0.05, 0.1, 0.5, 1, 2],
    registers: [register]
  }),

  gatewayErrorsTotal: new prometheus.Counter({
    name: 'payment_service_gateway_errors_total',
    help: 'Total number of payment gateway errors',
    labelNames: ['gateway', 'error_type'],
    registers: [register]
  }),

  // Refund and chargeback metrics
  refundsTotal: new prometheus.Counter({
    name: 'payment_service_refunds_total',
    help: 'Total number of refunds processed',
    labelNames: ['gateway', 'reason', 'currency'],
    registers: [register]
  }),

  chargebacksTotal: new prometheus.Counter({
    name: 'payment_service_chargebacks_total',
    help: 'Total number of chargebacks',
    labelNames: ['gateway', 'reason'],
    registers: [register]
  }),

  // Error metrics
  transactionErrorsTotal: new prometheus.Counter({
    name: 'payment_service_transaction_errors_total',
    help: 'Total number of transaction errors',
    labelNames: ['error_type', 'gateway', 'payment_method'],
    registers: [register]
  }),

  // System metrics
  queueSize: new prometheus.Gauge({
    name: 'payment_service_queue_size',
    help: 'Current size of payment processing queue',
    registers: [register]
  }),

  activeWorkers: new prometheus.Gauge({
    name: 'payment_service_active_workers',
    help: 'Number of active payment processing workers',
    registers: [register]
  }),

  // Webhook metrics
  webhooksReceivedTotal: new prometheus.Counter({
    name: 'payment_service_webhooks_received_total',
    help: 'Total number of webhooks received',
    labelNames: ['gateway', 'type'],
    registers: [register]
  }),

  webhooksProcessedTotal: new prometheus.Counter({
    name: 'payment_service_webhooks_processed_total',
    help: 'Total number of webhooks processed',
    labelNames: ['gateway', 'type', 'status'],
    registers: [register]
  }),

  // Fraud detection metrics
  fraudChecksTotal: new prometheus.Counter({
    name: 'payment_service_fraud_checks_total',
    help: 'Total number of fraud checks performed',
    labelNames: ['check_type', 'result'],
    registers: [register]
  }),

  // Tokenization metrics
  tokensCreatedTotal: new prometheus.Counter({
    name: 'payment_service_tokens_created_total',
    help: 'Total number of payment tokens created',
    labelNames: ['gateway', 'token_type'],
    registers: [register]
  }),

  // Settlement metrics
  settlementsTotal: new prometheus.Counter({
    name: 'payment_service_settlements_total',
    help: 'Total number of settlements processed',
    labelNames: ['gateway', 'status'],
    registers: [register]
  }),

  settlementAmount: new prometheus.Gauge({
    name: 'payment_service_settlement_amount',
    help: 'Amount settled by gateway',
    labelNames: ['gateway', 'currency'],
    registers: [register]
  }),

  // Reconciliation metrics
  reconciliationErrorsTotal: new prometheus.Counter({
    name: 'payment_service_reconciliation_errors_total',
    help: 'Total number of reconciliation errors',
    labelNames: ['gateway', 'error_type'],
    registers: [register]
  })
};

// Helper function to categorize amount into ranges
function getAmountRange(amount) {
  if (amount < 10) return '0-10';
  if (amount < 50) return '10-50';
  if (amount < 100) return '50-100';
  if (amount < 500) return '100-500';
  if (amount < 1000) return '500-1000';
  return '1000+';
}

// Metrics middleware for Express
function metricsMiddleware() {
  return responseTime((req, res, time) => {
    const endpoint = req.originalUrl || req.url;
    const method = req.method;
    const status = res.statusCode;

    // Increment gateway call counter for payment endpoints
    if (endpoint.includes('/api/v1/payments')) {
      const gateway = req.headers['x-payment-gateway'] || 'unknown';
      metrics.gatewayCallsTotal.inc({ gateway, endpoint, status });
      metrics.gatewayResponseTimeSeconds.observe({ gateway, endpoint }, time / 1000);
    }
  });
}

// Payment processor wrapper with metrics
function createPaymentProcessorWrapper(gatewayName, processor) {
  return {
    charge: async (paymentData) => {
      const start = Date.now();
      const { amount, currency, paymentMethod } = paymentData;
      const amountRange = getAmountRange(amount);

      try {
        // Process payment
        const result = await processor.charge(paymentData);
        const duration = Date.now() - start;

        // Record successful transaction
        metrics.transactionsTotal.inc({
          gateway: gatewayName,
          payment_method: paymentMethod,
          status: 'success',
          currency,
          amount_range: amountRange
        });

        metrics.transactionDurationSeconds.observe(
          { gateway: gatewayName, payment_method: paymentMethod, status: 'success' },
          duration / 1000
        );

        metrics.revenueTotal.inc({
          gateway: gatewayName,
          currency,
          payment_method: paymentMethod
        }, amount);

        return result;
      } catch (error) {
        const duration = Date.now() - start;
        const errorType = error.code || error.type || 'unknown';

        // Record failed transaction
        metrics.transactionsTotal.inc({
          gateway: gatewayName,
          payment_method: paymentMethod,
          status: 'failed',
          currency,
          amount_range: amountRange
        });

        metrics.transactionDurationSeconds.observe(
          { gateway: gatewayName, payment_method: paymentMethod, status: 'failed' },
          duration / 1000
        );

        metrics.transactionErrorsTotal.inc({
          error_type: errorType,
          gateway: gatewayName,
          payment_method: paymentMethod
        });

        metrics.gatewayErrorsTotal.inc({
          gateway: gatewayName,
          error_type: errorType
        });

        throw error;
      }
    },

    refund: async (transactionId, amount, reason) => {
      const start = Date.now();

      try {
        const result = await processor.refund(transactionId, amount, reason);
        const duration = Date.now() - start;

        metrics.refundsTotal.inc({
          gateway: gatewayName,
          reason: reason || 'customer_request',
          currency: 'USD' // Should be dynamic
        });

        return result;
      } catch (error) {
        metrics.gatewayErrorsTotal.inc({
          gateway: gatewayName,
          error_type: 'refund_failed'
        });
        throw error;
      }
    },

    createToken: async (paymentData) => {
      const start = Date.now();

      try {
        const token = await processor.createToken(paymentData);
        const duration = Date.now() - start;

        metrics.tokensCreatedTotal.inc({
          gateway: gatewayName,
          token_type: paymentData.type || 'card'
        });

        return token;
      } catch (error) {
        metrics.gatewayErrorsTotal.inc({
          gateway: gatewayName,
          error_type: 'tokenization_failed'
        });
        throw error;
      }
    }
  };
}

// Fraud detection wrapper
function createFraudDetectionWrapper(detector) {
  return {
    check: async (transactionData) => {
      const start = Date.now();

      try {
        const result = await detector.check(transactionData);
        const duration = Date.now() - start;

        metrics.fraudChecksTotal.inc({
          check_type: detector.type || 'basic',
          result: result.riskLevel || 'low'
        });

        return result;
      } catch (error) {
        metrics.fraudChecksTotal.inc({
          check_type: detector.type || 'basic',
          result: 'error'
        });
        throw error;
      }
    }
  };
}

// Settlement processor wrapper
function createSettlementProcessorWrapper(processor) {
  return {
    processSettlement: async (gateway, date) => {
      const start = Date.now();

      try {
        const settlement = await processor.processSettlement(gateway, date);
        const duration = Date.now() - start;

        metrics.settlementsTotal.inc({
          gateway,
          status: 'completed'
        });

        metrics.settlementAmount.set(
          { gateway, currency: settlement.currency },
          settlement.amount
        );

        return settlement;
      } catch (error) {
        metrics.settlementsTotal.inc({
          gateway,
          status: 'failed'
        });

        metrics.reconciliationErrorsTotal.inc({
          gateway,
          error_type: 'settlement_failed'
        });

        throw error;
      }
    }
  };
}

// Webhook processor wrapper
function createWebhookProcessorWrapper(processor) {
  return {
    process: async (gateway, type, payload) => {
      const start = Date.now();

      metrics.webhooksReceivedTotal.inc({ gateway, type });

      try {
        const result = await processor.process(gateway, type, payload);
        const duration = Date.now() - start;

        metrics.webhooksProcessedTotal.inc({
          gateway,
          type,
          status: 'success'
        });

        return result;
      } catch (error) {
        metrics.webhooksProcessedTotal.inc({
          gateway,
          type,
          status: 'failed'
        });

        metrics.gatewayErrorsTotal.inc({
          gateway,
          error_type: 'webhook_processing_failed'
        });

        throw error;
      }
    }
  };
}

// Function to get metrics as string
async function getMetrics() {
  return await register.metrics();
}

// Function to reset metrics (for testing)
function resetMetrics() {
  register.resetMetrics();
}

// Function to update queue metrics
function updateQueueMetrics(queue) {
  metrics.queueSize.set(queue.size());
  metrics.activeWorkers.set(queue.activeCount());
}

module.exports = {
  metrics,
  metricsMiddleware,
  createPaymentProcessorWrapper,
  createFraudDetectionWrapper,
  createSettlementProcessorWrapper,
  createWebhookProcessorWrapper,
  updateQueueMetrics,
  getMetrics,
  resetMetrics,
  register
};
