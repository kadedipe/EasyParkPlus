// parking-management/backend/tests/unit/test_api/admin/admin.test.js
const APIClient = require('../helpers/api-client');
const TestDataGenerator = require('../helpers/test-data');
const { User, Reservation, ParkingSpot, Payment } = require('../../../../src/models');

describe('Admin API', () => {
  let apiClient;
  let testAdmin;
  let testUser;
  let testSpot;
  
  beforeEach(async () => {
    apiClient = new APIClient();
    
    // Create admin user
    const adminData = TestDataGenerator.generateAdmin();
    const adminResponse = await apiClient.register(adminData);
    testAdmin = {
      id: adminResponse.body.data.user._id,
      token: adminResponse.body.data.token
    };
    
    // Create regular user
    const userData = TestDataGenerator.generateUser();
    const userResponse = await apiClient.register(userData);
    testUser = {
      id: userResponse.body.data.user._id,
      token: userResponse.body.data.token,
      email: userData.email
    };
    
    apiClient.setAdminToken(testAdmin.token);
    
    // Create test parking spot
    const spotData = TestDataGenerator.generateParkingSpot();
    const spotResponse = await apiClient.createParkingSpot(spotData);
    testSpot = spotResponse.body.data;
    
    // Create test reservations and payments
    apiClient.setAuthToken(testUser.token);
    
    const startTime = new Date(Date.now() + 3600000);
    const endTime = new Date(Date.now() + 7200000);
    
    const reservationResponse = await apiClient.createReservation({
      spotId: testSpot._id,
      startTime: startTime.toISOString(),
      endTime: endTime.toISOString(),
      vehicleNumber: 'ABC123'
    });
    
    await apiClient.processPayment({
      reservationId: reservationResponse.body.data._id,
      amount: reservationResponse.body.data.totalAmount,
      method: 'credit_card'
    });
    
    apiClient.setAdminToken(testAdmin.token);
  });
  
  describe('GET /api/admin/dashboard', () => {
    it('should get dashboard statistics', async () => {
      const response = await apiClient.getDashboardStats();
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('overview');
      expect(response.body.data.overview).toHaveProperty('totalUsers');
      expect(response.body.data.overview).toHaveProperty('totalSpots');
      expect(response.body.data.overview).toHaveProperty('totalReservations');
      expect(response.body.data.overview).toHaveProperty('totalRevenue');
      
      expect(response.body.data).toHaveProperty('recentActivity');
      expect(response.body.data).toHaveProperty('topSpots');
      expect(response.body.data).toHaveProperty('occupancyRate');
    });
    
    it('should include revenue trends', async () => {
      const response = await apiClient.getDashboardStats();
      
      expect(response.body.data).toHaveProperty('revenueTrends');
      expect(response.body.data.revenueTrends).toHaveProperty('daily');
      expect(response.body.data.revenueTrends).toHaveProperty('weekly');
      expect(response.body.data.revenueTrends).toHaveProperty('monthly');
    });
    
    it('should include spot utilization', async () => {
      const response = await apiClient.getDashboardStats();
      
      expect(response.body.data).toHaveProperty('spotUtilization');
      expect(response.body.data.spotUtilization).toHaveProperty('total');
      expect(response.body.data.spotUtilization).toHaveProperty('occupied');
      expect(response.body.data.spotUtilization).toHaveProperty('available');
      expect(response.body.data.spotUtilization).toHaveProperty('maintenance');
    });
    
    it('should return 403 for non-admin users', async () => {
      apiClient.setAuthToken(testUser.token);
      const response = await apiClient.getDashboardStats();
      
      expect(response.status).toBe(403);
    });
  });
  
  describe('GET /api/admin/reports/revenue', () => {
    it('should generate revenue report', async () => {
      const response = await apiClient.getRevenueReport({
        startDate: new Date(Date.now() - 86400000).toISOString(),
        endDate: new Date().toISOString()
      });
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('totalRevenue');
      expect(response.body.data).toHaveProperty('dailyBreakdown');
      expect(response.body.data).toHaveProperty('paymentMethodBreakdown');
      expect(response.body.data).toHaveProperty('averageTransactionValue');
    });
    
    it('should filter by payment method', async () => {
      const response = await apiClient.getRevenueReport({
        startDate: new Date(Date.now() - 86400000).toISOString(),
        endDate: new Date().toISOString(),
        paymentMethod: 'credit_card'
      });
      
      expect(response.status).toBe(200);
      expect(response.body.data.paymentMethodBreakdown).toHaveProperty('credit_card');
    });
    
    it('should support date ranges', async () => {
      const response = await apiClient.getRevenueReport({
        period: 'month'
      });
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('period', 'month');
    });
    
    it('should export CSV', async () => {
      const response = await apiClient.get('/api/admin/reports/revenue/export', {
        startDate: new Date(Date.now() - 86400000).toISOString(),
        endDate: new Date().toISOString(),
        format: 'csv'
      });
      
      expect(response.status).toBe(200);
      expect(response.headers['content-type']).toContain('text/csv');
      expect(response.headers['content-disposition']).toContain('attachment');
    });
  });
  
  describe('GET /api/admin/reports/occupancy', () => {
    it('should generate occupancy report', async () => {
      const response = await apiClient.getOccupancyReport({
        startDate: new Date(Date.now() - 86400000).toISOString(),
        endDate: new Date().toISOString()
      });
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('averageOccupancy');
      expect(response.body.data).toHaveProperty('peakHours');
      expect(response.body.data).toHaveProperty('spotTypeBreakdown');
      expect(response.body.data).toHaveProperty('hourlyOccupancy');
    });
    
    it('should calculate occupancy rates', async () => {
      const response = await apiClient.getOccupancyReport({
        startDate: new Date(Date.now() - 86400000).toISOString(),
        endDate: new Date().toISOString()
      });
      
      expect(response.body.data).toHaveProperty('occupancyRate');
      expect(response.body.data.occupancyRate).toBeGreaterThanOrEqual(0);
      expect(response.body.data.occupancyRate).toBeLessThanOrEqual(100);
    });
    
    it('should show trends by day of week', async () => {
      const response = await apiClient.getOccupancyReport({
        startDate: new Date(Date.now() - 604800000).toISOString(),
        endDate: new Date().toISOString()
      });
      
      expect(response.body.data).toHaveProperty('dailyPattern');
      expect(Object.keys(response.body.data.dailyPattern)).toHaveLength(7);
    });
  });
  
  describe('GET /api/admin/users', () => {
    it('should list all users with statistics', async () => {
      const response = await apiClient.getUsers();
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('users');
      expect(response.body.data.users[0]).toHaveProperty('stats');
      expect(response.body.data.users[0].stats).toHaveProperty('reservationCount');
      expect(response.body.data.users[0].stats).toHaveProperty('totalSpent');
    });
    
    it('should filter by user status', async () => {
      // Create inactive user
      const inactiveUser = TestDataGenerator.generateUser();
      await apiClient.register(inactiveUser);
      await User.findByIdAndUpdate(inactiveUser.id, { isActive: false });
      
      const response = await apiClient.getUsers({ status: 'inactive' });
      
      expect(response.status).toBe(200);
      expect(response.body.data.users.some(u => !u.isActive)).toBe(true);
    });
    
    it('should sort by registration date', async () => {
      const response = await apiClient.getUsers({
        sortBy: 'createdAt',
        sortOrder: 'desc'
      });
      
      const dates = response.body.data.users.map(u => new Date(u.createdAt));
      expect(dates).toEqual([...dates].sort((a, b) => b - a));
    });
  });
  
  describe('GET /api/admin/analytics', () => {
    it('should get user analytics', async () => {
      const response = await apiClient.get('/api/admin/analytics/users');
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('totalUsers');
      expect(response.body.data).toHaveProperty('newUsersToday');
      expect(response.body.data).toHaveProperty('newUsersThisWeek');
      expect(response.body.data).toHaveProperty('userGrowth');
    });
    
    it('should get reservation analytics', async () => {
      const response = await apiClient.get('/api/admin/analytics/reservations');
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('totalReservations');
      expect(response.body.data).toHaveProperty('completedReservations');
      expect(response.body.data).toHaveProperty('cancelledReservations');
      expect(response.body.data).toHaveProperty('cancellationRate');
    });
    
    it('should get spot analytics', async () => {
      const response = await apiClient.get('/api/admin/analytics/spots');
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('totalSpots');
      expect(response.body.data).toHaveProperty('spotsByType');
      expect(response.body.data).toHaveProperty('averagePrice');
      expect(response.body.data).toHaveProperty('mostPopularSpots');
    });
  });
  
  describe('POST /api/admin/maintenance', () => {
    it('should trigger database maintenance', async () => {
      const response = await apiClient.post('/api/admin/maintenance/database', {
        action: 'vacuum'
      });
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('message');
    });
    
    it('should trigger cache clearing', async () => {
      const response = await apiClient.post('/api/admin/maintenance/cache', {
        type: 'redis'
      });
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
    });
    
    it('should validate maintenance action', async () => {
      const response = await apiClient.post('/api/admin/maintenance/database', {
        action: 'invalid'
      });
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Invalid maintenance action');
    });
  });
  
  describe('GET /api/admin/system/health', () => {
    it('should get system health status', async () => {
      const response = await apiClient.get('/api/admin/system/health');
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('status');
      expect(response.body.data).toHaveProperty('components');
      expect(response.body.data.components).toHaveProperty('database');
      expect(response.body.data.components).toHaveProperty('redis');
      expect(response.body.data.components).toHaveProperty('disk');
      expect(response.body.data.components).toHaveProperty('memory');
    });
    
    it('should include detailed metrics', async () => {
      const response = await apiClient.get('/api/admin/system/health?detailed=true');
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('metrics');
      expect(response.body.data.metrics).toHaveProperty('responseTime');
      expect(response.body.data.metrics).toHaveProperty('errorRate');
      expect(response.body.data.metrics).toHaveProperty('requestRate');
    });
  });
  
  describe('POST /api/admin/settings', () => {
    it('should update system settings', async () => {
      const settings = {
        maxReservationDuration: 72,
        cancellationWindow: 2,
        defaultPricePerHour: 15,
        maintenanceMode: false
      };
      
      const response = await apiClient.post('/api/admin/settings', settings);
      
      expect(response.status).toBe(200);
      expect(response.body.data).toMatchObject(settings);
      
      // Verify settings were applied
      const getResponse = await apiClient.get('/api/admin/settings');
      expect(getResponse.body.data).toMatchObject(settings);
    });
    
    it('should validate settings values', async () => {
      const response = await apiClient.post('/api/admin/settings', {
        maxReservationDuration: -1,
        cancellationWindow: -5
      });
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('errors');
    });
    
    it('should log settings changes', async () => {
      const settings = { maintenanceMode: true };
      
      await apiClient.post('/api/admin/settings', settings);
      
      const auditLog = await apiClient.get('/api/admin/audit-logs?action=settings_update');
      expect(auditLog.body.data.logs).toContainEqual(
        expect.objectContaining({ action: 'settings_update' })
      );
    });
  });
  
  describe('GET /api/admin/audit-logs', () => {
    beforeEach(async () => {
      // Generate some audit logs
      await apiClient.updateProfile({ firstName: 'Test' });
      await apiClient.createParkingSpot(TestDataGenerator.generateParkingSpot());
      await apiClient.updateParkingSpot(testSpot._id, { pricePerHour: 20 });
    });
    
    it('should list audit logs', async () => {
      const response = await apiClient.get('/api/admin/audit-logs');
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('logs');
      expect(response.body.data.logs.length).toBeGreaterThan(0);
      expect(response.body.data).toHaveProperty('pagination');
    });
    
    it('should filter by action', async () => {
      const response = await apiClient.get('/api/admin/audit-logs?action=profile_update');
      
      expect(response.status).toBe(200);
      expect(response.body.data.logs.every(log => log.action === 'profile_update')).toBe(true);
    });
    
    it('should filter by user', async () => {
      const response = await apiClient.get(`/api/admin/audit-logs?userId=${testUser.id}`);
      
      expect(response.status).toBe(200);
      expect(response.body.data.logs.every(log => log.userId === testUser.id)).toBe(true);
    });
    
    it('should filter by date range', async () => {
      const startDate = new Date();
      startDate.setHours(0, 0, 0, 0);
      
      const response = await apiClient.get('/api/admin/audit-logs', {
        startDate: startDate.toISOString(),
        endDate: new Date().toISOString()
      });
      
      expect(response.status).toBe(200);
      expect(response.body.data.logs.length).toBeGreaterThan(0);
    });
    
    it('should export audit logs', async () => {
      const response = await apiClient.get('/api/admin/audit-logs/export', {
        format: 'csv'
      });
      
      expect(response.status).toBe(200);
      expect(response.headers['content-type']).toContain('text/csv');
    });
  });
});