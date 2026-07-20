// parking-management/backend/tests/unit/test_services/reservation/reservation.service.test.js
const ReservationService = require('../../../../src/services/reservation.service');
const ParkingSpotService = require('../../../../src/services/parking-spot.service');
const PaymentService = require('../../../../src/services/payment.service');
const NotificationService = require('../../../../src/services/notification.service');
const TestDataFactory = require('../helpers/test-data-factory');
const { Reservation, ParkingSpot } = require('../../../../src/models');

describe('ReservationService', () => {
  let reservationService;
  let parkingSpotService;
  let paymentService;
  let notificationService;
  
  beforeEach(() => {
    parkingSpotService = new ParkingSpotService();
    paymentService = new PaymentService();
    notificationService = new NotificationService();
    reservationService = new ReservationService(
      parkingSpotService,
      paymentService,
      notificationService
    );
  });
  
  describe('createReservation', () => {
    let spot;
    let userId;
    
    beforeEach(async () => {
      spot = await ParkingSpot.create(TestDataFactory.generateParkingSpot());
      userId = new mongoose.Types.ObjectId();
    });
    
    it('should create reservation successfully', async () => {
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 7200000);
      
      const reservationData = {
        spotId: spot._id,
        userId,
        startTime,
        endTime,
        vehicleNumber: 'ABC123'
      };
      
      const reservation = await reservationService.createReservation(reservationData);
      
      expect(reservation).toBeDefined();
      expect(reservation.userId.toString()).toBe(userId.toString());
      expect(reservation.spotId.toString()).toBe(spot._id.toString());
      expect(reservation.status).toBe('confirmed');
      expect(reservation.totalAmount).toBeGreaterThan(0);
      
      // Verify spot status updated
      const updatedSpot = await ParkingSpot.findById(spot._id);
      expect(updatedSpot.status).toBe('occupied');
    });
    
    it('should calculate total amount correctly', async () => {
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 10800000); // 3 hours
      const expectedAmount = spot.pricePerHour * 3;
      
      const reservation = await reservationService.createReservation({
        spotId: spot._id,
        userId,
        startTime,
        endTime,
        vehicleNumber: 'ABC123'
      });
      
      expect(reservation.totalAmount).toBe(expectedAmount);
    });
    
    it('should apply promo code discount', async () => {
      const promoCode = {
        code: 'TEST10',
        type: 'percentage',
        value: 10
      };
      
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 7200000);
      
      const reservation = await reservationService.createReservation({
        spotId: spot._id,
        userId,
        startTime,
        endTime,
        vehicleNumber: 'ABC123',
        promoCode: promoCode.code
      });
      
      const originalAmount = spot.pricePerHour * 2;
      const expectedAmount = originalAmount * 0.9;
      
      expect(reservation.totalAmount).toBe(expectedAmount);
      expect(reservation.discountApplied).toBe(10);
    });
    
    it('should prevent overlapping reservations', async () => {
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 7200000);
      
      // Create first reservation
      await reservationService.createReservation({
        spotId: spot._id,
        userId,
        startTime,
        endTime,
        vehicleNumber: 'ABC123'
      });
      
      // Try to create overlapping reservation
      await expect(reservationService.createReservation({
        spotId: spot._id,
        userId,
        startTime: new Date(startTime.getTime() + 1800000),
        endTime: new Date(endTime.getTime() + 1800000),
        vehicleNumber: 'XYZ789'
      })).rejects.toThrow('Spot already reserved for this time');
    });
    
    it('should validate time constraints', async () => {
      const pastStart = new Date(Date.now() - 3600000);
      const futureEnd = new Date(Date.now() + 3600000);
      
      await expect(reservationService.createReservation({
        spotId: spot._id,
        userId,
        startTime: pastStart,
        endTime: futureEnd,
        vehicleNumber: 'ABC123'
      })).rejects.toThrow('Start time must be in the future');
    });
    
    it('should send confirmation notification', async () => {
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 7200000);
      
      await reservationService.createReservation({
        spotId: spot._id,
        userId,
        startTime,
        endTime,
        vehicleNumber: 'ABC123'
      });
      
      expect(notificationService.sendReservationConfirmation).toHaveBeenCalled();
    });
  });
  
  describe('cancelReservation', () => {
    let reservation;
    let spot;
    
    beforeEach(async () => {
      spot = await ParkingSpot.create(TestDataFactory.generateParkingSpot());
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 7200000);
      
      reservation = await Reservation.create(
        TestDataFactory.generateReservation(
          new mongoose.Types.ObjectId(),
          spot._id,
          { startTime, endTime, status: 'confirmed' }
        )
      );
    });
    
    it('should cancel reservation successfully', async () => {
      const cancelledReservation = await reservationService.cancelReservation(reservation._id);
      
      expect(cancelledReservation.status).toBe('cancelled');
      expect(cancelledReservation.cancelledAt).toBeDefined();
      
      // Verify spot status updated
      const updatedSpot = await ParkingSpot.findById(spot._id);
      expect(updatedSpot.status).toBe('available');
    });
    
    it('should process refund if payment exists', async () => {
      // Create payment for reservation
      await paymentService.processPayment({
        reservationId: reservation._id,
        amount: reservation.totalAmount,
        method: 'credit_card'
      });
      
      await reservationService.cancelReservation(reservation._id);
      
      expect(paymentService.refundPayment).toHaveBeenCalled();
    });
    
    it('should apply cancellation fee if applicable', async () => {
      const nearStart = new Date(Date.now() + 1800000); // 30 minutes from now
      reservation.startTime = nearStart;
      await reservation.save();
      
      const cancelledReservation = await reservationService.cancelReservation(reservation._id);
      
      expect(cancelledReservation.cancellationFee).toBeGreaterThan(0);
      expect(cancelledReservation.refundAmount).toBeLessThan(reservation.totalAmount);
    });
    
    it('should not cancel past reservations', async () => {
      reservation.startTime = new Date(Date.now() - 7200000);
      reservation.endTime = new Date(Date.now() - 3600000);
      await reservation.save();
      
      await expect(reservationService.cancelReservation(reservation._id))
        .rejects
        .toThrow('Cannot cancel past reservation');
    });
  });
  
  describe('extendReservation', () => {
    let reservation;
    let spot;
    
    beforeEach(async () => {
      spot = await ParkingSpot.create(TestDataFactory.generateParkingSpot());
      const startTime = new Date(Date.now() + 3600000);
      const endTime = new Date(Date.now() + 7200000);
      
      reservation = await Reservation.create(
        TestDataFactory.generateReservation(
          new mongoose.Types.ObjectId(),
          spot._id,
          { startTime, endTime }
        )
      );
    });
    
    it('should extend reservation successfully', async () => {
      const newEndTime = new Date(Date.now() + 10800000); // 3 hours from now
      
      const extendedReservation = await reservationService.extendReservation(
        reservation._id,
        newEndTime
      );
      
      expect(extendedReservation.endTime.getTime()).toBe(newEndTime.getTime());
      expect(extendedReservation.totalAmount).toBeGreaterThan(reservation.totalAmount);
      expect(extendedReservation.additionalCharge).toBeDefined();
    });
    
    it('should calculate additional cost', async () => {
      const originalAmount = reservation.totalAmount;
      const newEndTime = new Date(Date.now() + 10800000);
      
      const extendedReservation = await reservationService.extendReservation(
        reservation._id,
        newEndTime
      );
      
      const additionalHours = 1;
      const expectedAdditional = spot.pricePerHour * additionalHours;
      const expectedTotal = originalAmount + expectedAdditional;
      
      expect(extendedReservation.additionalCharge).toBe(expectedAdditional);
      expect(extendedReservation.totalAmount).toBe(expectedTotal);
    });
    
    it('should check spot availability for extension', async () => {
      // Create conflicting reservation
      const conflictingStart = new Date(Date.now() + 5400000);
      const conflictingEnd = new Date(Date.now() + 9000000);
      
      await Reservation.create(
        TestDataFactory.generateReservation(
          new mongoose.Types.ObjectId(),
          spot._id,
          { startTime: conflictingStart, endTime: conflictingEnd }
        )
      );
      
      const newEndTime = new Date(Date.now() + 10800000);
      
      await expect(reservationService.extendReservation(reservation._id, newEndTime))
        .rejects
        .toThrow('Spot not available for extension');
    });
  });
  
  describe('getUserReservations', () => {
    let userId;
    
    beforeEach(async () => {
      userId = new mongoose.Types.ObjectId();
      const spot = await ParkingSpot.create(TestDataFactory.generateParkingSpot());
      
      // Create multiple reservations
      for (let i = 0; i < 5; i++) {
        await Reservation.create(
          TestDataFactory.generateReservation(userId, spot._id, {
            startTime: new Date(Date.now() + i * 86400000),
            endTime: new Date(Date.now() + (i + 1) * 86400000)
          })
        );
      }
    });
    
    it('should get user reservations with pagination', async () => {
      const result = await reservationService.getUserReservations(userId, {
        page: 1,
        limit: 2
      });
      
      expect(result).toHaveProperty('reservations');
      expect(result).toHaveProperty('pagination');
      expect(result.reservations).toHaveLength(2);
      expect(result.pagination.total).toBe(5);
    });
    
    it('should filter by status', async () => {
      const result = await reservationService.getUserReservations(userId, {
        status: 'confirmed'
      });
      
      expect(result.reservations.every(r => r.status === 'confirmed')).toBe(true);
    });
    
    it('should filter by date range', async () => {
      const startDate = new Date();
      startDate.setHours(0, 0, 0, 0);
      const endDate = new Date();
      endDate.setDate(endDate.getDate() + 2);
      
      const result = await reservationService.getUserReservations(userId, {
        startDate,
        endDate
      });
      
      expect(result.reservations.length).toBeLessThan(5);
    });
  });
});