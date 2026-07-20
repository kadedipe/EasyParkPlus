// parking-management/backend/tests/e2e/admin/admin-operations.test.js
const E2EClient = require('../helpers/e2e-client');
const TestDataFactory = require('../helpers/test-data-factory');

describe('Admin Operations E2E', () => {
  let adminClient;
  let userClient;
  let testSpot;
  
  beforeEach(async () => {
    adminClient = new E2EClient();
    userClient = new E2EClient();
    
    // Create admin user
    const adminData = TestDataFactory.generateUser({ role: 'admin' });
    await adminClient.register(adminData);
    
    // Create regular user
    const userData = TestDataFactory.generateUser();
    await userClient.register(userData);
    
    // Create test parking spot
    const spotData = TestDataFactory.generateParkingSpot();
    const spotResponse = await adminClient.createParkingSpot(spotData);
    testSpot = spotResponse.body.data;
  });
  
  describe('Admin Dashboard and Reports', () => {
    it('should access dashboard with statistics', async () => {
      // Step 1: Create multiple users, reservations, and payments
      for (let i = 0; i < 5; i++) {
        const tempClient = new E2EClient();
        const userData = TestDataFactory.generateUser();
        await tempClient.register(userData);
        
        const startTime = new Date(Date.now() + (i + 1) * 86400000);
        const endTime = new Date(startTime.getTime() + 3600000);
        
        const reservation = await tempClient.createReservation({
          spotId: testSpot._id,
          startTime: startTime.toISOString(),
          endTime: endTime.toISOString(),
          vehicleNumber: `VEH${i}`
        });
        
        await tempClient.processPayment({
          reservationId: reservation.body.data._id,
          amount: reservation.body.data.totalAmount,
          method: 'credit_card',
          cardDetails: {
            number: '4111111111111111',
            expiry: '12/25',
            cvv: '123'
          }
        });
      }
      
      // Step 2: Get dashboard statistics
      const dashboard = await adminClient.getDashboardStats();
      
      expect(dashboard.status).toBe(200);
      expect(dashboard.body.data).toHaveProperty('overview');
      expect(dashboard.body.data.overview).toHaveProperty('totalUsers');
      expect(dashboard.body.data.overview.totalUsers).toBeGreaterThanOrEqual(6); // 1 admin + 5 users
      expect(dashboard.body.data.overview).toHaveProperty('totalSpots');
      expect(dashboard.body.data.overview).toHaveProperty('totalReservations');
      expect(dashboard.body.data.overview).toHaveProperty('totalRevenue');
      
      // Step 3: Get revenue report
      const revenueReport = await adminClient.getRevenueReport({
        period: 'weekly'
      });
      
      expect(revenueReport.status).toBe(200);
      expect(revenueReport.body.data).toHaveProperty('totalRevenue');
      expect(revenueReport.body.data).toHaveProperty('dailyBreakdown');
      expect(revenueReport.body.data).toHaveProperty('paymentMethodBreakdown');
      
      // Step 4: Get occupancy report
      const occupancyReport = await adminClient.getOccupancyReport({
        days: 7
      });
      
      expect(occupancyReport.status).toBe(200);
      expect(occupancyReport.body.data).toHaveProperty('averageOccupancy');
      expect(occupancyReport.body.data).toHaveProperty('peakHours');
      expect(occupancyReport.body.data).toHaveProperty('spotUtilization');
    });
    
    it('should manage users', async () => {
      // Step 1: Get all users
      const usersList = await adminClient.getUsers();
      
      expect(usersList.status).toBe(200);
      expect(usersList.body.data.users.length).toBeGreaterThanOrEqual(2);
      
      // Step 2: Get specific user
      const targetUser = usersList.body.data.users.find(u => u.role === 'user');
      const userDetails = await adminClient.getUserById(targetUser._id);
      
      expect(userDetails.status).toBe(200);
      expect(userDetails.body.data).toHaveProperty('email', targetUser.email);
      
      // Step 3: Update user role
      const updateResponse = await adminClient.updateUser(targetUser._id, {
        role: 'manager'
      });
      
      expect(updateResponse.status).toBe(200);
      expect(updateResponse.body.data.role).toBe('manager');
      
      // Step 4: View user activity
      const activityLog = await adminClient.getUserActivity(targetUser._id);
      
      expect(activityLog.status).toBe(200);
      expect(activityLog.body.data).toHaveProperty('reservations');
      expect(activityLog.body.data).toHaveProperty('payments');
    });
    
    it('should manage system settings', async () => {
      // Step 1: Get current settings
      const settingsResponse = await adminClient.getSystemSettings();
      
      expect(settingsResponse.status).toBe(200);
      
      // Step 2: Update settings
      const updates = {
        maxReservationDuration: 48,
        cancellationWindow: 2,
        defaultPricePerHour: 12.50,
        maintenanceMode: false,
        reservationBufferMinutes: 15
      };
      
      const updateResponse = await adminClient.updateSystemSettings(updates);
      
      expect(updateResponse.status).toBe(200);
      expect(updateResponse.body.data).toMatchObject(updates);
      
      // Step 3: Verify settings applied
      const verifyResponse = await adminClient.getSystemSettings();
      expect(verifyResponse.body.data).toMatchObject(updates);
      
      // Step 4: Test settings take effect
      const startTime = new Date(Date.now() + 86400000);
      const endTime = new Date(startTime.getTime() + 49 * 3600000); // 49 hours
      
      const client = new E2EClient();
      const userData = TestDataFactory.generateUser();
      await client.register(userData);
      
      const reservationResponse = await client.createReservation({
        spotId: testSpot._id,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        vehicleNumber: 'ABC123'
      });
      
      expect(reservationResponse.status).toBe(400);
      expect(reservationResponse.body).toHaveProperty('message', 'Maximum reservation duration is 48 hours');
    });
  });
});