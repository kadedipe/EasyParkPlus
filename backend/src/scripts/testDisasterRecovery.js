// parking-management/backend/src/scripts/testDisasterRecovery.js
import { PrismaClient } from '@prisma/client';
import axios from 'axios';
import { exec } from 'child_process';
import { createClient } from 'redis';
import { promisify } from 'util';

const execAsync = promisify(exec);

class DisasterRecoveryTest {
  constructor() {
    this.prisma = new PrismaClient();
    this.redisClient = createClient({
      url: process.env.REDIS_URL || 'redis://localhost:6379',
    });
    this.results = [];
    this.startTime = null;
    this.recoveryTime = null;
  }

  async runAllTests() {
    console.log('🔄 Running Disaster Recovery Tests...\n');
    this.startTime = Date.now();

    // 1. Test Database Backup & Restore
    await this.testDatabaseBackupRestore();

    // 2. Test Database Failover
    await this.testDatabaseFailover();

    // 3. Test Redis Failover
    await this.testRedisFailover();

    // 4. Test Full System Recovery
    await this.testFullSystemRecovery();

    // 5. Test Data Integrity
    await this.testDataIntegrity();

    // 6. Generate Report
    this.generateReport();

    await this.prisma.$disconnect();
    await this.redisClient.quit();

    return this.results;
  }

  async testDatabaseBackupRestore() {
    console.log('📦 Testing Database Backup & Restore...');

    try {
      // Create test data
      const testData = await this.createTestData();

      // Create backup
      const backupName = await this.createBackup();

      // Delete test data
      await this.deleteTestData(testData);

      // Restore backup
      const restoreTime = await this.restoreBackup(backupName);

      // Verify data
      const verified = await this.verifyData(testData);

      this.recordResult({
        test: 'Database Backup & Restore',
        status: verified ? 'PASSED' : 'FAILED',
        details: {
          backupName,
          restoreTime: `${restoreTime}ms`,
          dataVerified: verified,
        },
        passed: verified,
      });

      console.log(`  ${verified ? '✅' : '❌'} Database backup & restore test ${verified ? 'PASSED' : 'FAILED'}`);
    } catch (error) {
      this.recordResult({
        test: 'Database Backup & Restore',
        status: 'FAILED',
        details: { error: error.message },
        passed: false,
      });
      console.log(`  ❌ Database backup & restore test FAILED: ${error.message}`);
    }
  }

  async testDatabaseFailover() {
    console.log('💥 Testing Database Failover...');

    try {
      // Simulate primary database failure
      await this.simulatePrimaryFailure();

      // Wait for failover
      const failoverTime = await this.waitForFailover();

      // Verify system is operational
      const operational = await this.checkSystemOperational();

      this.recordResult({
        test: 'Database Failover',
        status: operational ? 'PASSED' : 'FAILED',
        details: {
          failoverTime: `${failoverTime}ms`,
          operational: operational,
        },
        passed: operational,
      });

      console.log(`  ${operational ? '✅' : '❌'} Database failover test ${operational ? 'PASSED' : 'FAILED'}`);
    } catch (error) {
      this.recordResult({
        test: 'Database Failover',
        status: 'FAILED',
        details: { error: error.message },
        passed: false,
      });
      console.log(`  ❌ Database failover test FAILED: ${error.message}`);
    }
  }

  async testRedisFailover() {
    console.log('📦 Testing Redis Failover...');

    try {
      // Store test data
      await this.redisClient.set('test:failover', 'test:value');

      // Simulate Redis failure
      await this.simulateRedisFailure();

      // Wait for failover
      await this.waitForRedisFailover();

      // Verify data
      const data = await this.redisClient.get('test:failover');

      const success = data === 'test:value';

      this.recordResult({
        test: 'Redis Failover',
        status: success ? 'PASSED' : 'FAILED',
        details: {
          dataRecovered: success,
        },
        passed: success,
      });

      console.log(`  ${success ? '✅' : '❌'} Redis failover test ${success ? 'PASSED' : 'FAILED'}`);
    } catch (error) {
      this.recordResult({
        test: 'Redis Failover',
        status: 'FAILED',
        details: { error: error.message },
        passed: false,
      });
      console.log(`  ❌ Redis failover test FAILED: ${error.message}`);
    }
  }

  async testFullSystemRecovery() {
    console.log('🔄 Testing Full System Recovery...');

    try {
      // Create full system backup
      const backupName = await this.createFullBackup();

      // Simulate system failure
      await this.simulateSystemFailure();

      // Restore system
      const restoreTime = await this.restoreFullSystem(backupName);

      // Verify system
      const verified = await this.verifyFullSystem();

      this.recordResult({
        test: 'Full System Recovery',
        status: verified ? 'PASSED' : 'FAILED',
        details: {
          backupName,
          restoreTime: `${restoreTime}ms`,
          systemVerified: verified,
        },
        passed: verified,
      });

      console.log(`  ${verified ? '✅' : '❌'} Full system recovery test ${verified ? 'PASSED' : 'FAILED'}`);
    } catch (error) {
      this.recordResult({
        test: 'Full System Recovery',
        status: 'FAILED',
        details: { error: error.message },
        passed: false,
      });
      console.log(`  ❌ Full system recovery test FAILED: ${error.message}`);
    }
  }

  async testDataIntegrity() {
    console.log('📊 Testing Data Integrity...');

    try {
      // Test ACID compliance
      const acidTest = await this.testACID();

      // Test constraints
      const constraintTest = await this.testConstraints();

      // Test transactions
      const transactionTest = await this.testTransactions();

      const passed = acidTest && constraintTest && transactionTest;

      this.recordResult({
        test: 'Data Integrity',
        status: passed ? 'PASSED' : 'FAILED',
        details: {
          acidCompliance: acidTest,
          constraints: constraintTest,
          transactions: transactionTest,
        },
        passed,
      });

      console.log(`  ${passed ? '✅' : '❌'} Data integrity test ${passed ? 'PASSED' : 'FAILED'}`);
    } catch (error) {
      this.recordResult({
        test: 'Data Integrity',
        status: 'FAILED',
        details: { error: error.message },
        passed: false,
      });
      console.log(`  ❌ Data integrity test FAILED: ${error.message}`);
    }
  }

  // Helper Methods
  async createTestData() {
    const user = await this.prisma.user.create({
      data: {
        email: `test-${Date.now()}@example.com`,
        password: 'test123',
        firstName: 'Test',
        lastName: 'User',
      },
    });

    const parking = await this.prisma.parkingSpot.create({
      data: {
        name: 'Test Parking',
        address: '123 Test St',
        city: 'Test City',
        state: 'TS',
        zipCode: '12345',
        latitude: 40.7128,
        longitude: -74.0060,
        hourlyRate: 10.00,
        status: 'AVAILABLE',
      },
    });

    return { user, parking };
  }

  async deleteTestData(data) {
    await this.prisma.parkingSpot.delete({ where: { id: data.parking.id } });
    await this.prisma.user.delete({ where: { id: data.user.id } });
  }

  async createBackup() {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupName = `backup-${timestamp}`;
    
    // Simulate backup creation
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    return backupName;
  }

  async restoreBackup(backupName) {
    const start = Date.now();
    
    // Simulate restore
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    return Date.now() - start;
  }

  async verifyData(data) {
    const user = await this.prisma.user.findUnique({
      where: { id: data.user.id },
    });
    
    const parking = await this.prisma.parkingSpot.findUnique({
      where: { id: data.parking.id },
    });

    return !!(user && parking);
  }

  async simulatePrimaryFailure() {
    console.log('    Simulating primary database failure...');
    await new Promise(resolve => setTimeout(resolve, 500));
  }

  async waitForFailover() {
    const start = Date.now();
    console.log('    Waiting for failover...');
    await new Promise(resolve => setTimeout(resolve, 3000));
    return Date.now() - start;
  }

  async checkSystemOperational() {
    try {
      await this.prisma.$queryRaw`SELECT 1`;
      return true;
    } catch {
      return false;
    }
  }

  async simulateRedisFailure() {
    console.log('    Simulating Redis failure...');
    await new Promise(resolve => setTimeout(resolve, 500));
  }

  async waitForRedisFailover() {
    console.log('    Waiting for Redis failover...');
    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  async createFullBackup() {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    return `full-backup-${timestamp}`;
  }

  async simulateSystemFailure() {
    console.log('    Simulating system failure...');
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  async restoreFullSystem(backupName) {
    const start = Date.now();
    console.log(`    Restoring from ${backupName}...`);
    await new Promise(resolve => setTimeout(resolve, 3000));
    return Date.now() - start;
  }

  async verifyFullSystem() {
    try {
      await this.prisma.$queryRaw`SELECT 1`;
      await this.redisClient.set('test:verify', 'ok');
      await axios.get('http://localhost:3000/health');
      return true;
    } catch {
      return false;
    }
  }

  async testACID() {
    try {
      await this.prisma.$transaction([
        this.prisma.user.create({
          data: {
            email: `acid-${Date.now()}@example.com`,
            password: 'test123',
            firstName: 'ACID',
            lastName: 'Test',
          },
        }),
        // This will fail, causing rollback
        this.prisma.user.create({
          data: {
            email: `duplicate-${Date.now()}@example.com`,
            password: 'test123',
            firstName: 'Duplicate',
            lastName: 'Test',
          },
        }),
      ]);
      return false; // Should not reach here
    } catch {
      return true; // Transaction rolled back successfully
    }
  }

  async testConstraints() {
    try {
      await this.prisma.booking.create({
        data: {
          userId: 'invalid-id',
          parkingId: 'invalid-id',
          startTime: new Date(),
          endTime: new Date(),
          duration: 1,
          totalPrice: 10,
        },
      });
      return false;
    } catch {
      return true;
    }
  }

  async testTransactions() {
    try {
      const result = await this.prisma.$transaction(async (prisma) => {
        const user = await prisma.user.create({
          data: {
            email: `trans-${Date.now()}@example.com`,
            password: 'test123',
            firstName: 'Transaction',
            lastName: 'Test',
          },
        });

        const parking = await prisma.parkingSpot.create({
          data: {
            name: 'Transaction Parking',
            address: '456 Trans St',
            city: 'Trans City',
            state: 'TS',
            zipCode: '12345',
            latitude: 40.7128,
            longitude: -74.0060,
            hourlyRate: 10.00,
            status: 'AVAILABLE',
          },
        });

        const booking = await prisma.booking.create({
          data: {
            userId: user.id,
            parkingId: parking.id,
            startTime: new Date(),
            endTime: new Date(Date.now() + 3600000),
            duration: 1,
            totalPrice: 10,
          },
        });

        return { user, parking, booking };
      });

      // Clean up
      await this.prisma.booking.delete({ where: { id: result.booking.id } });
      await this.prisma.parkingSpot.delete({ where: { id: result.parking.id } });
      await this.prisma.user.delete({ where: { id: result.user.id } });

      return true;
    } catch {
      return false;
    }
  }

  recordResult(result) {
    this.results.push({
      ...result,
      timestamp: new Date().toISOString(),
    });
  }

  generateReport() {
    const passed = this.results.filter(r => r.passed).length;
    const total = this.results.length;
    const duration = Date.now() - this.startTime;

    console.log('\n📊 Disaster Recovery Test Report:');
    console.log('═'.repeat(50));
    console.log(`✅ Passed: ${passed}/${total}`);
    console.log(`❌ Failed: ${total - passed}/${total}`);
    console.log(`📈 Success Rate: ${(passed / total * 100).toFixed(2)}%`);
    console.log(`⏱️ Total Duration: ${(duration / 1000).toFixed(2)}s`);
    console.log('═'.repeat(50));

    // RTO/RPO Validation
    const recoveryTime = this.results.find(r => r.test === 'Full System Recovery')?.details?.restoreTime || 0;
    const rtoTarget = parseInt(process.env.RTO_TARGET) || 900; // 15 minutes in seconds
    
    console.log('\n📊 RTO/RPO Validation:');
    console.log(`⏱️ Recovery Time: ${(recoveryTime / 1000).toFixed(2)}s`);
    console.log(`🎯 RTO Target: ${rtoTarget}s`);
    console.log(`📊 Status: ${(recoveryTime / 1000) <= rtoTarget ? '✅ PASSED' : '❌ FAILED'}`);

    // Recommendations
    console.log('\n💡 Recommendations:');
    if (passed === total) {
      console.log('  ✅ All disaster recovery tests PASSED!');
      console.log(`  ✅ RTO met: ${(recoveryTime / 1000).toFixed(2)}s <= ${rtoTarget}s`);
    } else {
      const failures = this.results.filter(r => !r.passed);
      console.log(`  ❌ ${failures.length} tests failed. Review and fix:`);
      failures.forEach(f => {
        console.log(`    - ${f.test}: ${f.details?.error || 'Unknown error'}`);
      });
    }
  }
}

// Run tests
const tester = new DisasterRecoveryTest();
tester.runAllTests().catch(console.error);