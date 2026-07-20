// parking-management/backend/tests/unit/test_api/reservations/reservations.test.js
const APIClient = require('../helpers/api-client');
const TestDataGenerator = require('../helpers/test-data');
const { Reservation, ParkingSpot } = require('../../../../src/models');
const mongoose = require('mongoose');

describe('Reservation API', () => {
  let apiClient;
  let testUser;
  let testAdmin;
  let testSpot;
  
  beforeEach(async () => {
    apiClient = new APIClient();
    
    // Create regular user
    const userData = TestDataGenerator.generateUser();
    const userResponse = await apiClient.register(userData);
    testUser = {
      id: userResponse.body.data.user._id,
      token: userResponse.body.data.token,
      email: userData.email
    };
    
    // Create admin user
    const adminData = TestDataGenerator.generateAdmin();
    const adminResponse = await apiClient.register(adminData);
    testAdmin = {
      id: adminResponse.body.data.user._id,
      token: adminResponse.body.data.token
    };
    
    apiClient.setAuthToken(testUser.token);
    
    // Create test parking spot
    const spotData = TestDataGenerator.generateParkingSpot();
    apiClient.setAdminToken(testAdmin.token);
    const spotResponse = await apiClient.createParkingSpot(spotData);
    testSpot = spotResponse.body.data;
    apiClient.setAuthToken(testUser.token);
  });
  
  describe('POST /api/reservations', () => {
    it('should create a reservation', async () => {
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 7200000);
      
      const reservationData = {
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123',
        vehicleType: 'sedan'
      };
      
      const response = await apiClient.createReservation(reservationData);
      
      expect(response.status).toBe(201);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body.data).toHaveProperty('userId', testUser.id);
      expect(response.body.data).toHaveProperty('spotId', testSpot._id);
      expect(response.body.data).toHaveProperty('status', 'confirmed');
      expect(response.body.data).toHaveProperty('totalAmount');
      expect(response.body.data.totalAmount).toBeGreaterThan(0);
      
      // Verify spot status changed
      const spot = await ParkingSpot.findById(testSpot._id);
      expect(spot.status).toBe('occupied');
    });
    
    it('should calculate total amount correctly', async () => {
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 10800000); // 3 hours
      const expectedAmount = testSpot.pricePerHour * 3;
      
      const response = await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123'
      });
      
      expect(response.body.data.totalAmount).toBe(expectedAmount);
    });
    
    it('should apply promo code discount', async () => {
      // Create promo code (in reality, would be in database)
      const promoCode = 'WELCOME10';
      
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 7200000);
      
      const response = await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123',
        promoCode
      });
      
      const originalAmount = testSpot.pricePerHour * 2;
      const discountedAmount = originalAmount * 0.9;
      expect(response.body.data.totalAmount).toBe(discountedAmount);
      expect(response.body.data).toHaveProperty('discountApplied', 10);
    });
    
    it('should not allow overlapping reservations', async () => {
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 7200000);
      
      // Create first reservation
      await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123'
      });
      
      // Try to create overlapping reservation
      const overlappingStart = new Date(startTime.getTime() + 1800000);
      const overlappingEnd = new Date(endTime.getTime() + 1800000);
      
      const response = await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: overlappingStart.toISOString(),
        endTime: overlappingEnd.toISOString(),
        vehicleNumber: 'XYZ789'
      });
      
      expect(response.status).toBe(409);
      expect(response.body).toHaveProperty('message', 'Spot already reserved for this time');
    });
    
    it('should validate start time is in future', async () => {
      const startTime = new Date(Date.now() - 3600000);
      const endTime = new Date(Date.now() + 3600000);
      
      const response = await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123'
      });
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Start time must be in the future');
    });
    
    it('should validate end time after start time', async () => {
      const startTime = new Date(Date.now() + 7200000);
      const endTime = new Date(Date.now() + 3600000);
      
      const response = await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123'
      });
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'End time must be after start time');
    });
    
    it('should enforce maximum reservation duration', async () => {
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 86400000 * 8); // 8 days
      
      const response = await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123'
      });
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Maximum reservation duration is 7 days');
    });
    
    it('should validate vehicle number format', async () => {
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 7200000);
      
      const response = await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'INVALID'
      });
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('errors');
    });
  });
  
  describe('GET /api/reservations', () => {
    beforeEach(async () => {
      // Create multiple reservations
      const startTime1 = new Date(Date.now() + 3600000);
      const endTime1 = new Date(Date.now() + 7200000);
      
      const startTime2 = new Date(Date.now() + 86400000);
      const endTime2 = new Date(Date.now() + 90000000);
      
      await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: startTime1.toISOString(),
        endTime: endTime1.toISOString(),
        vehicleNumber: 'ABC123'
      });
      
      await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: startTime2.toISOString(),
        endTime: endTime2.toISOString(),
        vehicleNumber: 'XYZ789'
      });
    });
    
    it('should list user reservations', async () => {
      const response = await apiClient.getReservations();
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body.data).toHaveProperty('reservations');
      expect(response.body.data.reservations).toHaveLength(2);
      expect(response.body.data).toHaveProperty('pagination');
    });
    
    it('should filter by status', async () => {
      // Create cancelled reservation
      const startTime = new Date(Date.now() + 172800000);
      const endTime = new Date(Date.now() + 176400000);
      
      const response = await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'DEF456'
      });
      
      await apiClient.cancelReservation(response.body.data._id);
      
      const filteredResponse = await apiClient.getReservations({ status: 'cancelled' });
      
      expect(filteredResponse.status).toBe(200);
      expect(filteredResponse.body.data.reservations.every(r => r.status === 'cancelled')).toBe(true);
    });
    
    it('should filter by date range', async () => {
      const startDate = new Date();
      startDate.setHours(0, 0, 0, 0);
      
      const endDate = new Date();
      endDate.setDate(endDate.getDate() + 1);
      endDate.setHours(23, 59, 59, 999);
      
      const response = await apiClient.getReservations({
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString()
      });
      
      expect(response.status).toBe(200);
      expect(response.body.data.reservations).toHaveLength(1);
    });
    
    it('should filter by spot', async () => {
      const newSpot = await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot());
      
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 7200000);
      
      await apiClient.createReservation({
        spotId: newSpot.body.data._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'NEW123'
      });
      
      const response = await apiClient.getReservations({ spotId: newSpot.body.data._id });
      
      expect(response.status).toBe(200);
      expect(response.body.data.reservations).toHaveLength(1);
      expect(response.body.data.reservations[0].spotId).toBe(newSpot.body.data._id);
    });
    
    it('should sort reservations', async () => {
      const response = await apiClient.getReservations({
        sortBy: 'startTime',
        sortOrder: 'desc'
      });
      
      const dates = response.body.data.reservations.map(r => new Date(r.startTime));
      expect(dates).toEqual([...dates].sort((a, b) => b - a));
    });
  });
  
  describe('GET /api/reservations/:id', () => {
    let reservation;
    
    beforeEach(async () => {
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 7200000);
      
      const response = await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123'
      });
      
      reservation = response.body.data;
    });
    
    it('should get reservation by id', async () => {
      const response = await apiClient.getReservationById(reservation._id);
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('_id', reservation._id);
      expect(response.body.data).toHaveProperty('spotId', testSpot._id);
      expect(response.body.data).toHaveProperty('vehicleNumber', 'ABC123');
      expect(response.body.data).toHaveProperty('spot');
      expect(response.body.data.spot).toHaveProperty('name');
    });
    
    it('should return 403 for other user reservation', async () => {
      const { token } = await apiClient.register(TestDataGenerator.generateUser());
      apiClient.setAuthToken(token);
      
      const response = await apiClient.getReservationById(reservation._id);
      
      expect(response.status).toBe(403);
    });
    
    it('should return 404 for non-existent reservation', async () => {
      const nonExistentId = new mongoose.Types.ObjectId();
      const response = await apiClient.getReservationById(nonExistentId);
      
      expect(response.status).toBe(404);
    });
    
    it('should include payment details if available', async () => {
      // Create payment for reservation
      const paymentData = {
        reservationId: reservation._id,
        amount: reservation.totalAmount,
        method: 'credit_card'
      };
      
      await apiClient.processPayment(paymentData);
      
      const response = await apiClient.getReservationById(reservation._id);
      
      expect(response.body.data).toHaveProperty('payment');
      expect(response.body.data.payment).toHaveProperty('status', 'completed');
    });
  });
  
  describe('PUT /api/reservations/:id/cancel', () => {
    let reservation;
    
    beforeEach(async () => {
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 7200000);
      
      const response = await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123'
      });
      
      reservation = response.body.data;
    });
    
    it('should cancel reservation', async () => {
      const response = await apiClient.cancelReservation(reservation._id);
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('status', 'cancelled');
      expect(response.body.data).toHaveProperty('cancelledAt');
      
      // Verify spot status updated
      const spot = await ParkingSpot.findById(testSpot._id);
      expect(spot.status).toBe('available');
    });
    
    it('should process refund if payment was made', async () => {
      // Create payment
      const paymentData = {
        reservationId: reservation._id,
        amount: reservation.totalAmount,
        method: 'credit_card'
      };
      
      await apiClient.processPayment(paymentData);
      
      const response = await apiClient.cancelReservation(reservation._id);
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('refund');
      expect(response.body.data.refund).toHaveProperty('amount', reservation.totalAmount);
      expect(response.body.data.refund).toHaveProperty('status', 'completed');
    });
    
    it('should not cancel past reservations', async () => {
      const pastReservation = await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: new Date(Date.now() - 7200000).toISOString(),
        endTime: new Date(Date.now() - 3600000).toISOString(),
        vehicleNumber: 'PAST123'
      });
      
      const response = await apiClient.cancelReservation(pastReservation.body.data._id);
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Cannot cancel past reservation');
    });
    
    it('should not cancel already cancelled reservation', async () => {
      await apiClient.cancelReservation(reservation._id);
      const response = await apiClient.cancelReservation(reservation._id);
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Reservation already cancelled');
    });
    
    it('should allow cancellation within allowed window', async () => {
      const nearStartTime = new Date(Date.now() + 900000); // 15 minutes from now
      const endTime = new Date(Date.now() + 4500000);
      
      const nearReservation = await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: nearStartTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'NEAR123'
      });
      
      const response = await apiClient.cancelReservation(nearReservation.body.data._id);
      
      expect(response.status).toBe(200);
    });
  });
  
  describe('PUT /api/reservations/:id/extend', () => {
    let reservation;
    
    beforeEach(async () => {
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 7200000);
      
      const response = await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123'
      });
      
      reservation = response.body.data;
    });
    
    it('should extend reservation', async () => {
      const newEndTime = new Date(Date.now() + 10800000); // 3 hours from now
      
      const response = await apiClient.extendReservation(reservation._id, newEndTime.toISOString());
      
      expect(response.status).toBe(200);
      expect(new Date(response.body.data.endTime).getTime()).toBe(newEndTime.getTime());
      expect(response.body.data.totalAmount).toBeGreaterThan(reservation.totalAmount);
    });
    
    it('should calculate additional cost', async () => {
      const originalAmount = reservation.totalAmount;
      const newEndTime = new Date(Date.now() + 10800000);
      
      const response = await apiClient.extendReservation(reservation._id, newEndTime.toISOString());
      
      const additionalHours = 1; // 3 hours total - 2 hours original = 1 hour
      const expectedAdditional = testSpot.pricePerHour * additionalHours;
      const expectedTotal = originalAmount + expectedAdditional;
      
      expect(response.body.data.totalAmount).toBe(expectedTotal);
      expect(response.body.data).toHaveProperty('additionalCharge', expectedAdditional);
    });
    
    it('should validate new end time', async () => {
      const newEndTime = new Date(Date.now() - 3600000); // Past time
      
      const response = await apiClient.extendReservation(reservation._id, newEndTime.toISOString());
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'New end time must be in the future');
    });
    
    it('should check spot availability for extension', async () => {
      // Create another reservation that overlaps with extension
      const conflictingStart = new Date(Date.now() + 5400000); // 1.5 hours
      const conflictingEnd = new Date(Date.now() + 9000000); // 2.5 hours
      
      const anotherUser = await apiClient.register(TestDataGenerator.generateUser());
      apiClient.setAuthToken(anotherUser.body.data.token);
      
      await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: conflictingStart.toISOString(),
        endTime: conflictingEnd.toISOString(),
        vehicleNumber: 'CONFLICT'
      });
      
      apiClient.setAuthToken(testUser.token);
      const newEndTime = new Date(Date.now() + 10800000); // 3 hours
      
      const response = await apiClient.extendReservation(reservation._id, newEndTime.toISOString());
      
      expect(response.status).toBe(409);
      expect(response.body).toHaveProperty('message', 'Spot not available for requested extension');
    });
    
    it('should enforce maximum duration limit', async () => {
      const newEndTime = new Date(Date.now() + 86400000 * 8); // 8 days
      
      const response = await apiClient.extendReservation(reservation._id, newEndTime.toISOString());
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Extension would exceed maximum reservation duration');
    });
  });
});