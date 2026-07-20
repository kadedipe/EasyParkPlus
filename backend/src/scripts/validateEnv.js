// parking-management/backend/src/scripts/validateEnv.js

class EnvironmentValidator {
  constructor() {
    this.requiredVars = {
      // App Configuration
      NODE_ENV: { required: true, values: ['development', 'staging', 'production'] },
      PORT: { required: true, default: 5000 },
      
      // Database
      DATABASE_URL: { required: true, pattern: /^postgresql:\/\/.+/ },
      DATABASE_REPLICA_URL_1: { required: false, pattern: /^postgresql:\/\/.+/ },
      DATABASE_REPLICA_URL_2: { required: false, pattern: /^postgresql:\/\/.+/ },
      DB_POOL_SIZE: { required: false, default: 20 },
      DB_CONNECTION_TIMEOUT: { required: false, default: 30000 },
      
      // Redis
      REDIS_URL: { required: true, pattern: /^redis:\/\/.+/ },
      REDIS_PASSWORD: { required: false },
      REDIS_MAX_MEMORY: { required: false, default: 1024 },
      
      // JWT
      JWT_SECRET: { required: true, minLength: 32 },
      JWT_EXPIRY: { required: false, default: '7d' },
      JWT_REFRESH_SECRET: { required: true, minLength: 32 },
      JWT_REFRESH_EXPIRY: { required: false, default: '30d' },
      
      // Stripe
      STRIPE_SECRET_KEY: { required: true, pattern: /^sk_(live|test)_.+/ },
      STRIPE_PUBLISHABLE_KEY: { required: true, pattern: /^pk_(live|test)_.+/ },
      STRIPE_WEBHOOK_SECRET: { required: true, pattern: /^WEBHOOK_SECRET_PATTERN/ },
      
      // Payment Recovery
      PAYMENT_RECOVERY_MAX_RETRIES: { required: false, default: 3 },
      PAYMENT_RECOVERY_RETRY_DELAYS: { required: false, default: '60,300,900' },
      
      // Rate Limiting
      RATE_LIMIT_WINDOW_MS: { required: false, default: 60000 },
      RATE_LIMIT_MAX_REQUESTS: { required: false, default: 100 },
      
      // Monitoring
      SENTRY_DSN: { required: false, pattern: /^https:\/\/.+/ },
      LOG_LEVEL: { required: false, values: ['error', 'warn', 'info', 'debug'] },
      
      // CORS
      CORS_ORIGIN: { required: true, pattern: /^https?:\/\/.+/ },
      
      // Email
      SMTP_HOST: { required: false },
      SMTP_PORT: { required: false, default: 587 },
      SMTP_USER: { required: false },
      SMTP_PASS: { required: false },
      
      // AWS
      AWS_ACCESS_KEY_ID: { required: false },
      AWS_SECRET_ACCESS_KEY: { required: false },
      AWS_REGION: { required: false, default: 'us-east-1' },
      AWS_S3_BACKUP_BUCKET: { required: false },
      
      // Backup
      BACKUP_DIR: { required: false, default: './backups' },
      BACKUP_RETENTION_DAYS: { required: false, default: 30 },
      
      // Security
      HTTPS_ENABLED: { required: false, default: true },
      CSP_ENABLED: { required: false, default: true },
      RATE_LIMIT_ENABLED: { required: false, default: true },
      
      // Feature Flags
      ENABLE_EV_CHARGING: { required: false, default: true },
      ENABLE_PAYMENTS: { required: false, default: true },
      ENABLE_NOTIFICATIONS: { required: false, default: true },
      ENABLE_ANALYTICS: { required: false, default: false },
      ENABLE_ERROR_TRACKING: { required: false, default: false },
    };
    
    this.warnings = [];
    this.errors = [];
    this.missingVars = [];
    this.invalidVars = [];
  }

  validate() {
    console.log('🔍 Validating Environment Variables...\n');

    for (const [key, config] of Object.entries(this.requiredVars)) {
      const value = process.env[key];
      
      if (config.required && !value) {
        this.missingVars.push(key);
        this.errors.push(`❌ Required variable: ${key} is missing`);
        continue;
      }

      if (!value && config.default !== undefined) {
        // Use default if available
        process.env[key] = String(config.default);
        this.warnings.push(`⚠️ Using default for ${key}: ${config.default}`);
        continue;
      }

      if (value) {
        // Validate value
        if (config.values && !config.values.includes(value)) {
          this.invalidVars.push(key);
          this.errors.push(`❌ Invalid value for ${key}: ${value}. Expected: ${config.values.join(', ')}`);
        }

        if (config.pattern && !config.pattern.test(value)) {
          this.invalidVars.push(key);
          this.errors.push(`❌ Invalid format for ${key}: ${value}. Expected pattern: ${config.pattern}`);
        }

        if (config.minLength && value.length < config.minLength) {
          this.invalidVars.push(key);
          this.errors.push(`❌ ${key} is too short. Minimum length: ${config.minLength}`);
        }
      }
    }

    // Special validations
    this.validateDatabaseConnection();
    this.validateRedisConnection();
    this.validateEnvironment();
    this.validateSecurity();

    // Generate report
    this.generateReport();

    return {
      valid: this.errors.length === 0,
      warnings: this.warnings,
      errors: this.errors,
      missingVars: this.missingVars,
      invalidVars: this.invalidVars,
    };
  }

  validateDatabaseConnection() {
    try {
      const url = process.env.DATABASE_URL;
      if (url) {
        // Validate database URL format
        const parsed = new URL(url);
        if (!parsed.hostname || !parsed.pathname || !parsed.protocol) {
          this.errors.push('❌ Invalid DATABASE_URL format');
        }
      }
    } catch (error) {
      this.errors.push(`❌ Invalid DATABASE_URL: ${error.message}`);
    }
  }

  validateRedisConnection() {
    try {
      const url = process.env.REDIS_URL;
      if (url) {
        // Validate Redis URL format
        const parsed = new URL(url);
        if (!parsed.hostname || !parsed.protocol) {
          this.errors.push('❌ Invalid REDIS_URL format');
        }
      }
    } catch (error) {
      this.errors.push(`❌ Invalid REDIS_URL: ${error.message}`);
    }
  }

  validateEnvironment() {
    const env = process.env.NODE_ENV;
    if (!['development', 'staging', 'production'].includes(env)) {
      this.warnings.push(`⚠️ NODE_ENV is set to '${env}'. Expected: development, staging, or production`);
    }

    if (env === 'production') {
      // Production-specific validations
      if (process.env.JWT_SECRET === 'your-secret-key') {
        this.errors.push('❌ JWT_SECRET is using default value in production');
      }
      
      if (process.env.STRIPE_SECRET_KEY?.includes('test')) {
        this.errors.push('❌ STRIPE_SECRET_KEY is using test key in production');
      }
      
      if (process.env.NODE_ENV && !process.env.DATABASE_URL?.includes('production')) {
        this.warnings.push('⚠️ NODE_ENV is production but DATABASE_URL does not contain production');
      }
    }
  }

  validateSecurity() {
    const corsOrigin = process.env.CORS_ORIGIN;
    if (corsOrigin === '*' && process.env.NODE_ENV === 'production') {
      this.errors.push('❌ CORS_ORIGIN is set to "*" in production. This is insecure!');
    }

    // Check for sensitive data in env
    const sensitiveKeys = ['PASSWORD', 'SECRET', 'KEY', 'TOKEN', 'CREDENTIAL'];
    for (const key of Object.keys(process.env)) {
      if (sensitiveKeys.some(k => key.includes(k))) {
        const value = process.env[key];
        if (value && value.length < 8) {
          this.warnings.push(`⚠️ ${key} seems too short (${value.length} chars). Consider using longer values.`);
        }
      }
    }
  }

  generateReport() {
    console.log('\n📊 Environment Variables Validation Report:');
    console.log('═'.repeat(60));
    
    console.log(`\n📋 Total Variables Checked: ${Object.keys(this.requiredVars).length}`);
    console.log(`✅ Valid: ${Object.keys(this.requiredVars).length - this.missingVars.length - this.invalidVars.length}`);
    console.log(`❌ Missing: ${this.missingVars.length}`);
    console.log(`❌ Invalid: ${this.invalidVars.length}`);
    console.log(`⚠️ Warnings: ${this.warnings.length}`);

    if (this.missingVars.length > 0) {
      console.log('\n❌ Missing Required Variables:');
      this.missingVars.forEach(v => {
        console.log(`  - ${v}`);
      });
    }

    if (this.invalidVars.length > 0) {
      console.log('\n❌ Invalid Variables:');
      this.invalidVars.forEach(v => {
        console.log(`  - ${v}`);
      });
    }

    if (this.warnings.length > 0) {
      console.log('\n⚠️ Warnings:');
      this.warnings.forEach(w => {
        console.log(`  - ${w}`);
      });
    }

    // Print sample .env file
    console.log('\n📝 Sample .env file for reference:');
    console.log('═'.repeat(60));
    console.log('# Environment Configuration');
    console.log('NODE_ENV=production');
    console.log('PORT=5000');
    console.log('');
    console.log('# Database');
    console.log('DATABASE_URL=postgresql://user:password@localhost:5432/parking_db');
    console.log('');
    console.log('# Redis');
    console.log('REDIS_URL=redis://localhost:6379');
    console.log('');
    console.log('# JWT');
    console.log('JWT_SECRET=your-super-secret-jwt-key-min-32-chars');
    console.log('JWT_REFRESH_SECRET=your-super-secret-refresh-key-min-32-chars');
    console.log('');
    console.log('# Stripe');
    console.log('STRIPE_SECRET_KEY=<your_stripe_secret_key>');
    console.log('STRIPE_PUBLISHABLE_KEY=<your_stripe_publishable_key>');
    console.log('STRIPE_WEBHOOK_SECRET=<your_stripe_webhook_secret>');
    console.log('');
    console.log('# Security');
    console.log('CORS_ORIGIN=https://yourdomain.com');
    console.log('HTTPS_ENABLED=true');
    console.log('CSP_ENABLED=true');

    console.log('\n💡 Recommendations:');
    if (this.errors.length === 0 && this.warnings.length === 0) {
      console.log('  ✅ All environment variables are correctly configured!');
    } else if (this.errors.length === 0) {
      console.log('  ✅ No critical issues found.');
      console.log('  ⚠️ Please review warnings for best practices.');
    } else {
      console.log('  ❌ Critical issues found. Please fix before deployment.');
      console.log('  - Review missing and invalid variables');
      console.log('  - Ensure all required secrets are set');
      console.log('  - Verify production values are not using defaults');
    }
  }
}

// Run validation
const validator = new EnvironmentValidator();
const result = validator.validate();

// Exit with appropriate code
process.exit(result.valid ? 0 : 1);