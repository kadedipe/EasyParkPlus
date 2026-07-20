// parking-management/backend/tests/e2e/parking/parking-workflow.test.js
const E2EClient = require('../helpers/e2e-client');
const TestDataFactory = require('../helpers/test-data-factory');

describe('Parking Spot E2E Workflow', () => {
  let client;
  let adminClient;
  let testUser;
  
  beforeEach(async () => {
    client = new E2EClient();
    adminClient = new E2EClient();
    
    // Create admin user
    const adminData = TestDataFactory.generateUser({ role: 'admin' });
    await adminClient.register(adminData);
    
    // Create regular user
    const userData = TestDataFactory.generateUser();
    const registerResponse = await client.register(userData);
    testUser = registerResponse.body.data.user;
  });
  
  describe('Complete Parking Spot Management Flow', () => {
    let createdSpot;
    
    it('should create, manage, and delete parking spots', async () => {
      // Step 1: Admin creates parking spot
      const spotData = TestDataFactory.generateParkingSpot();
      const createResponse = await adminClient.createParkingSpot(spotData);
      
      expect(createResponse.status).toBe(201);
      expect(createResponse.body.data).toHaveProperty('name', spotData.name);
      expect(createResponse.body.data).toHaveProperty('pricePerHour', spotData.pricePerHour);
      
      createdSpot = createResponse.body.data;
      
      // Step 2: User searches for parking spots
      const searchResponse = await client.getParkingSpots({
        search: spotData.name,
        status: 'available'
      });
      
      expect(searchResponse.status).toBe(200);
      expect(searchResponse.body.data.spots.length).toBeGreaterThan(0);
      
      // Step 3: User gets spot details
      const spotDetails = await client.getParkingSpotById(createdSpot._id);
      
      expect(spotDetails.status).toBe(200);
      expect(spotDetails.body.data).toHaveProperty('name', spotData.name);
      expect(spotDetails.body.data).toHaveProperty('availability');
      
      // Step 4: Admin updates spot information
      const updates = {
        pricePerHour: 25.50,
        status: 'maintenance',
        amenities: ['security', 'cctv', 'lighting']
      };
      
      const updateResponse = await adminClient.updateParkingSpot(createdSpot._id, updates);
      
      expect(updateResponse.status).toBe(200);
      expect(updateResponse.body.data).toHaveProperty('pricePerHour', updates.pricePerHour);
      expect(updateResponse.body.data).toHaveProperty('status', updates.status);
      
      // Step 5: Admin deletes spot
      const deleteResponse = await adminClient.deleteParkingSpot(createdSpot._id);
      
      expect(deleteResponse.status).toBe(200);
      
      // Step 6: Verify spot is deleted
      const getResponse = await client.getParkingSpotById(createdSpot._id);
      expect(getResponse.status).toBe(404);
    });
    
    it('should find nearby spots', async () => {
      // Step 1: Create multiple spots at different locations
      const spot1 = await adminClient.createParkingSpot(
        TestDataFactory.generateParkingSpot({
          location: { latitude: 40.7128, longitude: -74.0060 }
        })
      );
      
      const spot2 = await adminClient.createParkingSpot(
        TestDataFactory.generateParkingSpot({
          location: { latitude: 40.7130, longitude: -74.0062 }
        })
      );
      
      const spot3 = await adminClient.createParkingSpot(
        TestDataFactory.generateParkingSpot({
          location: { latitude: 40.8000, longitude: -74.1000 }
        })
      );
      
      // Step 2: Search nearby spots
      const nearbyResponse = await client.getParkingSpots({
        lat: 40.7129,
        lng: -74.0061,
        radius: 500
      });
      
      expect(nearbyResponse.status).toBe(200);
      expect(nearbyResponse.body.data.spots.length).toBe(2);
      
      // Step 3: Verify distance calculation
      expect(nearbyResponse.body.data.spots[0]).toHaveProperty('distance');
      expect(nearbyResponse.body.data.spots[0].distance).toBeLessThan(500);
    });
    
    it('should filter spots by availability for date range', async () => {
      // Step 1: Create spot
      const spot = await adminClient.createParkingSpot(
        TestDataFactory.generateParkingSpot()
      );
      
      // Step 2: Create reservation
      const startTime = new Date(Date.now() + 86400000); // tomorrow
      const endTime = new Date(Date.now() + 90000000);
      
      await client.createReservation({
        spotId: spot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123'
      });
      
      // Step 3: Check availability for that time
      const availabilityCheck = await client.getParkingSpotById(spot._id, {
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString()
      });
      
      expect(availabilityCheck.body.data.availability.isAvailable).toBe(false);
      
      // Step 4: Check availability for different time
      const differentTime = await client.getParkingSpotById(spot._id, {
        startTime: new Date(Date.now() + 172800000).toISOString(),
        endTime: new Date(Date.now() + 176400000).toISOString()
      });
      
      expect(differentTime.body.data.availability.isAvailable).toBe(true);
    });
  });
});