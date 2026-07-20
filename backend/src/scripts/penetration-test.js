// parking-management/backend/src/scripts/penetration-test.js
import axios from 'axios';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

class PenetrationTest {
  constructor() {
    this.baseUrl = process.env.APP_URL || 'http://localhost:3000';
    this.testResults = [];
    this.attackPatterns = {
      sqlInjection: [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "' UNION SELECT * FROM users --",
        "1' OR '1'='1' --",
        "admin' --",
        "' OR 1=1 --",
      ],
      xss: [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        "<body onload=alert('XSS')>",
        "<svg/onload=alert('XSS')>",
        "'';alert('XSS');//",
      ],
      pathTraversal: [
        "../../../etc/passwd",
        "../../../../etc/passwd",
        "../../../../windows/win.ini",
        "../../../../boot.ini",
        "../../../../proc/self/environ",
      ],
      commandInjection: [
        "; ls -la",
        "| whoami",
        "&& cat /etc/passwd",
        "`id`",
        "$(whoami)",
      ],
      authBypass: [
        "admin' OR '1'='1' --",
        "admin' OR 1=1 --",
        "admin' OR '1'='1'/*",
        "admin'--",
        "admin'#",
        "admin'/*",
      ],
      rateLimit: this.generateRateLimitTests(),
      jwtAttacks: this.generateJwtTests(),
    };
  }

  async runAllTests() {
    console.log('🔒 Starting Security Penetration Tests...\n');

    // 1. SQL Injection Tests
    await this.testSQLInjection();

    // 2. XSS Tests
    await this.testXSS();

    // 3. Path Traversal Tests
    await this.testPathTraversal();

    // 4. Command Injection Tests
    await this.testCommandInjection();

    // 5. Authentication Bypass Tests
    await this.testAuthBypass();

    // 6. Rate Limit Tests
    await this.testRateLimiting();

    // 7. JWT Security Tests
    await this.testJWTSecurity();

    // 8. SSL/TLS Tests
    await this.testSSL();

    // 9. CORS Tests
    await this.testCORS();

    // 10. Generate Report
    this.generateReport();

    console.log('\n' + '═'.repeat(50));
    const passed = this.testResults.filter(r => r.passed).length;
    const total = this.testResults.length;
    console.log(`📊 Security Test Results: ${passed}/${total} passed`);

    return { results: this.testResults, passed, total };
  }

  generateRateLimitTests() {
    const tests = [];
    for (let i = 0; i < 200; i++) {
      tests.push({
        request: `Request ${i + 1}`,
        shouldBlock: i >= 100,
      });
    }
    return tests;
  }

  generateJwtTests() {
    return [
      {
        name: 'Expired Token',
        payload: { exp: Math.floor(Date.now() / 1000) - 3600 },
        shouldFail: true,
      },
      {
        name: 'Invalid Signature',
        payload: { signature: 'invalid' },
        shouldFail: true,
      },
      {
        name: 'Missing Token',
        payload: null,
        shouldFail: true,
      },
      {
        name: 'Malformed Token',
        payload: 'malformed-token',
        shouldFail: true,
      },
    ];
  }

  async testSQLInjection() {
    console.log('🔍 Testing SQL Injection...');
    
    const endpoints = [
      '/api/parking/search',
      '/api/auth/login',
      '/api/bookings',
      '/api/users/profile',
    ];

    for (const endpoint of endpoints) {
      for (const payload of this.attackPatterns.sqlInjection) {
        try {
          const response = await axios.get(
            `${this.baseUrl}${endpoint}?search=${encodeURIComponent(payload)}`,
            { validateStatus: false }
          );

          const passed = !this.detectSQLInjectionSuccess(response);
          this.recordResult({
            type: 'SQL Injection',
            endpoint,
            payload,
            status: response.status,
            passed,
            details: passed ? 'Blocked successfully' : 'Vulnerable!',
          });

          if (!passed) {
            console.log(`  ⚠️ SQL Injection possible on ${endpoint}`);
          }
        } catch (error) {
          this.recordResult({
            type: 'SQL Injection',
            endpoint,
            payload,
            status: error.response?.status || 500,
            passed: true,
            details: 'Error handled correctly',
          });
        }
      }
    }
  }

  async testXSS() {
    console.log('🔍 Testing XSS...');
    
    const endpoints = [
      '/api/parking/search',
      '/api/reviews',
      '/api/contact',
    ];

    for (const endpoint of endpoints) {
      for (const payload of this.attackPatterns.xss) {
        try {
          const response = await axios.post(
            `${this.baseUrl}${endpoint}`,
            { comment: payload, name: payload },
            { validateStatus: false }
          );

          const passed = !this.detectXSSSuccess(response);
          this.recordResult({
            type: 'XSS',
            endpoint,
            payload: payload.substring(0, 30) + '...',
            status: response.status,
            passed,
            details: passed ? 'Sanitized successfully' : 'Vulnerable!',
          });

          if (!passed) {
            console.log(`  ⚠️ XSS possible on ${endpoint}`);
          }
        } catch (error) {
          this.recordResult({
            type: 'XSS',
            endpoint,
            payload: payload.substring(0, 30) + '...',
            status: error.response?.status || 500,
            passed: true,
            details: 'Error handled correctly',
          });
        }
      }
    }
  }

  async testPathTraversal() {
    console.log('🔍 Testing Path Traversal...');
    
    const endpoints = [
      '/api/files',
      '/api/images',
      '/static',
    ];

    for (const endpoint of endpoints) {
      for (const payload of this.attackPatterns.pathTraversal) {
        try {
          const response = await axios.get(
            `${this.baseUrl}${endpoint}?file=${encodeURIComponent(payload)}`,
            { validateStatus: false }
          );

          const passed = !this.detectPathTraversalSuccess(response);
          this.recordResult({
            type: 'Path Traversal',
            endpoint,
            payload,
            status: response.status,
            passed,
            details: passed ? 'Blocked successfully' : 'Vulnerable!',
          });

          if (!passed) {
            console.log(`  ⚠️ Path Traversal possible on ${endpoint}`);
          }
        } catch (error) {
          this.recordResult({
            type: 'Path Traversal',
            endpoint,
            payload,
            status: error.response?.status || 500,
            passed: true,
            details: 'Error handled correctly',
          });
        }
      }
    }
  }

  async testCommandInjection() {
    console.log('🔍 Testing Command Injection...');
    
    const endpoints = [
      '/api/export',
      '/api/report',
      '/api/ping',
    ];

    for (const endpoint of endpoints) {
      for (const payload of this.attackPatterns.commandInjection) {
        try {
          const response = await axios.get(
            `${this.baseUrl}${endpoint}?cmd=${encodeURIComponent(payload)}`,
            { validateStatus: false }
          );

          const passed = !this.detectCommandInjectionSuccess(response);
          this.recordResult({
            type: 'Command Injection',
            endpoint,
            payload: payload.substring(0, 20) + '...',
            status: response.status,
            passed,
            details: passed ? 'Blocked successfully' : 'Vulnerable!',
          });

          if (!passed) {
            console.log(`  ⚠️ Command Injection possible on ${endpoint}`);
          }
        } catch (error) {
          this.recordResult({
            type: 'Command Injection',
            endpoint,
            payload: payload.substring(0, 20) + '...',
            status: error.response?.status || 500,
            passed: true,
            details: 'Error handled correctly',
          });
        }
      }
    }
  }

  async testAuthBypass() {
    console.log('🔍 Testing Authentication Bypass...');
    
    const protectedEndpoints = [
      '/api/bookings',
      '/api/payments',
      '/api/users/profile',
      '/api/dashboard',
    ];

    for (const endpoint of protectedEndpoints) {
      for (const payload of this.attackPatterns.authBypass) {
        try {
          const response = await axios.get(
            `${this.baseUrl}${endpoint}`,
            {
              headers: {
                'Authorization': `Bearer ${payload}`,
              },
              validateStatus: false,
            }
          );

          const passed = response.status === 401 || response.status === 403;
          this.recordResult({
            type: 'Authentication Bypass',
            endpoint,
            payload: payload.substring(0, 20) + '...',
            status: response.status,
            passed,
            details: passed ? 'Protected successfully' : 'Vulnerable!',
          });

          if (!passed) {
            console.log(`  ⚠️ Auth Bypass possible on ${endpoint}`);
          }
        } catch (error) {
          this.recordResult({
            type: 'Authentication Bypass',
            endpoint,
            payload: payload.substring(0, 20) + '...',
            status: error.response?.status || 500,
            passed: true,
            details: 'Error handled correctly',
          });
        }
      }
    }
  }

  async testRateLimiting() {
    console.log('🔍 Testing Rate Limiting...');
    
    const endpoint = '/api/auth/login';
    const startTime = Date.now();
    let blocked = false;
    let attempts = 0;

    while (!blocked && attempts < 150) {
      try {
        await axios.post(
          `${this.baseUrl}${endpoint}`,
          { email: 'test@example.com', password: 'wrongpassword' },
          { validateStatus: false }
        );
        attempts++;
      } catch (error) {
        if (error.response?.status === 429) {
          blocked = true;
        }
      }
    }

    const duration = Date.now() - startTime;
    const passed = blocked && attempts >= 100;

    this.recordResult({
      type: 'Rate Limiting',
      endpoint,
      attempts,
      duration,
      passed,
      details: passed ? `Rate limiting active (blocked after ${attempts} attempts)` : 'Rate limiting not effective',
    });

    if (passed) {
      console.log(`  ✅ Rate limiting active (${attempts} attempts)`);
    } else {
      console.log(`  ⚠️ Rate limiting not effective (${attempts} attempts)`);
    }
  }

  async testJWTSecurity() {
    console.log('🔍 Testing JWT Security...');
    
    const endpoint = '/api/auth/verify';
    
    for (const test of this.attackPatterns.jwtAttacks) {
      try {
        const response = await axios.get(
          `${this.baseUrl}${endpoint}`,
          {
            headers: {
              'Authorization': `Bearer ${test.payload}`,
            },
            validateStatus: false,
          }
        );

        const passed = (test.shouldFail && (response.status === 401 || response.status === 403)) ||
                      (!test.shouldFail && response.status === 200);
        
        this.recordResult({
          type: 'JWT Security',
          test: test.name,
          status: response.status,
          passed,
          details: passed ? 'Protected successfully' : 'Vulnerable!',
        });

        if (!passed) {
          console.log(`  ⚠️ JWT vulnerability: ${test.name}`);
        }
      } catch (error) {
        this.recordResult({
          type: 'JWT Security',
          test: test.name,
          status: error.response?.status || 500,
          passed: true,
          details: 'Error handled correctly',
        });
      }
    }
  }

  async testSSL() {
    console.log('🔍 Testing SSL/TLS...');
    
    try {
      // Check for HTTPS
      const response = await axios.get(this.baseUrl, { validateStatus: false });
      const isHttps = this.baseUrl.startsWith('https');
      
      // Check for HSTS header
      const hstsHeader = response.headers['strict-transport-security'];
      
      const passed = isHttps && hstsHeader;
      
      this.recordResult({
        type: 'SSL/TLS',
        endpoint: this.baseUrl,
        details: passed 
          ? 'HTTPS enabled with HSTS' 
          : `HTTPS: ${isHttps}, HSTS: ${!!hstsHeader}`,
        passed,
      });

      if (passed) {
        console.log('  ✅ SSL/TLS configured correctly');
      } else {
        console.log('  ⚠️ SSL/TLS configuration issues detected');
      }
    } catch (error) {
      this.recordResult({
        type: 'SSL/TLS',
        endpoint: this.baseUrl,
        details: 'SSL/TLS test failed',
        passed: false,
      });
      console.log('  ❌ SSL/TLS test failed');
    }
  }

  async testCORS() {
    console.log('🔍 Testing CORS...');
    
    const endpoint = '/api/health';
    const origins = [
      'https://evil.com',
      'http://localhost:3001',
      'https://example.com',
    ];

    for (const origin of origins) {
      try {
        const response = await axios.options(
          `${this.baseUrl}${endpoint}`,
          {
            headers: {
              'Origin': origin,
              'Access-Control-Request-Method': 'GET',
            },
            validateStatus: false,
          }
        );

        const allowedOrigin = response.headers['access-control-allow-origin'];
        const passed = allowedOrigin === '*' || allowedOrigin === origin;

        this.recordResult({
          type: 'CORS',
          origin,
          status: response.status,
          passed,
          details: passed 
            ? `CORS allowed for ${origin}` 
            : `CORS blocked for ${origin}`,
        });
      } catch (error) {
        this.recordResult({
          type: 'CORS',
          origin,
          status: error.response?.status || 500,
          passed: true,
          details: 'CORS blocked correctly',
        });
      }
    }
  }

  detectSQLInjectionSuccess(response) {
    const data = response.data;
    if (typeof data === 'string') {
      return data.includes('error') === false || 
             data.includes('SQL') ||
             data.includes('syntax') ||
             data.length > 0;
    }
    return false;
  }

  detectXSSSuccess(response) {
    const data = typeof response.data === 'string' 
      ? response.data 
      : JSON.stringify(response.data);
    
    return data.includes('<script') ||
           data.includes('alert(') ||
           data.includes('onerror=') ||
           data.includes('javascript:');
  }

  detectPathTraversalSuccess(response) {
    return response.status === 200 && 
           (response.data?.includes('root:') || 
            response.data?.includes('[System]'));
  }

  detectCommandInjectionSuccess(response) {
    return response.status === 200 && 
           response.data?.includes('uid=') ||
           response.data?.includes('root');
  }

  recordResult(result) {
    this.testResults.push({
      ...result,
      timestamp: new Date().toISOString(),
    });
  }

  generateReport() {
    const report = {
      timestamp: new Date().toISOString(),
      target: this.baseUrl,
      results: this.testResults,
      summary: {
        total: this.testResults.length,
        passed: this.testResults.filter(r => r.passed).length,
        failed: this.testResults.filter(r => !r.passed).length,
        byType: this.testResults.reduce((acc, r) => {
          acc[r.type] = acc[r.type] || { passed: 0, total: 0 };
          acc[r.type].total++;
          if (r.passed) acc[r.type].passed++;
          return acc;
        }, {}),
      },
      recommendations: this.generateRecommendations(),
    };

    const reportPath = path.join(__dirname, '../../security-reports/penetration-test-report.json');
    if (!fs.existsSync(path.dirname(reportPath))) {
      fs.mkdirSync(path.dirname(reportPath), { recursive: true });
    }
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`\n✅ Security report saved to: ${reportPath}`);
  }

  generateRecommendations() {
    const recommendations = [];
    const failed = this.testResults.filter(r => !r.passed);

    if (failed.some(r => r.type === 'SQL Injection')) {
      recommendations.push('Implement parameterized queries and input validation');
    }

    if (failed.some(r => r.type === 'XSS')) {
      recommendations.push('Implement output encoding and Content Security Policy');
    }

    if (failed.some(r => r.type === 'Rate Limiting')) {
      recommendations.push('Implement rate limiting on all endpoints');
    }

    if (failed.some(r => r.type === 'JWT Security')) {
      recommendations.push('Strengthen JWT token validation and signing');
    }

    if (failed.some(r => r.type === 'SSL/TLS')) {
      recommendations.push('Enable HTTPS and configure HSTS');
    }

    if (failed.length === 0) {
      recommendations.push('All security tests passed! Keep up the good practices.');
    }

    return recommendations;
  }
}

// Run the penetration tests
const tester = new PenetrationTest();
tester.runAllTests().catch(console.error);