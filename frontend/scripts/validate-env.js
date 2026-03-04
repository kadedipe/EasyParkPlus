#!/usr/bin/env node

/**
 * Environment Variables Validation Script
 * 
 * This script validates that all required environment variables are set
 * and displays warnings for missing optional variables.
 */

const REQUIRED_VARS = [
  'VITE_API_URL',
  'VITE_GOOGLE_MAPS_API_KEY',
  'VITE_STRIPE_PUBLIC_KEY',
];

const OPTIONAL_VARS = [
  'VITE_WS_URL',
  'VITE_FIREBASE_API_KEY',
  'VITE_FIREBASE_PROJECT_ID',
  'VITE_SENTRY_DSN',
  'VITE_GA_TRACKING_ID',
  'VITE_PAYPAL_CLIENT_ID',
  'VITE_MAPBOX_TOKEN',
  'VITE_ALGOLIA_APP_ID',
  'VITE_RECAPTCHA_SITE_KEY',
  'VITE_INTERCOM_APP_ID',
  'VITE_MIXPANEL_TOKEN',
  'VITE_LOGROCKET_APP_ID',
  'VITE_HOTJAR_ID',
];

const validateEnv = () => {
  console.log('\n🔍 Validating environment variables...\n');
  
  let hasError = false;
  const missingRequired = [];
  const missingOptional = [];

  // Check required variables
  REQUIRED_VARS.forEach(varName => {
    if (!process.env[varName]) {
      missingRequired.push(varName);
      hasError = true;
    }
  });

  // Check optional variables (just warnings)
  OPTIONAL_VARS.forEach(varName => {
    if (!process.env[varName]) {
      missingOptional.push(varName);
    }
  });

  // Display results
  if (missingRequired.length > 0) {
    console.error('❌ Missing required environment variables:');
    missingRequired.forEach(varName => {
      console.error(`   - ${varName}`);
    });
    console.log('');
  }

  if (missingOptional.length > 0) {
    console.warn('⚠️  Missing optional environment variables:');
    missingOptional.forEach(varName => {
      console.warn(`   - ${varName}`);
    });
    console.log('');
  }

  if (!hasError) {
    console.log('✅ All required environment variables are set!\n');
  }

  // Validate specific formats
  validateFormats();

  return !hasError;
};

const validateFormats = () => {
  // Validate API URL format
  if (process.env.VITE_API_URL) {
    try {
      new URL(process.env.VITE_API_URL);
    } catch {
      console.warn('⚠️  VITE_API_URL has invalid URL format');
    }
  }

  // Validate Google Maps API key format (starts with AIza)
  if (process.env.VITE_GOOGLE_MAPS_API_KEY && 
      !process.env.VITE_GOOGLE_MAPS_API_KEY.startsWith('AIza') &&
      process.env.VITE_APP_ENV === 'production') {
    console.warn('⚠️  VITE_GOOGLE_MAPS_API_KEY may be invalid (should start with AIza)');
  }

  // Validate Stripe key format
  if (process.env.VITE_STRIPE_PUBLIC_KEY) {
    const isTest = process.env.VITE_STRIPE_PUBLIC_KEY.startsWith('pk_test_');
    const isLive = process.env.VITE_STRIPE_PUBLIC_KEY.startsWith('pk_live_');
    
    if (!isTest && !isLive) {
      console.warn('⚠️  VITE_STRIPE_PUBLIC_KEY has invalid format');
    }
    
    if (process.env.VITE_APP_ENV === 'production' && isTest) {
      console.error('❌ Using Stripe TEST key in production!');
    }
    
    if (process.env.VITE_APP_ENV === 'development' && isLive) {
      console.warn('⚠️  Using Stripe LIVE key in development!');
    }
  }
};

// Run validation if called directly
if (require.main === module) {
  const isValid = validateEnv();
  process.exit(isValid ? 0 : 1);
}

module.exports = { validateEnv };