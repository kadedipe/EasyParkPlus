// parking-management/backend/src/scripts/performance-test.js
import { performance } from 'perf_hooks';
import { dbManager } from '../config/database.js';

class PerformanceTester {
  constructor() {
    this.results = [];
    this.thresholds = {
      queryTime: 100, // milliseconds
      throughput: 1000, // queries per second
      errorRate: 0.01, // 1%
    };
  }

  /**
   * Run performance tests
   */
  async runTests() {
    console.log('🚀 Starting Database Performance Tests...\n');
    
    const tests = [
      this.testBasicQueries.bind(this),
      this.testComplexQueries.bind(this),
      this.testConcurrentQueries.bind(this),
      this.testBulkOperations.bind(this),
      this.testAggregationQueries.bind(this),
    ];

    for (const test of tests) {
      await this.runTest(test);
    }

    this.printReport();
    await dbManager.disconnect();
  }

  /**
   * Run a single test
   */
  async runTest(testFn) {
    const start = performance.now();
    let success = true;
    let error = null;
    
    try {
      await testFn();
    } catch (err) {
      success = false;
      error = err.message;
    }
    
    const duration = performance.now() - start;
    
    this.results.push({
      name: testFn.name,
      duration,
      success,
      error,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Test basic queries
   */
  async testBasicQueries() {
    console.log('📊 Testing basic queries...');
    
    const operations = [
      { name: 'Find users', query: () => dbManager.primaryClient.user.findMany({ take: 10 }) },
      { name: 'Find parking spots', query: () => dbManager.primaryClient.parkingSpot.findMany({ take: 10 }) },
      { name: 'Find bookings', query: () => dbManager.primaryClient.booking.findMany({ take: 10 }) },
      { name: 'Find payments', query: () => dbManager.primaryClient.payment.findMany({ take: 10 }) },
    ];

    const results = [];
    
    for (const op of operations) {
      const start = performance.now();
      await op.query();
      const duration = performance.now() - start;
      results.push({ ...op, duration });
      
      console.log(`  ${op.name}: ${duration.toFixed(2)}ms`);
      
      if (duration > this.thresholds.queryTime) {
        console.warn(`  ⚠️ Query exceeded threshold (${this.thresholds.queryTime}ms)`);
      }
    }
    
    const avgDuration = results.reduce((sum, r) => sum + r.duration, 0) / results.length;
    console.log(`  Average: ${avgDuration.toFixed(2)}ms\n`);
    
    return results;
  }

  /**
   * Test complex queries
   */
  async testComplexQueries() {
    console.log('🔍 Testing complex queries...');
    
    const operations = [
      {
        name: 'Search with joins',
        query: () => dbManager.primaryClient.parkingSpot.findMany({
          where: {
            status: 'AVAILABLE',
          },
          include: {
            bookings: {
              where: { status: 'CONFIRMED' },
              take: 5,
            },
            reviews: {
              take: 10,
              orderBy: { createdAt: 'desc' },
            },
          },
          take: 20,
        }),
      },
      {
        name: 'Aggregate with group by',
        query: () => dbManager.primaryClient.$queryRaw`
          SELECT 
            status,
            COUNT(*) as count,
            AVG(hourly_rate) as avg_rate
          FROM parking_spots
          GROUP BY status
        `,
      },
      {
        name: 'Date range search',
        query: () => dbManager.primaryClient.booking.findMany({
          where: {
            startTime: {
              gte: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
              lte: new Date(),
            },
          },
          include: {
            user: true,
            parkingSpot: true,
          },
          take: 50,
        }),
      },
    ];

    const results = [];
    
    for (const op of operations) {
      const start = performance.now();
      await op.query();
      const duration = performance.now() - start;
      results.push({ ...op, duration });
      
      console.log(`  ${op.name}: ${duration.toFixed(2)}ms`);
    }
    
    const avgDuration = results.reduce((sum, r) => sum + r.duration, 0) / results.length;
    console.log(`  Average: ${avgDuration.toFixed(2)}ms\n`);
    
    return results;
  }

  /**
   * Test concurrent queries
   */
  async testConcurrentQueries() {
    console.log('🔄 Testing concurrent queries...');
    
    const concurrencyLevels = [5, 10, 20, 50];
    const results = [];

    for (const level of concurrencyLevels) {
      const start = performance.now();
      
      const promises = Array(level).fill().map(() => 
        dbManager.primaryClient.parkingSpot.findMany({
          where: { status: 'AVAILABLE' },
          take: 10,
        })
      );
      
      await Promise.all(promises);
      const duration = performance.now() - start;
      
      const throughput = (level / (duration / 1000)).toFixed(2);
      results.push({ concurrency: level, duration, throughput });
      
      console.log(`  ${level} concurrent queries: ${duration.toFixed(2)}ms (${throughput} req/s)`);
    }
    
    console.log(`  Average throughput: ${(results.reduce((sum, r) => sum + parseFloat(r.throughput), 0) / results.length).toFixed(2)} req/s\n`);
    
    return results;
  }

  /**
   * Test bulk operations
   */
  async testBulkOperations() {
    console.log('📦 Testing bulk operations...');
    
    const bulkSizes = [10, 50, 100, 500];
    const results = [];

    for (const size of bulkSizes) {
      const start = performance.now();
      
      // Create bulk records
      const data = Array(size).fill().map((_, i) => ({
        name: `Test Spot ${i}`,
        address: `${i} Test Street`,
        city: 'Test City',
        state: 'TS',
        zipCode: '12345',
        latitude: 40.7128 + (i * 0.0001),
        longitude: -74.0060 + (i * 0.0001),
        hourlyRate: 10 + (i % 5),
        status: 'AVAILABLE',
        features: ['EV_CHARGING', 'SECURE_CAMERA'],
        images: ['test.jpg'],
      }));
      
      await dbManager.primaryClient.parkingSpot.createMany({
        data,
      });
      
      const duration = performance.now() - start;
      const rate = (size / (duration / 1000)).toFixed(2);
      results.push({ size, duration, rate });
      
      console.log(`  ${size} records: ${duration.toFixed(2)}ms (${rate} records/s)`);
      
      // Clean up
      await dbManager.primaryClient.parkingSpot.deleteMany({
        where: {
          name: {
            startsWith: 'Test Spot',
          },
        },
      });
    }
    
    console.log(`  Average rate: ${(results.reduce((sum, r) => sum + parseFloat(r.rate), 0) / results.length).toFixed(2)} records/s\n`);
    
    return results;
  }

  /**
   * Test aggregation queries
   */
  async testAggregationQueries() {
    console.log('📊 Testing aggregation queries...');
    
    const operations = [
      {
        name: 'Revenue by day',
        query: () => dbManager.primaryClient.$queryRaw`
          SELECT 
            DATE(start_time) as day,
            SUM(total_price) as revenue,
            COUNT(*) as bookings
          FROM bookings
          WHERE status = 'COMPLETED'
          GROUP BY DATE(start_time)
          ORDER BY day DESC
          LIMIT 30
        `,
      },
      {
        name: 'Average price by city',
        query: () => dbManager.primaryClient.$queryRaw`
          SELECT 
            city,
            AVG(hourly_rate) as avg_rate,
            COUNT(*) as spot_count
          FROM parking_spots
          GROUP BY city
          ORDER BY spot_count DESC
          LIMIT 10
        `,
      },
      {
        name: 'Booking trends by hour',
        query: () => dbManager.primaryClient.$queryRaw`
          SELECT 
            EXTRACT(HOUR FROM start_time) as hour,
            COUNT(*) as bookings
          FROM bookings
          GROUP BY EXTRACT(HOUR FROM start_time)
          ORDER BY hour
        `,
      },
    ];

    const results = [];
    
    for (const op of operations) {
      const start = performance.now();
      await op.query();
      const duration = performance.now() - start;
      results.push({ ...op, duration });
      
      console.log(`  ${op.name}: ${duration.toFixed(2)}ms`);
    }
    
    const avgDuration = results.reduce((sum, r) => sum + r.duration, 0) / results.length;
    console.log(`  Average: ${avgDuration.toFixed(2)}ms\n`);
    
    return results;
  }

  /**
   * Print test report
   */
  printReport() {
    console.log('\n📈 Performance Test Report');
    console.log('═'.repeat(50));
    
    const successful = this.results.filter(r => r.success);
    const failed = this.results.filter(r => !r.success);
    
    console.log(`Tests: ${this.results.length}`);
    console.log(`✅ Passed: ${successful.length}`);
    console.log(`❌ Failed: ${failed.length}`);
    
    if (failed.length > 0) {
      console.log('\nFailed Tests:');
      failed.forEach(f => {
        console.log(`  ✗ ${f.name}: ${f.error}`);
      });
    }
    
    const avgDuration = successful.reduce((sum, r) => sum + r.duration, 0) / successful.length;
    console.log(`\nAverage duration: ${avgDuration.toFixed(2)}ms`);
    
    // Print recommendations
    console.log('\n💡 Recommendations:');
    if (avgDuration > 100) {
      console.log('  - Consider adding indexes to frequently queried fields');
    }
    if (this.results.some(r => r.duration > 1000)) {
      console.log('  - Optimize slow queries or add caching');
    }
    if (this.results.some(r => r.name?.includes('Concurrent') && parseFloat(r.throughput) < 100)) {
      console.log('  - Consider implementing connection pooling');
    }
    
    console.log('═'.repeat(50));
  }
}

// Run tests
const tester = new PerformanceTester();
tester.runTests().catch(console.error);