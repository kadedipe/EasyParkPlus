// parking-management/backend/tests/unit/test_api/parking/parking-spots.test.js
const APIClient = require('../helpers/api-client');
const TestDataGenerator = require('../helpers/test-data');
const { ParkingSpot, Reservation } = require('../../../../src/models');
const mongoose = require('mongoose');

describe('Parking Spot API', () => {
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
      token: userResponse.body.data.token
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
  
  describe('GET /api/parking-spots', () => {
    it('should list all parking spots', async () => {
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot());
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot());
      
      const response = await apiClient.getParkingSpots();
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body.data).toHaveProperty('spots');
      expect(response.body.data.spots.length).toBeGreaterThanOrEqual(3);
      expect(response.body.data).toHaveProperty('pagination');
    });
    
    it('should filter by status', async () => {
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot({ status: 'occupied' }));
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot({ status: 'maintenance' }));
      
      const response = await apiClient.getParkingSpots({ status: 'available' });
      
      expect(response.status).toBe(200);
      expect(response.body.data.spots.every(spot => spot.status === 'available')).toBe(true);
    });
    
    it('should filter by type', async () => {
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot({ type: 'ev' }));
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot({ type: 'disabled' }));
      
      const response = await apiClient.getParkingSpots({ type: 'ev' });
      
      expect(response.status).toBe(200);
      expect(response.body.data.spots.every(spot => spot.type === 'ev')).toBe(true);
    });
    
    it('should search by name or address', async () => {
      const uniqueName = `UNIQUE_${Date.now()}`;
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot({ name: uniqueName }));
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot({
        location: { address: uniqueName }
      }));
      
      const response = await apiClient.getParkingSpots({ search: uniqueName });
      
      expect(response.status).toBe(200);
      expect(response.body.data.spots.length).toBe(2);
    });
    
    it('should filter by price range', async () => {
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot({ pricePerHour: 5 }));
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot({ pricePerHour: 25 }));
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot({ pricePerHour: 15 }));
      
      const response = await apiClient.getParkingSpots({
        minPrice: 10,
        maxPrice: 20
      });
      
      expect(response.status).toBe(200);
      expect(response.body.data.spots.every(spot => 
        spot.pricePerHour >= 10 && spot.pricePerHour <= 20
      )).toBe(true);
    });
    
    it('should filter by amenities', async () => {
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot({
        amenities: ['security', 'cctv']
      }));
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot({
        amenities: ['ev_charger']
      }));
      
      const response = await apiClient.getParkingSpots({ amenities: ['security', 'cctv'] });
      
      expect(response.status).toBe(200);
      expect(response.body.data.spots.every(spot => 
        spot.amenities.includes('security') && spot.amenities.includes('cctv')
      )).toBe(true);
    });
    
    it('should sort results', async () => {
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot({ pricePerHour: 5 }));
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot({ pricePerHour: 30 }));
      
      const response = await apiClient.getParkingSpots({
        sortBy: 'pricePerHour',
        sortOrder: 'asc'
      });
      
      const prices = response.body.data.spots.map(s => s.pricePerHour);
      expect(prices).toEqual([...prices].sort((a, b) => a - b));
    });
    
    it('should support pagination', async () => {
      const response = await apiClient.getParkingSpots({
        page: 1,
        limit: 2
      });
      
      expect(response.body.data.spots.length).toBeLessThanOrEqual(2);
      expect(response.body.data.pagination).toHaveProperty('page', 1);
      expect(response.body.data.pagination).toHaveProperty('limit', 2);
    });
  });
  
  describe('GET /api/parking-spots/nearby', () => {
    it('should find nearby spots', async () => {
      const centerLat = 40.7128;
      const centerLng = -74.0060;
      
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot({
        location: { latitude: centerLat + 0.001, longitude: centerLng + 0.001 }
      }));
      
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot({
        location: { latitude: centerLat + 0.1, longitude: centerLng + 0.1 }
      }));
      
      const response = await apiClient.getNearbySpots(centerLat, centerLng, 500);
      
      expect(response.status).toBe(200);
      expect(response.body.data.spots).toHaveLength(1);
      expect(response.body.data.spots[0]).toHaveProperty('distance');
      expect(response.body.data.spots[0].distance).toBeLessThan(500);
    });
    
    it('should validate coordinates', async () => {
      const response = await apiClient.getNearbySpots('invalid', -74.0060, 1000);
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('errors');
    });
    
    it('should handle no spots found', async () => {
      const response = await apiClient.getNearbySpots(0, 0, 1);
      
      expect(response.status).toBe(200);
      expect(response.body.data.spots).toHaveLength(0);
    });
  });
  
  describe('GET /api/parking-spots/:id', () => {
    it('should get parking spot by id', async () => {
      const response = await apiClient.getParkingSpotById(testSpot._id);
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('_id', testSpot._id);
      expect(response.body.data).toHaveProperty('name', testSpot.name);
      expect(response.body.data).toHaveProperty('pricePerHour', testSpot.pricePerHour);
      expect(response.body.data).toHaveProperty('location');
    });
    
    it('should return 404 for non-existent spot', async () => {
      const nonExistentId = new mongoose.Types.ObjectId();
      const response = await apiClient.getParkingSpotById(nonExistentId);
      
      expect(response.status).toBe(404);
    });
    
    it('should include availability for time range', async () => {
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 7200000);
      
      const response = await apiClient.getParkingSpotById(testSpot._id, {
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString()
      });
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('availability');
      expect(response.body.data.availability).toHaveProperty('isAvailable');
      expect(response.body.data.availability).toHaveProperty('upcomingReservations');
    });
    
    it('should return availability false for reserved time', async () => {
      // Create reservation for the spot
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 7200000);
      
      await apiClient.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123'
      });
      
      const response = await apiClient.getParkingSpotById(testSpot._id, {
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString()
      });
      
      expect(response.body.data.availability.isAvailable).toBe(false);
      expect(response.body.data.availability).toHaveProperty('conflictingReservations');
    });
  });
  
  describe('POST /api/parking-spots', () => {
    beforeEach(() => {
      apiClient.setAdminToken(testAdmin.token);
    });
    
    it('should create new parking spot as admin', async () => {
      const spotData = TestDataGenerator.generateParkingSpot();
      
      const response = await apiClient.createParkingSpot(spotData);
      
      expect(response.status).toBe(201);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body.data).toHaveProperty('name', spotData.name);
      expect(response.body.data).toHaveProperty('pricePerHour', spotData.pricePerHour);
      expect(response.body.data).toHaveProperty('location');
      
      // Verify database
      const spot = await ParkingSpot.findById(response.body.data._id);
      expect(spot).toBeTruthy();
    });
    
    it('should validate required fields', async () => {
      const response = await apiClient.createParkingSpot({ name: 'Invalid' });
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('errors');
    });
    
    it('should enforce unique spot name', async () => {
      const spotData = TestDataGenerator.generateParkingSpot({ name: 'UniqueSpot' });
      await apiClient.createParkingSpot(spotData);
      
      const response = await apiClient.createParkingSpot(spotData);
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Parking spot name already exists');
    });
    
    it('should return 403 for non-admin users', async () => {
      apiClient.setAuthToken(testUser.token);
      const spotData = TestDataGenerator.generateParkingSpot();
      
      const response = await apiClient.createParkingSpot(spotData);
      
      expect(response.status).toBe(403);
    });
  });
  
  describe('PUT /api/parking-spots/:id', () => {
    beforeEach(() => {
      apiClient.setAdminToken(testAdmin.token);
    });
    
    it('should update parking spot as admin', async () => {
      const updates = {
        pricePerHour: 25.50,
        status: 'maintenance',
        amenities: ['security', 'cctv', 'lighting']
      };
      
      const response = await apiClient.updateParkingSpot(testSpot._id, updates);
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('pricePerHour', updates.pricePerHour);
      expect(response.body.data).toHaveProperty('status', updates.status);
      expect(response.body.data.amenities).toEqual(expect.arrayContaining(updates.amenities));
      
      // Verify database
      const spot = await ParkingSpot.findById(testSpot._id);
      expect(spot.pricePerHour).toBe(updates.pricePerHour);
    });
    
    it('should update location partially', async () => {
      const updates = {
        location: {
          address: 'New Address, New York, NY'
        }
      };
      
      const response = await apiClient.updateParkingSpot(testSpot._id, updates);
      
      expect(response.status).toBe(200);
      expect(response.body.data.location).toHaveProperty('address', updates.location.address);
      expect(response.body.data.location).toHaveProperty('latitude', testSpot.location.latitude);
    });
    
    it('should return 403 for non-admin users', async () => {
      apiClient.setAuthToken(testUser.token);
      const response = await apiClient.updateParkingSpot(testSpot._id, { pricePerHour: 30 });
      
      expect(response.status).toBe(403);
    });
    
    it('should return 404 for non-existent spot', async () => {
      const nonExistentId = new mongoose.Types.ObjectId();
      const response = await apiClient.updateParkingSpot(nonExistentId, { pricePerHour: 30 });
      
      expect(response.status).toBe(404);
    });
  });
  
  describe('DELETE /api/parking-spots/:id', () => {
    let spotToDelete;
    
    beforeEach(async () => {
      apiClient.setAdminToken(testAdmin.token);
      const spotData = TestDataGenerator.generateParkingSpot();
      const response = await apiClient.createParkingSpot(spotData);
      spotToDelete = response.body.data;
    });
    
    it('should delete parking spot as admin', async () => {
      const response = await apiClient.deleteParkingSpot(spotToDelete._id);
      
      expect(response.status).toBe(200);
      
      const deletedSpot = await ParkingSpot.findById(spotToDelete._id);
      expect(deletedSpot).toBeNull();
    });
    
    it('should not delete spot with active reservations', async () => {
      // Create reservation for the spot
      apiClient.setAuthToken(testUser.token);
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 7200000);
      
      await apiClient.createReservation({
        spotId: spotToDelete._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123'
      });
      
      apiClient.setAdminToken(testAdmin.token);
      const response = await apiClient.deleteParkingSpot(spotToDelete._id);
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Cannot delete spot with active reservations');
      
      // Spot should still exist
      const spot = await ParkingSpot.findById(spotToDelete._id);
      expect(spot).toBeTruthy();
    });
    
    it('should return 403 for non-admin users', async () => {
      apiClient.setAuthToken(testUser.token);
      const response = await apiClient.deleteParkingSpot(spotToDelete._id);
      
      expect(response.status).toBe(403);
    });
  });
});