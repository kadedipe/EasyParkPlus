// parking-management/backend/tests/e2e/errors/error-recovery.test.js
const E2EClient = require('../helpers/e2e-client');
const TestDataFactory = require('../helpers/test-data-factory');

describe('Error Handling and Recovery', () => {
  let client;
  let adminClient;
  let testSpot;
  
  beforeAll(async () => {
    adminClient = new E2EClient();
    const adminData = TestDataFactory.generateUser({ role: 'admin' });
    await adminClient.register(adminData);
    
    const spotData = TestDataFactory.generateParkingSpot();
    const spotResponse = await adminClient.createParkingSpot(spotData);
    testSpot = spotResponse.body.data;
  });
  
  beforeEach(async () => {
    client = new E2EClient();
    const userData = TestDataFactory.generateUser();
    await client.register(userData);
  });
  
  describe('Validation Errors', () => {
    it('should return proper validation errors', async () => {
      // Invalid email format
      const invalidEmail = await client.register(
        TestDataFactory.generateUser({ email: 'invalid-email' })
      );
      expect(invalidEmail.status).toBe(400);
      expect(invalidEmail.body.errors).toContainEqual(
        expect.objectContaining({ field: 'email' })
      );
      
      // Invalid reservation time
      const startTime = new Date(Date.now() - 86400000); // past date
      const endTime = new Date(Date.now() - 7200000);
      
      const invalidReservation = await client.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123'
      });
      
      expect(invalidReservation.status).toBe(400);
      expect(invalidReservation.body).toHaveProperty('message');
    });
    
    it('should handle malformed requests gracefully', async () => {
      const malformedRequests = [
        { method: 'POST', url: '/api/auth/login', body: { email: 'test@test.com' } }, // missing password
        { method: 'POST', url: '/api/reservations', body: { spotId: testSpot._id } }, // missing times
        { method: 'PUT', url: `/api/parking-spots/${testSpot._id}`, body: { invalid: 'data' } }
      ];
      
      for (const request of malformedRequests) {
        let response;
        if (request.method === 'POST') {
          response = await adminClient.post(request.url, request.body);
        } else if (request.method === 'PUT') {
          response = await adminClient.put(request.url, request.body);
        }
        
        expect(response.status).toBe(400);
        expect(response.body).toHaveProperty('errors');
      }
    });
  });
  
  describe('Rate Limiting', () => {
    it('should enforce rate limits', async () => {
      const requests = [];
      const numRequests = 100;
      
      // Make many rapid requests
      for (let i = 0; i < numRequests; i++) {
        requests.push(client.getParkingSpots());
      }
      
      const responses = await Promise.all(requests);
      const rateLimited = responses.filter(r => r.status === 429);
      
      expect(rateLimited.length).toBeGreaterThan(0);
      console.log(`${rateLimited.length} requests were rate limited`);
      
      // Check rate limit headers
      const rateLimitResponse = responses.find(r => r.headers['x-ratelimit-limit']);
      if (rateLimitResponse) {
        expect(rateLimitResponse.headers['x-ratelimit-limit']).toBeDefined();
        expect(rateLimitResponse.headers['x-ratelimit-remaining']).toBeDefined();
        expect(rateLimitResponse.headers['x-ratelimit-reset']).toBeDefined();
      }
    });
    
    it('should recover after rate limit window', async () => {
      // Trigger rate limit
      for (let i = 0; i < 60; i++) {
        await client.getParkingSpots();
      }
      
      // Wait for rate limit window
      await client.wait(60000);
      
      // Should work again
      const response = await client.getParkingSpots();
      expect(response.status).toBe(200);
    });
  });
  
  describe('Database Connection Recovery', () => {
    it('should handle database disconnection and reconnect', async () {
      const mongoose = require('mongoose');
      
      // Simulate database disconnection
      await mongoose.disconnect();
      
      // Attempt request (should fail gracefully)
      const response = await client.getParkingSpots();
      expect(response.status).toBe(503);
      expect(response.body).toHaveProperty('message', 'Service temporarily unavailable');
      
      // Reconnect
      await mongoose.connect(process.env.MONGODB_URI);
      
      // Wait for connection to stabilize
      await client.wait(1000);
      
      // Should work again
      const recoveryResponse = await client.getParkingSpots();
      expect(recoveryResponse.status).toBe(200);
    });
  });
  
  describe('Transaction Rollback', () => {
    it('should rollback failed transactions', async () => {
      // Attempt to create reservation with invalid payment
      const startTime = new Date(Date.now() + 86400000);
      const endTime = new Date(startTime.getTime() + 7200000);
      
      const reservation = await client.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123'
      });
      
      // Attempt payment that will fail
      const failedPayment = await client.processPayment({
        reservationId: reservation.body.data._id,
        amount: reservation.body.data.totalAmount,
        method: 'credit_card',
        cardDetails: {
          number: '4000000000000002', // Declined card
          expiry: '12/25',
          cvv: '123'
        }
      });
      
      expect(failedPayment.status).toBe(402);
      
      // Reservation should still be pending payment
      const reservationStatus = await client.getReservationById(reservation.body.data._id);
      expect(reservationStatus.body.data.paymentStatus).toBe('pending');
      
      // Spot should still be reserved
      const spotStatus = await client.getParkingSpotById(testSpot._id);
      expect(spotStatus.body.data.status).toBe('occupied');
    });
  });
  
  describe('Idempotency', () => {
    it('should handle duplicate requests idempotently', async () => {
      const idempotencyKey = `idem_${Date.now()}`;
      
      const startTime = new Date(Date.now() + 86400000);
      const endTime = new Date(startTime.getTime() + 7200000);
      
      // First request
      const firstResponse = await client.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123',
        idempotencyKey
      });
      
      // Duplicate request with same key
      const duplicateResponse = await client.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123',
        idempotencyKey
      });
      
      expect(firstResponse.body.data._id).toBe(duplicateResponse.body.data._id);
      expect(duplicateResponse.status).toBe(200); // Should return existing
      
      // Only one reservation should exist
      const reservations = await client.getReservations();
      const matchingReservations = reservations.body.data.reservations.filter(
        r => r._id === firstResponse.body.data._id
      );
      expect(matchingReservations).toHaveLength(1);
    });
  });
});