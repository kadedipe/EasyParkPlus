// parking-management/backend/tests/unit/test_services/parking/parking-spot.service.test.js
const ParkingSpotService = require('../../../../src/services/parking-spot.service');
const TestDataFactory = require('../helpers/test-data-factory');
const { ParkingSpot, Reservation } = require('../../../../src/models');

describe('ParkingSpotService', () => {
  let parkingSpotService;
  
  beforeEach(() => {
    parkingSpotService = new ParkingSpotService();
  });
  
  describe('createParkingSpot', () => {
    it('should create parking spot successfully', async () => {
      const spotData = TestDataFactory.generateParkingSpot();
      
      const spot = await parkingSpotService.createParkingSpot(spotData);
      
      expect(spot).toBeDefined();
      expect(spot.name).toBe(spotData.name);
      expect(spot.pricePerHour).toBe(spotData.pricePerHour);
      expect(spot.location.coordinates).toEqual(spotData.location.coordinates);
    });
    
    it('should validate unique spot name', async () => {
      const spotData = TestDataFactory.generateParkingSpot({ name: 'UniqueSpot' });
      await ParkingSpot.create(spotData);
      
      await expect(parkingSpotService.createParkingSpot(spotData))
        .rejects
        .toThrow('Parking spot name already exists');
    });
    
    it('should create geospatial index', async () => {
      const spotData = TestDataFactory.generateParkingSpot();
      const spot = await parkingSpotService.createParkingSpot(spotData);
      
      const geoQuery = await ParkingSpot.find({
        location: {
          $near: {
            $geometry: {
              type: 'Point',
              coordinates: spotData.location.coordinates
            },
            $maxDistance: 1000
          }
        }
      });
      
      expect(geoQuery).toContainEqual(expect.objectContaining({ _id: spot._id }));
    });
  });
  
  describe('getNearbySpots', () => {
    beforeEach(async () => {
      // Create spots at different locations
      await ParkingSpot.create(TestDataFactory.generateParkingSpot({
        name: 'Nearby1',
        location: {
          type: 'Point',
          coordinates: [-74.0060, 40.7128]
        }
      }));
      
      await ParkingSpot.create(TestDataFactory.generateParkingSpot({
        name: 'Nearby2',
        location: {
          type: 'Point',
          coordinates: [-74.0070, 40.7130]
        }
      }));
      
      await ParkingSpot.create(TestDataFactory.generateParkingSpot({
        name: 'Far',
        location: {
          type: 'Point',
          coordinates: [-74.1000, 40.8000]
        }
      }));
    });
    
    it('should find nearby spots within radius', async () => {
      const spots = await parkingSpotService.getNearbySpots(-74.0065, 40.7129, 500);
      
      expect(spots).toHaveLength(2);
      expect(spots[0]).toHaveProperty('distance');
      expect(spots[0].distance).toBeLessThan(500);
    });
    
    it('should filter by spot type', async () => {
      const evSpots = await parkingSpotService.getNearbySpots(-74.0065, 40.7129, 1000, {
        type: 'ev'
      });
      
      expect(evSpots.every(spot => spot.type === 'ev')).toBe(true);
    });
    
    it('should filter by price range', async () => {
      const spots = await parkingSpotService.getNearbySpots(-74.0065, 40.7129, 1000, {
        minPrice: 5,
        maxPrice: 15
      });
      
      expect(spots.every(spot => 
        spot.pricePerHour >= 5 && spot.pricePerHour <= 15
      )).toBe(true);
    });
    
    it('should filter by availability', async () => {
      const spots = await parkingSpotService.getNearbySpots(-74.0065, 40.7129, 1000, {
        availableOnly: true
      });
      
      expect(spots.every(spot => spot.status === 'available')).toBe(true);
    });
  });
  
  describe('checkAvailability', () => {
    let spot;
    let startTime;
    let endTime;
    
    beforeEach(async () => {
      spot = await ParkingSpot.create(TestDataFactory.generateParkingSpot());
      startTime = new Date(Date.now() + 3600000);
      endTime = new Date(Date.now() + 7200000);
      
      // Create conflicting reservation
      await Reservation.create(TestDataFactory.generateReservation(
        new mongoose.Types.ObjectId(),
        spot._id,
        { startTime, endTime }
      ));
    });
    
    it('should return false for unavailable time', async () => {
      const isAvailable = await parkingSpotService.checkAvailability(
        spot._id,
        startTime,
        endTime
      );
      
      expect(isAvailable).toBe(false);
    });
    
    it('should return true for available time', async () => {
      const availableStart = new Date(Date.now() + 86400000);
      const availableEnd = new Date(Date.now() + 90000000);
      
      const isAvailable = await parkingSpotService.checkAvailability(
        spot._id,
        availableStart,
        availableEnd
      );
      
      expect(isAvailable).toBe(true);
    });
    
    it('should include buffer time', async () => {
      const nearStart = new Date(startTime.getTime() - 15 * 60 * 1000); // 15 min before
      const nearEnd = new Date(startTime.getTime() + 30 * 60 * 1000);
      
      const isAvailable = await parkingSpotService.checkAvailability(
        spot._id,
        nearStart,
        nearEnd,
        { bufferMinutes: 30 }
      );
      
      expect(isAvailable).toBe(false);
    });
  });
  
  describe('updateSpotStatus', () => {
    let spot;
    
    beforeEach(async () => {
      spot = await ParkingSpot.create(TestDataFactory.generateParkingSpot());
    });
    
    it('should update spot status', async () => {
      const updatedSpot = await parkingSpotService.updateSpotStatus(
        spot._id,
        'maintenance'
      );
      
      expect(updatedSpot.status).toBe('maintenance');
    });
    
    it('should validate status transitions', async () => {
      // Can't go from maintenance directly to occupied
      spot.status = 'maintenance';
      await spot.save();
      
      await expect(parkingSpotService.updateSpotStatus(spot._id, 'occupied'))
        .rejects
        .toThrow('Invalid status transition');
    });
    
    it('should trigger webhook on status change', async () => {
      const webhookSpy = jest.spyOn(parkingSpotService, 'notifyStatusChange');
      
      await parkingSpotService.updateSpotStatus(spot._id, 'occupied');
      
      expect(webhookSpy).toHaveBeenCalled();
    });
  });
  
  describe('getSpotAnalytics', () => {
    let spot;
    
    beforeEach(async () => {
      spot = await ParkingSpot.create(TestDataFactory.generateParkingSpot());
      
      // Create multiple reservations
      for (let i = 0; i < 10; i++) {
        await Reservation.create(TestDataFactory.generateReservation(
          new mongoose.Types.ObjectId(),
          spot._id,
          {
            startTime: new Date(Date.now() + i * 86400000),
            endTime: new Date(Date.now() + (i + 1) * 86400000),
            status: 'confirmed'
          }
        ));
      }
    });
    
    it('should calculate utilization rate', async () => {
      const analytics = await parkingSpotService.getSpotAnalytics(spot._id, 30);
      
      expect(analytics).toHaveProperty('utilizationRate');
      expect(analytics.utilizationRate).toBeGreaterThanOrEqual(0);
      expect(analytics.utilizationRate).toBeLessThanOrEqual(100);
    });
    
    it('should calculate revenue', async () => {
      const analytics = await parkingSpotService.getSpotAnalytics(spot._id, 30);
      
      expect(analytics).toHaveProperty('totalRevenue');
      expect(analytics.totalRevenue).toBeGreaterThan(0);
    });
    
    it('should identify peak hours', async () => {
      const analytics = await parkingSpotService.getSpotAnalytics(spot._id, 30);
      
      expect(analytics).toHaveProperty('peakHours');
      expect(analytics.peakHours).toBeInstanceOf(Array);
    });
  });
});