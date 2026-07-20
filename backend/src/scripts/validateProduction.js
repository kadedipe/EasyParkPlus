// parking-management/backend/src/scripts/validateProduction.js
import { PrismaClient } from '@prisma/client';
import axios from 'axios';
import { exec } from 'child_process';
import fs from 'fs';
import path from 'path';
import { createClient } from 'redis';
import { fileURLToPath } from 'url';
import { promisify } from 'util';

const execAsync = promisify(exec);
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class ProductionValidator {
  constructor() {
    this.baseUrl = process.env.APP_URL || 'https://api.yourdomain.com';
    this.results = [];
    this.prisma = new PrismaClient();
    this.redisClient = createClient({
      url: process.env.REDIS_URL || 'redis://localhost:6379',
    });
    this.thresholds = {
      responseTime: 200, // ms
      uptime: 99.9, // percentage
      errorRate: 1, // percentage
      memoryUsage: 80, // percentage
      cpuUsage: 70, // percentage
      diskUsage: 85, // percentage
    };
  }

  async validate() {
    console.log('🔍 Starting Production Environment Validation...\n');

    // 1. Infrastructure Validation
    await this.validateInfrastructure();

    // 2. Application Validation
    await this.validateApplication();

    // 3. Database Validation
    await this.validateDatabase();

    // 4. Redis Validation
    await this.validateRedis();

    // 5. Security Validation
    await this.validateSecurity();

    // 6. Performance Validation
    await this.validatePerformance();

    // 7. Monitoring Validation
    await this.validateMonitoring();

    // 8. Generate Report
    this.generateReport();

    // Cleanup
    await this.prisma.$disconnect();
    await this.redisClient.quit();

    return this.results;
  }

  async validateInfrastructure() {
    console.log('📡 Validating Infrastructure...');

    // Check CPU
    const cpuInfo = await this.getCpuInfo();
    this.recordResult({
      category: 'Infrastructure',
      check: 'CPU Usage',
      value: `${cpuInfo.usage.toFixed(1)}%`,
      passed: cpuInfo.usage < this.thresholds.cpuUsage,
      details: cpuInfo,
    });

    // Check Memory
    const memoryInfo = await this.getMemoryInfo();
    this.recordResult({
      category: 'Infrastructure',
      check: 'Memory Usage',
      value: `${memoryInfo.usage.toFixed(1)}%`,
      passed: memoryInfo.usage < this.thresholds.memoryUsage,
      details: memoryInfo,
    });

    // Check Disk
    const diskInfo = await this.getDiskInfo();
    this.recordResult({
      category: 'Infrastructure',
      check: 'Disk Usage',
      value: `${diskInfo.usage.toFixed(1)}%`,
      passed: diskInfo.usage < this.thresholds.diskUsage,
      details: diskInfo,
    });

    // Check Network
    const networkInfo = await this.getNetworkInfo();
    this.recordResult({
      category: 'Infrastructure',
      check: 'Network Connectivity',
      value: networkInfo.status,
      passed: networkInfo.status === 'healthy',
      details: networkInfo,
    });

    console.log(`  ✅ Infrastructure validated: CPU ${cpuInfo.usage.toFixed(1)}%, Memory ${memoryInfo.usage.toFixed(1)}%, Disk ${diskInfo.usage.toFixed(1)}%`);
  }

  async getCpuInfo() {
    try {
      const { stdout } = await execAsync('top -bn1 | grep "Cpu(s)"');
      const usage = parseFloat(stdout.match(/(\d+\.\d+)/)?.[0] || '0');
      return { usage, details: stdout.trim() };
    } catch (error) {
      return { usage: 0, error: error.message };
    }
  }

  async getMemoryInfo() {
    try {
      const { stdout } = await execAsync('free -m');
      const lines = stdout.split('\n');
      const memLine = lines[1].split(/\s+/);
      const total = parseInt(memLine[1]);
      const used = parseInt(memLine[2]);
      const usage = (used / total) * 100;
      return { usage, total, used, details: stdout.trim() };
    } catch (error) {
      return { usage: 0, error: error.message };
    }
  }

  async getDiskInfo() {
    try {
      const { stdout } = await execAsync('df -h /');
      const lines = stdout.split('\n');
      const diskLine = lines[1].split(/\s+/);
      const usage = parseFloat(diskLine[4].replace('%', ''));
      return { usage, details: stdout.trim() };
    } catch (error) {
      return { usage: 0, error: error.message };
    }
  }

  async getNetworkInfo() {
    try {
      const { stdout } = await execAsync('ping -c 4 google.com');
      const status = stdout.includes('64 bytes') ? 'healthy' : 'unhealthy';
      return { status, details: stdout.trim() };
    } catch (error) {
      return { status: 'unhealthy', error: error.message };
    }
  }

  async validateApplication() {
    console.log('📱 Validating Application...');

    // Check API Health
    try {
      const response = await axios.get(`${this.baseUrl}/health`, {
        timeout: 5000,
        validateStatus: false,
      });
      const passed = response.status === 200;
      this.recordResult({
        category: 'Application',
        check: 'API Health',
        value: `Status ${response.status}`,
        passed,
        details: response.data,
      });
      console.log(`  ✅ API health check: ${passed ? 'PASSED' : 'FAILED'}`);
    } catch (error) {
      this.recordResult({
        category: 'Application',
        check: 'API Health',
        value: 'Unreachable',
        passed: false,
        details: error.message,
      });
    }

    // Check Environment Variables
    const envVars = [
      'NODE_ENV',
      'DATABASE_URL',
      'REDIS_URL',
      'JWT_SECRET',
      'STRIPE_SECRET_KEY',
      'STRIPE_WEBHOOK_SECRET',
    ];
    
    let missingVars = 0;
    for (const varName of envVars) {
      const exists = !!process.env[varName];
      if (!exists) missingVars++;
      this.recordResult({
        category: 'Application',
        check: `Env: ${varName}`,
        value: exists ? 'Present' : 'Missing',
        passed: exists,
        details: exists ? 'Configured' : 'Not found',
      });
    }
    console.log(`  ✅ Environment variables: ${envVars.length - missingVars}/${envVars.length} present`);

    // Check SSL Certificate
    try {
      const sslInfo = await this.checkSSL();
      this.recordResult({
        category: 'Application',
        check: 'SSL Certificate',
        value: sslInfo.valid ? 'Valid' : 'Invalid',
        passed: sslInfo.valid,
        details: sslInfo,
      });
      console.log(`  ✅ SSL: ${sslInfo.valid ? 'Valid' : 'Invalid'}`);
    } catch (error) {
      this.recordResult({
        category: 'Application',
        check: 'SSL Certificate',
        value: 'Error',
        passed: false,
        details: error.message,
      });
    }
  }

  async checkSSL() {
    try {
      const { stdout } = await execAsync(`openssl s_client -connect ${new URL(this.baseUrl).hostname}:443 -servername ${new URL(this.baseUrl).hostname} < /dev/null 2>/dev/null | openssl x509 -noout -dates`);
      const lines = stdout.split('\n');
      const notAfter = lines.find(l => l.includes('notAfter='))?.replace('notAfter=', '');
      const valid = !!notAfter;
      return { valid, notAfter, details: stdout.trim() };
    } catch (error) {
      return { valid: false, error: error.message };
    }
  }

  async validateDatabase() {
    console.log('🗄️ Validating Database...');

    try {
      // Test connection
      await this.prisma.$queryRaw`SELECT 1`;
      
      // Get database stats
      const stats = await this.prisma.$queryRaw`
        SELECT 
          (SELECT count(*) FROM users) as users,
          (SELECT count(*) FROM parking_spots) as parking_spots,
          (SELECT count(*) FROM bookings) as bookings,
          (SELECT count(*) FROM payments) as payments,
          (SELECT count(*) FROM notifications) as notifications
      `;

      this.recordResult({
        category: 'Database',
        check: 'Connection',
        value: 'Connected',
        passed: true,
        details: stats[0],
      });

      // Check replication
      const replicaStatus = await this.checkReplication();
      this.recordResult({
        category: 'Database',
        check: 'Replication',
        value: replicaStatus.status,
        passed: replicaStatus.status === 'healthy',
        details: replicaStatus,
      });

      // Check query performance
      const queryPerformance = await this.measureQueryPerformance();
      this.recordResult({
        category: 'Database',
        check: 'Query Performance',
        value: `${queryPerformance.avg.toFixed(2)}ms`,
        passed: queryPerformance.avg < 100,
        details: queryPerformance,
      });

      console.log(`  ✅ Database: ${stats[0].bookings} bookings, ${stats[0].users} users`);
    } catch (error) {
      this.recordResult({
        category: 'Database',
        check: 'Connection',
        value: 'Error',
        passed: false,
        details: error.message,
      });
      console.log(`  ❌ Database connection failed: ${error.message}`);
    }
  }

  async checkReplication() {
    try {
      const result = await this.prisma.$queryRaw`
        SELECT 
          pg_is_in_recovery() as is_replica,
          (SELECT count(*) FROM pg_stat_replication) as replica_count
      `;
      return {
        status: result[0].replica_count > 0 ? 'healthy' : 'warning',
        isReplica: result[0].is_replica,
        replicaCount: result[0].replica_count,
      };
    } catch (error) {
      return { status: 'unknown', error: error.message };
    }
  }

  async measureQueryPerformance() {
    const times = [];
    for (let i = 0; i < 10; i++) {
      const start = Date.now();
      await this.prisma.$queryRaw`SELECT 1`;
      times.push(Date.now() - start);
    }
    return {
      avg: times.reduce((a, b) => a + b, 0) / times.length,
      min: Math.min(...times),
      max: Math.max(...times),
    };
  }

  async validateRedis() {
    console.log('📦 Validating Redis...');

    try {
      await this.redisClient.connect();
      
      // Test operations
      await this.redisClient.set('test:key', 'test:value');
      const value = await this.redisClient.get('test:key');
      await this.redisClient.del('test:key');

      // Get Redis info
      const info = await this.redisClient.info();
      const usedMemory = info.match(/used_memory_human:([^\r\n]*)/)?.[1] || 'unknown';
      const connectedClients = info.match(/connected_clients:([^\r\n]*)/)?.[1] || '0';

      this.recordResult({
        category: 'Redis',
        check: 'Connection',
        value: 'Connected',
        passed: true,
        details: { usedMemory, connectedClients },
      });

      // Check memory usage
      const memoryInfo = await this.redisClient.info('memory');
      const memoryUsage = parseFloat(memoryInfo.match(/used_memory_peak_human:([^\r\n]*)/)?.[1] || '0');
      const memoryLimit = parseFloat(process.env.REDIS_MAX_MEMORY || '1024');

      this.recordResult({
        category: 'Redis',
        check: 'Memory Usage',
        value: `${(memoryUsage / memoryLimit * 100).toFixed(1)}%`,
        passed: memoryUsage < memoryLimit * 0.8,
        details: { used: memoryUsage, limit: memoryLimit },
      });

      console.log(`  ✅ Redis: ${connectedClients} clients, ${usedMemory} memory`);
    } catch (error) {
      this.recordResult({
        category: 'Redis',
        check: 'Connection',
        value: 'Error',
        passed: false,
        details: error.message,
      });
      console.log(`  ❌ Redis connection failed: ${error.message}`);
    }
  }

  async validateSecurity() {
    console.log('🔒 Validating Security...');

    // Check CORS
    try {
      const response = await axios.options(`${this.baseUrl}/health`, {
        headers: {
          'Origin': 'https://yourdomain.com',
          'Access-Control-Request-Method': 'GET',
        },
        validateStatus: false,
      });
      const corsHeader = response.headers['access-control-allow-origin'];
      this.recordResult({
        category: 'Security',
        check: 'CORS',
        value: corsHeader || 'Missing',
        passed: !!corsHeader,
        details: { allowedOrigins: corsHeader },
      });
    } catch (error) {
      this.recordResult({
        category: 'Security',
        check: 'CORS',
        value: 'Error',
        passed: false,
        details: error.message,
      });
    }

    // Check Security Headers
    try {
      const response = await axios.get(this.baseUrl, { validateStatus: false });
      const securityHeaders = {
        'X-Frame-Options': response.headers['x-frame-options'],
        'X-XSS-Protection': response.headers['x-xss-protection'],
        'X-Content-Type-Options': response.headers['x-content-type-options'],
        'Strict-Transport-Security': response.headers['strict-transport-security'],
        'Content-Security-Policy': response.headers['content-security-policy'],
      };

      const missingHeaders = Object.entries(securityHeaders)
        .filter(([key, value]) => !value)
        .map(([key]) => key);

      this.recordResult({
        category: 'Security',
        check: 'Security Headers',
        value: missingHeaders.length === 0 ? 'All Present' : `${missingHeaders.length} Missing`,
        passed: missingHeaders.length === 0,
        details: { headers: securityHeaders, missing: missingHeaders },
      });

      console.log(`  ✅ Security Headers: ${missingHeaders.length === 0 ? 'All Present' : `${missingHeaders.length} Missing`}`);
    } catch (error) {
      this.recordResult({
        category: 'Security',
        check: 'Security Headers',
        value: 'Error',
        passed: false,
        details: error.message,
      });
    }
  }

  async validatePerformance() {
    console.log('⚡ Validating Performance...');

    // Check response time
    const responseTimes = [];
    for (let i = 0; i < 10; i++) {
      const start = Date.now();
      await axios.get(`${this.baseUrl}/health`, { timeout: 5000 });
      responseTimes.push(Date.now() - start);
    }

    const avgResponseTime = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;
    const maxResponseTime = Math.max(...responseTimes);

    this.recordResult({
      category: 'Performance',
      check: 'Response Time',
      value: `${avgResponseTime.toFixed(2)}ms`,
      passed: avgResponseTime < this.thresholds.responseTime,
      details: { avg: avgResponseTime, max: maxResponseTime, samples: responseTimes },
    });

    console.log(`  ✅ Response Time: ${avgResponseTime.toFixed(2)}ms (threshold: ${this.thresholds.responseTime}ms)`);
  }

  async validateMonitoring() {
    console.log('📊 Validating Monitoring...');

    // Check if Sentry is configured
    const sentryConfigured = !!process.env.SENTRY_DSN;
    this.recordResult({
      category: 'Monitoring',
      check: 'Sentry',
      value: sentryConfigured ? 'Configured' : 'Not Configured',
      passed: sentryConfigured,
      details: { dsn: process.env.SENTRY_DSN ? 'Present' : 'Missing' },
    });

    // Check if logging is configured
    const loggingConfigured = !!process.env.LOG_LEVEL;
    this.recordResult({
      category: 'Monitoring',
      check: 'Logging',
      value: loggingConfigured ? 'Configured' : 'Not Configured',
      passed: loggingConfigured,
      details: { logLevel: process.env.LOG_LEVEL || 'Not Set' },
    });

    // Check if Health endpoint is accessible
    try {
      const response = await axios.get(`${this.baseUrl}/health`);
      this.recordResult({
        category: 'Monitoring',
        check: 'Health Endpoint',
        value: `Status ${response.status}`,
        passed: response.status === 200,
        details: response.data,
      });
    } catch (error) {
      this.recordResult({
        category: 'Monitoring',
        check: 'Health Endpoint',
        value: 'Unreachable',
        passed: false,
        details: error.message,
      });
    }

    console.log(`  ✅ Monitoring: Sentry ${sentryConfigured ? '✓' : '✗'}, Logging ${loggingConfigured ? '✓' : '✗'}`);
  }

  recordResult(result) {
    this.results.push({
      ...result,
      timestamp: new Date().toISOString(),
      environment: 'production',
    });
  }

  generateReport() {
    const report = {
      timestamp: new Date().toISOString(),
      environment: 'production',
      summary: {
        total: this.results.length,
        passed: this.results.filter(r => r.passed).length,
        failed: this.results.filter(r => !r.passed).length,
        byCategory: this.results.reduce((acc, r) => {
          acc[r.category] = acc[r.category] || { passed: 0, total: 0 };
          acc[r.category].total++;
          if (r.passed) acc[r.category].passed++;
          return acc;
        }, {}),
      },
      results: this.results,
      recommendations: this.generateRecommendations(),
      thresholds: this.thresholds,
    };

    const reportPath = path.join(process.cwd(), 'production-validation-report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`\n✅ Production validation report saved to: ${reportPath}`);

    // Print summary
    console.log('\n📊 Production Validation Summary:');
    console.log('═'.repeat(50));
    console.log(`✅ Passed: ${report.summary.passed}`);
    console.log(`❌ Failed: ${report.summary.failed}`);
    console.log('═'.repeat(50));
    
    if (report.summary.failed === 0) {
      console.log('🎉 All production validations PASSED!');
    } else {
      console.log('⚠️ Some validations FAILED. Please review the report.');
    }
  }

  generateRecommendations() {
    const recommendations = [];
    const failed = this.results.filter(r => !r.passed);

    if (failed.some(r => r.category === 'Infrastructure' && r.check === 'CPU Usage')) {
      recommendations.push('Consider scaling up CPU resources or optimizing application performance');
    }

    if (failed.some(r => r.category === 'Infrastructure' && r.check === 'Memory Usage')) {
      recommendations.push('Consider increasing memory allocation or optimizing memory usage');
    }

    if (failed.some(r => r.category === 'Application' && r.check.includes('Env:'))) {
      recommendations.push('Configure all required environment variables');
    }

    if (failed.some(r => r.category === 'Application' && r.check === 'SSL Certificate')) {
      recommendations.push('Renew or update SSL certificate');
    }

    if (failed.some(r => r.category === 'Database' && r.check === 'Connection')) {
      recommendations.push('Check database connectivity and credentials');
    }

    if (failed.some(r => r.category === 'Security' && r.check === 'Security Headers')) {
      recommendations.push('Configure missing security headers');
    }

    if (failed.some(r => r.category === 'Monitoring' && r.check === 'Sentry')) {
      recommendations.push('Configure Sentry for error tracking');
    }

    if (recommendations.length === 0) {
      recommendations.push('All validations passed. Production environment is healthy!');
    }

    return recommendations;
  }
}

// Run validation
const validator = new ProductionValidator();
validator.validate().catch(console.error);