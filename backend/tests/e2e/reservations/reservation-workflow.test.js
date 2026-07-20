// parking-management/backend/tests/e2e/reservations/reservation-workflow.test.js
const E2EClient = require('../helpers/e2e-client');
const TestDataFactory = require('../helpers/test-data-factory');
const { Reservation } = require('../../../../src/models');

describe('Reservation E2E Workflow', () => {
  let client;
  let adminClient;
  let testSpot;
  let testUser;
  
  beforeEach(async () => {
    client = new E2EClient();
    adminClient = new E2EClient();
    
    // Create admin
    const adminData = TestDataFactory.generateUser({ role: 'admin' });
    await adminClient.register(adminData);
    
    // Create regular user
    const userData = TestDataFactory.generateUser();
    const registerResponse = await client.register(userData);
    testUser = registerResponse.body.data.user;
    
    // Create test parking spot
    const spotData = TestDataFactory.generateParkingSpot();
    const spotResponse = await adminClient.createParkingSpot(spotData);
    testSpot = spotResponse.body.data;
  });
  
  describe('Complete Reservation Lifecycle', () => {
    let createdReservation;
    
    it('should create, manage, and complete reservation', async () => {
      // Step 1: User creates reservation
      const startTime = new Date(Date.now() + 86400000); // tomorrow
      const endTime = new Date(Date.now() + 90000000);
      
      const reservationData = {
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123',
        vehicleType: 'sedan'
      };
      
      const createResponse = await client.createReservation(reservationData);
      
      expect(createResponse.status).toBe(201);
      expect(createResponse.body.data).toHaveProperty('status', 'confirmed');
      expect(createResponse.body.data).toHaveProperty('totalAmount');
      expect(createResponse.body.data.spotId).toBe(testSpot._id);
      
      createdReservation = createResponse.body.data;
      
      // Step 2: User views all reservations
      const reservationsList = await client.getReservations();
      
      expect(reservationsList.status).toBe(200);
      expect(reservationsList.body.data.reservations.length).toBeGreaterThan(0);
      
      // Step 3: User views specific reservation
      const reservationDetails = await client.getReservationById(createdReservation._id);
      
      expect(reservationDetails.status).toBe(200);
      expect(reservationDetails.body.data).toHaveProperty('vehicleNumber', 'ABC123');
      expect(reservationDetails.body.data).toHaveProperty('spot');
      expect(reservationDetails.body.data.spot).toHaveProperty('name', testSpot.name);
      
      // Step 4: User extends reservation
      const newEndTime = new Date(endTime.getTime() + 3600000); // +1 hour
      const extendResponse = await client.extendReservation(
        createdReservation._id,
        newEndTime.toISOString()
      );
      
      expect(extendResponse.status).toBe(200);
      expect(new Date(extendResponse.body.data.endTime).getTime()).toBe(newEndTime.getTime());
      expect(extendResponse.body.data.totalAmount).toBeGreaterThan(createdReservation.totalAmount);
      
      // Step 5: User cancels reservation
      const cancelResponse = await client.cancelReservation(createdReservation._id);
      
      expect(cancelResponse.status).toBe(200);
      expect(cancelResponse.body.data).toHaveProperty('status', 'cancelled');
      expect(cancelResponse.body.data).toHaveProperty('cancelledAt');
      
      // Step 6: Verify spot is available again
      const spotStatus = await client.getParkingSpotById(testSpot._id);
      expect(spotStatus.body.data.status).toBe('available');
    });
    
    it('should prevent overlapping reservations', async () => {
      const startTime = new Date(Date.now() + 86400000);
      const endTime = new Date(Date.now() + 90000000);
      
      // Step 1: Create first reservation
      const firstReservation = await client.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123'
      });
      
      expect(firstReservation.status).toBe(201);
      
      // Step 2: Try to create overlapping reservation
      const overlappingStart = new Date(startTime.getTime() + 1800000);
      const overlappingEnd = new Date(endTime.getTime() + 1800000);
      
      const secondReservation = await client.createReservation({
        spotId: testSpot._id,
        startTime: overlappingStart.toISOString(),
        endTime: overlappingEnd.toISOString(),
        vehicleNumber: 'XYZ789'
      });
      
      expect(secondReservation.status).toBe(409);
      expect(secondReservation.body).toHaveProperty('message', 'Spot already reserved for this time');
    });
    
    it('should handle reservation reminders', async () => {
      // Step 1: Create reservation for near future
      const startTime = new Date(Date.now() + 3600000); // 1 hour from now
      const endTime = new Date(Date.now() + 7200000);
      
      const reservation = await client.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123'
      });
      
      expect(reservation.status).toBe(201);
      
      // Step 2: Wait for reminder job
      await client.wait(5000);
      
      // Step 3: Check notifications
      const notifications = await client.getUserNotifications();
      expect(notifications.body.data.notifications).toContainEqual(
        expect.objectContaining({
          type: 'reservation_reminder',
          title: expect.stringContaining('Upcoming Reservation')
        })
      );
    });
  });
});