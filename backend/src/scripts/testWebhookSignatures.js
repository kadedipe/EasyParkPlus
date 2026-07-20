// parking-management/backend/src/scripts/testWebhookSignatures.js
import { signatureVerifier } from '../webhooks/signatureVerifier.complete.js';

class WebhookSignatureTester {
  constructor() {
    this.testResults = [];
  }

  async runAllTests() {
    console.log('🔐 Testing Webhook Signature Verification...\n');

    // 1. Test Stripe signatures
    await this.testStripeSignatures();

    // 2. Test PayPal signatures
    await this.testPaypalSignatures();

    // 3. Test GitHub signatures
    await this.testGithubSignatures();

    // 4. Test Slack signatures
    await this.testSlackSignatures();

    // 5. Test replay attack prevention
    await this.testReplayAttackPrevention();

    // 6. Test invalid signatures
    await this.testInvalidSignatures();

    // 7. Generate report
    this.generateReport();

    return this.testResults;
  }

  async testStripeSignatures() {
    console.log('📝 Testing Stripe signatures...');
    
    const payload = JSON.stringify({
      id: 'evt_test_123',
      type: 'payment_intent.succeeded',
      data: { object: { id: 'pi_123' } },
    });

    // Generate valid signature
    const valid = signatureVerifier.generateSignature(payload, 'stripe');
    
    // Test valid signature
    const result1 = signatureVerifier.verifySignature(
      'stripe',
      payload,
      valid.signature,
      valid.timestamp
    );

    this.recordResult({
      provider: 'Stripe',
      test: 'Valid Signature',
      passed: result1.valid,
      details: result1,
    });

    // Test tampered payload
    const tamperedPayload = payload.replace('succeeded', 'failed');
    const result2 = signatureVerifier.verifySignature(
      'stripe',
      tamperedPayload,
      valid.signature,
      valid.timestamp
    );

    this.recordResult({
      provider: 'Stripe',
      test: 'Tampered Payload',
      passed: !result2.valid,
      details: result2,
    });

    // Test expired timestamp
    const expiredTimestamp = Math.floor(Date.now() / 1000) - 600;
    const result3 = signatureVerifier.verifySignature(
      'stripe',
      payload,
      valid.signature,
      expiredTimestamp
    );

    this.recordResult({
      provider: 'Stripe',
      test: 'Expired Timestamp',
      passed: !result3.valid,
      details: result3,
    });

    console.log(`  ✅ Stripe tests completed`);
  }

  async testPaypalSignatures() {
    console.log('📝 Testing PayPal signatures...');
    
    const payload = JSON.stringify({
      event_type: 'PAYMENT.CAPTURE.COMPLETED',
      resource: { id: 'pay_123' },
    });

    const headers = {
      'paypal-auth-algo': 'SHA256withRSA',
      'paypal-cert-url': 'https://api.paypal.com/v1/oauth2/cert',
      'paypal-transmission-id': 'trans_123',
      'paypal-transmission-time': new Date().toISOString(),
    };

    // Test with missing headers
    const result1 = signatureVerifier.verifySignature(
      'paypal',
      payload,
      'signature_123',
      null,
      {}
    );

    this.recordResult({
      provider: 'PayPal',
      test: 'Missing Headers',
      passed: !result1.valid,
      details: result1,
    });

    console.log(`  ✅ PayPal tests completed`);
  }

  async testGithubSignatures() {
    console.log('📝 Testing GitHub signatures...');
    
    const payload = JSON.stringify({
      action: 'opened',
      number: 1,
      repository: { name: 'test-repo' },
    });

    // Generate signature
    const signature = signatureVerifier.generateSignature(payload, 'github');
    
    const result = signatureVerifier.verifySignature(
      'github',
      payload,
      signature.signature
    );

    this.recordResult({
      provider: 'GitHub',
      test: 'Valid Signature',
      passed: result.valid,
      details: result,
    });

    console.log(`  ✅ GitHub tests completed`);
  }

  async testSlackSignatures() {
    console.log('📝 Testing Slack signatures...');
    
    const payload = JSON.stringify({
      type: 'url_verification',
      challenge: 'challenge_123',
    });

    const timestamp = Math.floor(Date.now() / 1000);
    const signature = signatureVerifier.generateSignature(payload, 'slack');

    const result = signatureVerifier.verifySignature(
      'slack',
      payload,
      signature.signature,
      timestamp
    );

    this.recordResult({
      provider: 'Slack',
      test: 'Valid Signature',
      passed: result.valid,
      details: result,
    });

    console.log(`  ✅ Slack tests completed`);
  }

  async testReplayAttackPrevention() {
    console.log('📝 Testing replay attack prevention...');
    
    const payload = JSON.stringify({ test: 'replay' });
    const signature = signatureVerifier.generateSignature(payload, 'stripe');

    // First attempt should pass
    const result1 = signatureVerifier.verifySignature(
      'stripe',
      payload,
      signature.signature,
      signature.timestamp
    );

    // Second attempt with same signature should be flagged as replay
    const result2 = signatureVerifier.verifySignature(
      'stripe',
      payload,
      signature.signature,
      signature.timestamp
    );

    this.recordResult({
      provider: 'All',
      test: 'Replay Attack Prevention',
      passed: result1.valid && !result2.valid,
      details: {
        firstAttempt: result1,
        secondAttempt: result2,
      },
    });

    console.log(`  ✅ Replay attack tests completed`);
  }

  async testInvalidSignatures() {
    console.log('📝 Testing invalid signatures...');
    
    const payload = JSON.stringify({ test: 'invalid' });
    const invalidSignatures = [
      'invalid_signature',
      't=123,v1=invalid',
      'wrong_format',
      '',
      null,
    ];

    let passed = 0;
    for (const sig of invalidSignatures) {
      const result = signatureVerifier.verifySignature(
        'stripe',
        payload,
        sig,
        Math.floor(Date.now() / 1000)
      );

      if (!result.valid) passed++;
    }

    this.recordResult({
      provider: 'Stripe',
      test: 'Invalid Signatures',
      passed: passed === invalidSignatures.length,
      details: {
        tested: invalidSignatures.length,
        rejected: passed,
      },
    });

    console.log(`  ✅ Invalid signature tests completed`);
  }

  recordResult(result) {
    this.testResults.push({
      ...result,
      timestamp: new Date().toISOString(),
    });
  }

  generateReport() {
    console.log('\n📊 Webhook Signature Test Report:');
    console.log('═'.repeat(50));
    
    const passed = this.testResults.filter(r => r.passed).length;
    const total = this.testResults.length;
    
    console.log(`✅ Passed: ${passed}/${total}`);
    console.log(`❌ Failed: ${total - passed}/${total}`);
    console.log(`📈 Success Rate: ${(passed / total * 100).toFixed(2)}%`);
    console.log('═'.repeat(50));

    // List failures
    const failures = this.testResults.filter(r => !r.passed);
    if (failures.length > 0) {
      console.log('\n❌ Failed Tests:');
      failures.forEach(f => {
        console.log(`  - ${f.provider}: ${f.test}`);
      });
    }

    console.log('\n💡 Recommendations:');
    if (passed === total) {
      console.log('  ✅ All signature verifications are working correctly!');
    } else {
      console.log('  - Review signature configuration for failed providers');
      console.log('  - Ensure webhook secrets are correctly configured');
      console.log('  - Check timestamp tolerance settings');
    }
  }
}

// Run tests
const tester = new WebhookSignatureTester();
tester.runAllTests().catch(console.error);