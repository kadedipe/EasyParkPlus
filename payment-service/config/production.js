module.exports = {
  // Payment gateway configurations
  stripe: {
    secretKey: process.env.STRIPE_SECRET_KEY,
    publishableKey: process.env.STRIPE_PUBLISHABLE_KEY,
    webhookSecret: process.env.STRIPE_WEBHOOK_SECRET,
    apiVersion: '2023-10-16'
  },
  
  paypal: {
    clientId: process.env.PAYPAL_CLIENT_ID,
    clientSecret: process.env.PAYPAL_CLIENT_SECRET,
    environment: process.env.NODE_ENV === 'production' ? 'live' : 'sandbox',
    webhookId: process.env.PAYPAL_WEBHOOK_ID
  },
  
  // Other payment gateways
  braintree: {
    merchantId: process.env.BRAINTREE_MERCHANT_ID,
    publicKey: process.env.BRAINTREE_PUBLIC_KEY,
    privateKey: process.env.BRAINTREE_PRIVATE_KEY,
    environment: process.env.NODE_ENV === 'production' ? 'production' : 'sandbox'
  },
  
  square: {
    accessToken: process.env.SQUARE_ACCESS_TOKEN,
    locationId: process.env.SQUARE_LOCATION_ID,
    environment: process.env.NODE_ENV === 'production' ? 'production' : 'sandbox'
  },
  
  // Application settings
  app: {
    port: process.env.PORT || 3001,
    environment: process.env.NODE_ENV || 'development',
    logLevel: process.env.LOG_LEVEL || 'info'
  },
  
  // Database configuration
  database: {
    url: process.env.DATABASE_URL || 'postgresql://payment_user:payment_password@postgres-primary:5432/payment_db',
    pool: {
      max: 20,
      min: 5,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 2000
    }
  },
  
  // Redis configuration
  redis: {
    url: process.env.REDIS_URL || 'redis://redis:6379',
    password: process.env.REDIS_PASSWORD,
    tls: process.env.REDIS_TLS === 'true'
  },
  
  // Fraud detection
  fraud: {
    enabled: process.env.FRAUD_DETECTION_ENABLED === 'true',
    maxMind: {
      accountId: process.env.MAXMIND_ACCOUNT_ID,
      licenseKey: process.env.MAXMIND_LICENSE_KEY
    },
    thresholds: {
      highRisk: 70,
      mediumRisk: 30
    }
  },
  
  // Rate limiting
  rateLimit: {
    payment: {
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 100 // 100 requests per window
    },
    refund: {
      windowMs: 60 * 60 * 1000, // 1 hour
      max: 20 // 20 requests per window
    }
  },
  
  // Security
  security: {
    jwtSecret: process.env.JWT_SECRET,
    encryptionKey: process.env.ENCRYPTION_KEY,
    webhookVerification: process.env.WEBHOOK_VERIFICATION === 'true'
  },
  
  // Monitoring
  monitoring: {
    prometheus: {
      enabled: true,
      path: '/metrics'
    },
    sentry: {
      dsn: process.env.SENTRY_DSN,
      environment: process.env.NODE_ENV
    }
  },
  
  // Business rules
  business: {
    minAmount: 0.5, // Minimum payment amount
    maxAmount: 10000, // Maximum payment amount
    supportedCurrencies: ['USD', 'EUR', 'GBP', 'CAD', 'AUD'],
    defaultCurrency: 'USD',
    autoRefundThreshold: 5000, // Auto-review payments above this amount
    settlementFrequency: 'daily' // daily, weekly, monthly
  }
};