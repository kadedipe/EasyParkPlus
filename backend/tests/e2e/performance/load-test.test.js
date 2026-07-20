// parking-management/backend/tests/e2e/performance/load-test.test.js
const E2EClient = require('../helpers/e2e-client');
const TestDataFactory = require('../helpers/test-data-factory');

describe('Performance and Load Tests', () => {
  let adminClient;
  let testSpot;
  
  beforeAll(async () => {
    adminClient = new E2EClient();
    const adminData = TestDataFactory.generateUser({ role: 'admin' });
    await adminClient.register(adminData);
    
    // Create test spots
    const spotPromises = [];
    for (let i = 0; i < 10; i++) {
      spotPromises.push(
        adminClient.createParkingSpot(TestDataFactory.generateParkingSpot())
      );
    }
    const spots = await Promise.all(spotPromises);
    testSpot = spots[0];
  });
  
  describe('API Response Times', () => {
    it('should respond within acceptable time limits', async () => {
      const endpoints = [
        { method: 'GET', url: '/api/parking-spots' },
        { method: 'GET', url: `/api/parking-spots/${testSpot._id}` },
        { method: 'GET', url: '/api/auth/health' }
      ];
      
      for (const endpoint of endpoints) {
        const startTime = Date.now();
        
        let response;
        if (endpoint.method === 'GET') {
          response = await adminClient.get(endpoint.url);
        }
        
        const duration = Date.now() - startTime;
        
        expect(response.status).toBeLessThan(500);
        expect(duration).toBeLessThan(100); // 100ms max
        console.log(`${endpoint.method} ${endpoint.url}: ${duration}ms`);
      }
    });
    
    it('should handle concurrent requests efficiently', async () => {
      const numRequests = 50;
      const requestPromises = [];
      
      const startTime = Date.now();
      
      for (let i = 0; i < numRequests; i++) {
        requestPromises.push(
          adminClient.getParkingSpots({
            lat: 40.7128,
            lng: -74.0060,
            radius: 1000
          })
        );
      }
      
      const responses = await Promise.all(requestPromises);
      const duration = Date.now() - startTime;
      
      const successCount = responses.filter(r => r.status === 200).length;
      expect(successCount).toBe(numRequests);
      expect(duration).toBeLessThan(5000); // 5 seconds max for 50 requests
      
      const avgResponseTime = duration / numRequests;
      console.log(`Average response time for ${numRequests} concurrent requests: ${avgResponseTime}ms`);
      expect(avgResponseTime).toBeLessThan(100);
    });
  });
  
  describe('Database Performance', () => {
    it('should handle bulk insert efficiently', async () => {
      const numReservations = 100;
      const startTime = Date.now();
      
      const client = new E2EClient();
      const userData = TestDataFactory.generateUser();
      await client.register(userData);
      
      const reservationPromises = [];
      for (let i = 0; i < numReservations; i++) {
        const startTime = new Date(Date.now() + (i + 1) * 3600000);
        const endTime = new Date(startTime.getTime() + 3600000);
        
        reservationPromises.push(
          client.createReservation({
            spotId: testSpot._id,
            startTime: startTime.toISOString(),
            endTime: endTime.toISOString(),
            vehicleNumber: `BULK${i}`
          })
        );
      }
      
      const responses = await Promise.all(reservationPromises);
      const duration = Date.now() - startTime;
      
      const successCount = responses.filter(r => r.status === 201).length;
      expect(successCount).toBe(numReservations);
      expect(duration).toBeLessThan(10000); // 10 seconds max
      
      const avgInsertTime = duration / numReservations;
      console.log(`Average insert time for ${numReservations} reservations: ${avgInsertTime}ms`);
    });
    
    it('should handle complex queries efficiently', async () => {
      const complexQueries = [
        { status: 'available', type: 'ev', minPrice: 10, maxPrice: 20 },
        { status: 'occupied', amenities: ['security', 'cctv'] },
        { search: 'downtown', sortBy: 'pricePerHour', sortOrder: 'asc' },
        { nearby: true, lat: 40.7128, lng: -74.0060, radius: 500 }
      ];
      
      for (const query of complexQueries) {
        const startTime = Date.now();
        
        const response = await adminClient.getParkingSpots(query);
        const duration = Date.now() - startTime;
        
        expect(response.status).toBe(200);
        expect(duration).toBeLessThan(200); // 200ms max for complex queries
        
        console.log(`Complex query ${JSON.stringify(query)}: ${duration}ms`);
      }
    });
  });
  
  describe('Caching Performance', () => {
    it('should cache frequently accessed data', async () => {
      const spotId = testSpot._id;
      
      // First request (should cache)
      const firstRequest = Date.now();
      await adminClient.getParkingSpotById(spotId);
      const firstDuration = Date.now() - firstRequest;
      
      // Second request (should be cached)
      const secondRequest = Date.now();
      await adminClient.getParkingSpotById(spotId);
      const secondDuration = Date.now() - secondRequest;
      
      // Cached response should be faster
      expect(secondDuration).toBeLessThan(firstDuration);
      
      console.log(`First request: ${firstDuration}ms, Cached request: ${secondDuration}ms`);
      expect(secondDuration).toBeLessThan(firstDuration * 0.5); // At least 50% faster
    });
    
    it('should invalidate cache on updates', async () => {
      const spotId = testSpot._id;
      
      // Cache the spot
      await adminClient.getParkingSpotById(spotId);
      
      // Update the spot (should invalidate cache)
      await adminClient.updateParkingSpot(spotId, { pricePerHour: 99.99 });
      
      // Request after update (should not be cached)
      const startTime = Date.now();
      await adminClient.getParkingSpotById(spotId);
      const duration = Date.now() - startTime;
      
      // Should take longer than cached request
      expect(duration).toBeGreaterThan(10);
    });
  });
});