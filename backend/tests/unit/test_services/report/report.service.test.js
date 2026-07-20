// parking-management/backend/tests/unit/test_services/report/report.service.test.js
const ReportService = require('../../../../src/services/report.service');
const TestDataFactory = require('../helpers/test-data-factory');
const { Reservation, Payment, ParkingSpot, User } = require('../../../../src/models');

describe('ReportService', () => {
  let reportService;
  
  beforeEach(() => {
    reportService = new ReportService();
  });
  
  describe('generateRevenueReport', () => {
    beforeEach(async () => {
      // Create test data for last 30 days
      for (let i = 0; i < 30; i++) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        
        await Payment.create({
          reservationId: new mongoose.Types.ObjectId(),
          amount: Math.random() * 100 + 10,
          method: ['credit_card', 'paypal'][i % 2],
          status: 'completed',
          createdAt: date
        });
      }
    });
    
    it('should generate daily revenue report', async () => {
      const report = await reportService.generateRevenueReport({
        period: 'daily',
        days: 7
      });
      
      expect(report).toHaveProperty('data');
      expect(report).toHaveProperty('summary');
      expect(report.data).toHaveLength(7);
      expect(report.summary).toHaveProperty('totalRevenue');
      expect(report.summary).toHaveProperty('averageDailyRevenue');
      expect(report.summary).toHaveProperty('peakDay');
    });
    
    it('should generate monthly revenue report', async () => {
      const report = await reportService.generateRevenueReport({
        period: 'monthly',
        year: 2024
      });
      
      expect(report.data).toHaveLength(12);
      expect(report.summary).toHaveProperty('totalRevenue');
      expect(report.summary).toHaveProperty('bestMonth');
    });
    
    it('should filter by payment method', async () => {
      const report = await reportService.generateRevenueReport({
        period: 'daily',
        days: 7,
        paymentMethod: 'credit_card'
      });
      
      expect(report.summary.paymentMethodBreakdown).toHaveProperty('credit_card');
    });
  });
  
  describe('generateOccupancyReport', () => {
    let spots;
    
    beforeEach(async () => {
      spots = await Promise.all(
        Array(5).fill().map(() => ParkingSpot.create(TestDataFactory.generateParkingSpot()))
      );
      
      // Create reservations for past 7 days
      for (let i = 0; i < 7; i++) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        
        for (const spot of spots) {
          await Reservation.create(
            TestDataFactory.generateReservation(
              new mongoose.Types.ObjectId(),
              spot._id,
              {
                startTime: new Date(date.setHours(9, 0, 0)),
                endTime: new Date(date.setHours(17, 0, 0)),
                status: 'confirmed'
              }
            )
          );
        }
      }
    });
    
    it('should generate occupancy report', async () => {
      const report = await reportService.generateOccupancyReport({
        days: 7
      });
      
      expect(report).toHaveProperty('data');
      expect(report).toHaveProperty('summary');
      expect(report.summary).toHaveProperty('averageOccupancy');
      expect(report.summary).toHaveProperty('peakHour');
      expect(report.summary).toHaveProperty('peakDay');
    });
    
    it('should calculate hourly occupancy', async () => {
      const report = await reportService.generateOccupancyReport({
        days: 7,
        granularity: 'hourly'
      });
      
      expect(report.data[0]).toHaveProperty('hourly');
      expect(report.data[0].hourly).toHaveLength(24);
    });
    
    it('should filter by spot type', async () => {
      const report = await reportService.generateOccupancyReport({
        days: 7,
        spotType: 'ev'
      });
      
      const evSpots = spots.filter(s => s.type === 'ev');
      expect(report.summary.totalSpots).toBe(evSpots.length);
    });
  });
  
  describe('generateUserActivityReport', () => {
    beforeEach(async () => {
      // Create users with different activity levels
      for (let i = 0; i < 20; i++) {
        const user = await User.create(TestDataFactory.generateUser());
        
        // Create reservations for each user
        const reservationCount = Math.floor(Math.random() * 10);
        for (let j = 0; j < reservationCount; j++) {
          await Reservation.create(
            TestDataFactory.generateReservation(user._id, new mongoose.Types.ObjectId())
          );
        }
      }
    });
    
    it('should generate user activity report', async () => {
      const report = await reportService.generateUserActivityReport();
      
      expect(report).toHaveProperty('data');
      expect(report).toHaveProperty('summary');
      expect(report.summary).toHaveProperty('totalUsers');
      expect(report.summary).toHaveProperty('activeUsers');
      expect(report.summary).toHaveProperty('averageReservationsPerUser');
    });
    
    it('should segment users by activity level', async () => {
      const report = await reportService.generateUserActivityReport({
        segments: ['inactive', 'occasional', 'frequent', 'power']
      });
      
      expect(report.segments).toBeDefined();
      expect(report.segments).toHaveLength(4);
      expect(report.segments[0]).toHaveProperty('count');
      expect(report.segments[0]).toHaveProperty('percentage');
    });
    
    it('should calculate retention metrics', async () => {
      const report = await reportService.generateUserActivityReport({
        includeRetention: true
      });
      
      expect(report).toHaveProperty('retention');
      expect(report.retention).toHaveProperty('day1');
      expect(report.retention).toHaveProperty('day7');
      expect(report.retention).toHaveProperty('day30');
    });
  });
  
  describe('generateMaintenanceReport', () => {
    let spots;
    
    beforeEach(async () => {
      spots = await Promise.all(
        Array(10).fill().map(() => ParkingSpot.create(TestDataFactory.generateParkingSpot()))
      );
      
      // Mark some spots as maintenance
      for (let i = 0; i < 3; i++) {
        spots[i].status = 'maintenance';
        spots[i].maintenanceHistory = [{
          startDate: new Date(Date.now() - 7 * 86400000),
          endDate: new Date(),
          reason: 'Regular maintenance',
          technician: 'John Doe'
        }];
        await spots[i].save();
      }
    });
    
    it('should generate maintenance report', async () => {
      const report = await reportService.generateMaintenanceReport();
      
      expect(report).toHaveProperty('data');
      expect(report).toHaveProperty('summary');
      expect(report.summary).toHaveProperty('totalSpots');
      expect(report.summary).toHaveProperty('underMaintenance');
      expect(report.summary).toHaveProperty('averageMaintenanceDuration');
    });
    
    it('should list spots requiring maintenance', async () => {
      const report = await reportService.generateMaintenanceReport({
        includePending: true
      });
      
      expect(report).toHaveProperty('pendingMaintenance');
      expect(report.pendingMaintenance).toBeDefined();
    });
    
    it('should calculate maintenance costs', async () => {
      const report = await reportService.generateMaintenanceReport({
        includeCosts: true
      });
      
      expect(report.summary).toHaveProperty('totalMaintenanceCost');
      expect(report.summary).toHaveProperty('averageCostPerSpot');
    });
  });
  
  describe('exportReport', () => {
    let reportData;
    
    beforeEach(async () => {
      reportData = {
        title: 'Test Report',
        data: [
          { date: '2024-01-01', revenue: 1000, reservations: 10 },
          { date: '2024-01-02', revenue: 1500, reservations: 15 },
          { date: '2024-01-03', revenue: 1200, reservations: 12 }
        ]
      };
    });
    
    it('should export to CSV', async () => {
      const csv = await reportService.exportReport(reportData, 'csv');
      
      expect(csv).toContain('date,revenue,reservations');
      expect(csv).toContain('2024-01-01,1000,10');
      expect(csv).toContain('2024-01-02,1500,15');
    });
    
    it('should export to JSON', async () => {
      const json = await reportService.exportReport(reportData, 'json');
      const parsed = JSON.parse(json);
      
      expect(parsed).toHaveProperty('title', 'Test Report');
      expect(parsed).toHaveProperty('data');
      expect(parsed.data).toHaveLength(3);
    });
    
    it('should export to Excel', async () => {
      const excelBuffer = await reportService.exportReport(reportData, 'excel');
      
      expect(excelBuffer).toBeInstanceOf(Buffer);
      expect(excelBuffer.length).toBeGreaterThan(0);
    });
    
    it('should apply formatting options', async () => {
      const csv = await reportService.exportReport(reportData, 'csv', {
        formatNumbers: true,
        includeHeader: true
      });
      
      expect(csv).toContain('date,revenue,reservations');
      expect(csv).toContain('$1,000.00');
    });
  });
});