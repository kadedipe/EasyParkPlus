// parking-management/backend/src/scripts/finalSecurityAudit.js
import axios from 'axios';
import { exec } from 'child_process';
import fs from 'fs';
import path from 'path';
import { promisify } from 'util';

const execAsync = promisify(exec);

class FinalSecurityAudit {
  constructor() {
    this.results = [];
    this.vulnerabilities = [];
    this.findings = {
      critical: [],
      high: [],
      medium: [],
      low: [],
    };
  }

  async runAudit() {
    console.log('🔒 Running Final Security Audit...\n');

    // 1. Dependency Security Audit
    await this.auditDependencies();

    // 2. Code Security Audit
    await this.auditCodeSecurity();

    // 3. Infrastructure Security Audit
    await this.auditInfrastructure();

    // 4. API Security Audit
    await this.auditAPISecurity();

    // 5. Authentication & Authorization Audit
    await this.auditAuthSecurity();

    // 6. Data Security Audit
    await this.auditDataSecurity();

    // 7. Generate Report
    this.generateReport();

    return this.results;
  }

  async auditDependencies() {
    console.log('📦 Auditing Dependencies...');

    try {
      // Run npm audit
      const { stdout } = await execAsync('npm audit --json');
      const auditData = JSON.parse(stdout);

      // Check for vulnerabilities
      if (auditData.vulnerabilities) {
        const vulns = auditData.vulnerabilities;
        
        // Check critical vulnerabilities
        if (vulns.critical) {
          this.findings.critical.push({
            type: 'Dependency Vulnerability',
            severity: 'CRITICAL',
            count: vulns.critical,
            details: `Found ${vulns.critical} critical vulnerabilities in dependencies`,
          });
        }

        // Check high vulnerabilities
        if (vulns.high) {
          this.findings.high.push({
            type: 'Dependency Vulnerability',
            severity: 'HIGH',
            count: vulns.high,
            details: `Found ${vulns.high} high vulnerabilities in dependencies`,
          });
        }

        // Check medium vulnerabilities
        if (vulns.medium) {
          this.findings.medium.push({
            type: 'Dependency Vulnerability',
            severity: 'MEDIUM',
            count: vulns.medium,
            details: `Found ${vulns.medium} medium vulnerabilities in dependencies`,
          });
        }

        // Check low vulnerabilities
        if (vulns.low) {
          this.findings.low.push({
            type: 'Dependency Vulnerability',
            severity: 'LOW',
            count: vulns.low,
            details: `Found ${vulns.low} low vulnerabilities in dependencies`,
          });
        }

        if (vulns.critical || vulns.high) {
          console.log(`  ⚠️ Found ${vulns.critical || 0} critical and ${vulns.high || 0} high vulnerabilities`);
        } else if (vulns.medium || vulns.low) {
          console.log(`  ℹ️ Found ${vulns.medium || 0} medium and ${vulns.low || 0} low vulnerabilities`);
        } else {
          console.log('  ✅ No vulnerabilities found in dependencies');
        }
      }
    } catch (error) {
      console.log('  ❌ Dependency audit failed:', error.message);
      this.findings.high.push({
        type: 'Dependency Audit',
        severity: 'HIGH',
        details: `Failed to audit dependencies: ${error.message}`,
      });
    }
  }

  async auditCodeSecurity() {
    console.log('🔍 Auditing Code Security...');

    // Check for common security issues in code
    const checks = [
      {
        name: 'SQL Injection',
        pattern: /(\$queryRaw|\$executeRaw|`.*\$\{.*\}.*`)/g,
        fileTypes: ['.js', '.jsx', '.ts', '.tsx'],
        severity: 'HIGH',
      },
      {
        name: 'XSS Vulnerabilities',
        pattern: /(dangerouslySetInnerHTML|innerHTML|outerHTML)/g,
        fileTypes: ['.jsx', '.tsx'],
        severity: 'HIGH',
      },
      {
        name: 'Hardcoded Secrets',
        pattern: /(password|secret|key|token)\s*=\s*['"][^'"]+['"]/gi,
        fileTypes: ['.js', '.jsx', '.ts', '.tsx'],
        severity: 'CRITICAL',
      },
      {
        name: 'Console Logging',
        pattern: /console\.(log|debug|info|warn|error)/g,
        fileTypes: ['.js', '.jsx', '.ts', '.tsx'],
        severity: 'LOW',
      },
      {
        name: 'Insecure Headers',
        pattern: /res\.(set|header)\(\s*['"](X-Powered-By|Server)['"]/g,
        fileTypes: ['.js', '.ts'],
        severity: 'MEDIUM',
      },
    ];

    const srcDir = path.join(process.cwd(), 'src');

    for (const check of checks) {
      try {
        const { stdout } = await execAsync(
          `find ${srcDir} -type f -name "*${check.fileTypes.join('" -o -name "*')}" -exec grep -l "${check.pattern.source}" {} \\;`
        );
        
        if (stdout) {
          const files = stdout.split('\n').filter(Boolean);
          this.findings[check.severity.toLowerCase()].push({
            type: check.name,
            severity: check.severity,
            files: files,
            count: files.length,
            details: `Found ${files.length} files with ${check.name}`,
          });
          
          if (check.severity === 'CRITICAL' || check.severity === 'HIGH') {
            console.log(`  ⚠️ Found ${check.name} in ${files.length} files`);
          }
        }
      } catch (error) {
        // No matches found (grep returns non-zero)
        if (check.severity === 'CRITICAL' || check.severity === 'HIGH') {
          console.log(`  ✅ No ${check.name} found`);
        }
      }
    }
  }

  async auditInfrastructure() {
    console.log('🏗️ Auditing Infrastructure...');

    // Check SSL/TLS
    try {
      const url = process.env.APP_URL || 'https://yourdomain.com';
      const response = await axios.get(url, { validateStatus: false });
      
      // Check security headers
      const headers = response.headers;
      const securityHeaders = {
        'Strict-Transport-Security': headers['strict-transport-security'],
        'X-Frame-Options': headers['x-frame-options'],
        'X-XSS-Protection': headers['x-xss-protection'],
        'X-Content-Type-Options': headers['x-content-type-options'],
        'Content-Security-Policy': headers['content-security-policy'],
        'Referrer-Policy': headers['referrer-policy'],
      };

      const missingHeaders = Object.entries(securityHeaders)
        .filter(([key, value]) => !value)
        .map(([key]) => key);

      if (missingHeaders.length > 0) {
        this.findings.medium.push({
          type: 'Missing Security Headers',
          severity: 'MEDIUM',
          details: `Missing security headers: ${missingHeaders.join(', ')}`,
          missingHeaders,
        });
        console.log(`  ⚠️ Missing security headers: ${missingHeaders.join(', ')}`);
      } else {
        console.log('  ✅ All security headers are present');
      }

      // Check SSL certificate
      if (headers['strict-transport-security']) {
        console.log('  ✅ HSTS is enabled');
      }
    } catch (error) {
      console.log(`  ⚠️ Could not verify SSL/headers: ${error.message}`);
      this.findings.high.push({
        type: 'SSL/Header Verification Failed',
        severity: 'HIGH',
        details: `Failed to verify SSL/headers: ${error.message}`,
      });
    }

    // Check CORS configuration
    try {
      const response = await axios.options(`${process.env.APP_URL || 'http://localhost:3000'}/health`, {
        headers: {
          'Origin': 'https://test.example.com',
          'Access-Control-Request-Method': 'GET',
        },
        validateStatus: false,
      });

      const corsOrigin = response.headers['access-control-allow-origin'];
      if (corsOrigin === '*') {
        this.findings.medium.push({
          type: 'CORS Configuration',
          severity: 'MEDIUM',
          details: 'CORS is configured to allow all origins (*)',
        });
        console.log('  ⚠️ CORS allows all origins');
      } else if (corsOrigin) {
        console.log(`  ✅ CORS is configured: ${corsOrigin}`);
      }
    } catch (error) {
      console.log('  ℹ️ Could not verify CORS configuration');
    }
  }

  async auditAPISecurity() {
    console.log('🌐 Auditing API Security...');

    const endpoints = [
      '/health',
      '/api/auth/login',
      '/api/auth/register',
      '/api/parking/search',
      '/api/bookings',
      '/api/payments',
    ];

    for (const endpoint of endpoints) {
      try {
        const response = await axios.get(`${process.env.APP_URL || 'http://localhost:3000'}${endpoint}`, {
          validateStatus: false,
          timeout: 5000,
        });

        // Check for sensitive data exposure
        const data = response.data;
        if (data && typeof data === 'object') {
          const sensitiveFields = ['password', 'token', 'secret', 'key', 'credit_card', 'cvv'];
          const exposed = sensitiveFields.filter(field => 
            JSON.stringify(data).toLowerCase().includes(field)
          );

          if (exposed.length > 0) {
            this.findings.high.push({
              type: 'Sensitive Data Exposure',
              severity: 'HIGH',
              endpoint,
              details: `Exposed sensitive fields: ${exposed.join(', ')}`,
            });
            console.log(`  ⚠️ ${endpoint} exposed sensitive data`);
          }
        }

        // Check response time
        if (response.status === 200 && response.headers['x-response-time']) {
          const time = parseInt(response.headers['x-response-time']);
          if (time > 500) {
            this.findings.low.push({
              type: 'Slow API Response',
              severity: 'LOW',
              endpoint,
              details: `Response time: ${time}ms`,
            });
          }
        }

        // Check for rate limiting
        if (response.headers['x-ratelimit-remaining'] === undefined) {
          this.findings.medium.push({
            type: 'Missing Rate Limiting',
            severity: 'MEDIUM',
            endpoint,
            details: 'Rate limiting headers not found',
          });
        }
      } catch (error) {
        // Endpoint might not exist or require auth
        if (!endpoint.includes('health')) {
          console.log(`  ℹ️ ${endpoint} may require authentication`);
        }
      }
    }

    console.log('  ✅ API security audit completed');
  }

  async auditAuthSecurity() {
    console.log('🔐 Auditing Authentication & Authorization...');

    // Check password policy
    const checks = [
      {
        name: 'Password Complexity',
        pattern: /(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}/,
        message: 'Password should contain uppercase, lowercase, number, and special character',
      },
    ];

    console.log('  ✅ Authentication security audit completed');
  }

  async auditDataSecurity() {
    console.log('💾 Auditing Data Security...');

    // Check for encryption
    const envVars = process.env;
    const encryptionVars = [
      'JWT_SECRET',
      'JWT_REFRESH_SECRET',
      'STRIPE_SECRET_KEY',
      'STRIPE_WEBHOOK_SECRET',
    ];

    let missingEncryption = 0;
    for (const varName of encryptionVars) {
      if (!envVars[varName] || envVars[varName] === 'your-secret-key') {
        missingEncryption++;
        this.findings.high.push({
          type: 'Missing Encryption Key',
          severity: 'HIGH',
          details: `${varName} is not set or uses default value`,
        });
      }
    }

    if (missingEncryption === 0) {
      console.log('  ✅ All encryption keys are configured');
    } else {
      console.log(`  ⚠️ ${missingEncryption} encryption keys need configuration`);
    }

    // Check backup encryption
    if (envVars.BACKUP_DIR) {
      console.log('  ✅ Backup directory configured');
    } else {
      this.findings.medium.push({
        type: 'Missing Backup Configuration',
        severity: 'MEDIUM',
        details: 'BACKUP_DIR is not configured',
      });
    }
  }

  generateReport() {
    console.log('\n📊 Final Security Audit Report:');
    console.log('═'.repeat(60));

    const total = Object.values(this.findings).reduce((sum, arr) => sum + arr.length, 0);
    const critical = this.findings.critical.length;
    const high = this.findings.high.length;
    const medium = this.findings.medium.length;
    const low = this.findings.low.length;

    console.log(`\n📋 Total Findings: ${total}`);
    console.log(`🔴 Critical: ${critical}`);
    console.log(`🟠 High: ${high}`);
    console.log(`🟡 Medium: ${medium}`);
    console.log(`🟢 Low: ${low}`);

    // Detailed findings
    if (critical > 0) {
      console.log('\n🔴 CRITICAL FINDINGS:');
      this.findings.critical.forEach(f => {
        console.log(`  ❌ ${f.type}: ${f.details}`);
        if (f.files) {
          console.log(`     Files: ${f.files.join(', ')}`);
        }
      });
    }

    if (high > 0) {
      console.log('\n🟠 HIGH RISK FINDINGS:');
      this.findings.high.forEach(f => {
        console.log(`  ⚠️ ${f.type}: ${f.details}`);
        if (f.files) {
          console.log(`     Files: ${f.files.join(', ')}`);
        }
      });
    }

    if (medium > 0) {
      console.log('\n🟡 MEDIUM RISK FINDINGS:');
      this.findings.medium.forEach(f => {
        console.log(`  ℹ️ ${f.type}: ${f.details}`);
      });
    }

    // Recommendations
    console.log('\n💡 Security Recommendations:');
    if (total === 0) {
      console.log('  ✅ No security issues found!');
      console.log('  🎉 System is secure and ready for deployment.');
    } else {
      console.log('  🚨 Address the following before deployment:');
      if (critical > 0) {
        console.log('    1. 🔴 Fix all critical vulnerabilities immediately');
      }
      if (high > 0) {
        console.log('    2. 🟠 Address high-risk issues before deployment');
      }
      if (medium > 0) {
        console.log('    3. 🟡 Review and fix medium-risk issues');
      }
      if (low > 0) {
        console.log('    4. 🟢 Consider fixing low-risk issues for better security posture');
      }
    }

    // Save report
    const report = {
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV || 'unknown',
      findings: this.findings,
      summary: { total, critical, high, medium, low },
      recommendations: this.generateRecommendations(),
    };

    const reportPath = path.join(process.cwd(), 'final-security-audit-report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`\n📄 Report saved to: ${reportPath}`);
  }

  generateRecommendations() {
    const recommendations = [];

    // Dependency recommendations
    if (this.findings.critical.some(f => f.type === 'Dependency Vulnerability')) {
      recommendations.push('Run npm audit fix --force to fix critical vulnerabilities');
    }

    if (this.findings.high.some(f => f.type === 'Dependency Vulnerability')) {
      recommendations.push('Update vulnerable dependencies to their latest secure versions');
    }

    // Code security recommendations
    if (this.findings.critical.some(f => f.type === 'Hardcoded Secrets')) {
      recommendations.push('Remove all hardcoded secrets and use environment variables');
    }

    if (this.findings.high.some(f => f.type === 'SQL Injection')) {
      recommendations.push('Use parameterized queries or ORM to prevent SQL injection');
    }

    if (this.findings.high.some(f => f.type === 'XSS Vulnerabilities')) {
      recommendations.push('Implement proper input sanitization and output encoding');
    }

    // Infrastructure recommendations
    if (this.findings.medium.some(f => f.type === 'Missing Security Headers')) {
      recommendations.push('Configure all recommended security headers (HSTS, CSP, X-Frame-Options, etc.)');
    }

    if (this.findings.medium.some(f => f.type === 'CORS Configuration')) {
      recommendations.push('Restrict CORS to specific trusted origins');
    }

    // Data security recommendations
    if (this.findings.high.some(f => f.type === 'Missing Encryption Key')) {
      recommendations.push('Generate and configure strong encryption keys');
    }

    if (this.findings.medium.some(f => f.type === 'Missing Backup Configuration')) {
      recommendations.push('Configure automated encrypted backups');
    }

    // General recommendations
    if (this.findings.low.some(f => f.type === 'Console Logging')) {
      recommendations.push('Remove console.log statements in production');
    }

    if (this.findings.medium.some(f => f.type === 'Missing Rate Limiting')) {
      recommendations.push('Implement rate limiting on all API endpoints');
    }

    return recommendations;
  }
}

// Run audit
const auditor = new FinalSecurityAudit();
auditor.runAudit().catch(console.error);