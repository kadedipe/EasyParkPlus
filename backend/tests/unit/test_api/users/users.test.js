// parking-management/backend/tests/unit/test_api/users/users.test.js
const APIClient = require('../helpers/api-client');
const TestDataGenerator = require('../helpers/test-data');
const { User, AuditLog } = require('../../../../src/models');

describe('User API', () => {
  let apiClient;
  let testUser;
  let testAdmin;
  
  beforeEach(async () => {
    apiClient = new APIClient();
    
    // Create regular user
    testUser = TestDataGenerator.generateUser();
    const userResponse = await apiClient.register(testUser);
    testUser.id = userResponse.body.data.user._id;
    testUser.token = userResponse.body.data.token;
    
    // Create admin user
    testAdmin = TestDataGenerator.generateAdmin();
    const adminResponse = await apiClient.register(testAdmin);
    testAdmin.id = adminResponse.body.data.user._id;
    testAdmin.token = adminResponse.body.data.token;
    
    apiClient.setAuthToken(testUser.token);
  });
  
  describe('GET /api/users/profile', () => {
    it('should get current user profile', async () => {
      const response = await apiClient.getProfile();
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body.data).toHaveProperty('email', testUser.email);
      expect(response.body.data).toHaveProperty('firstName', testUser.firstName);
      expect(response.body.data).toHaveProperty('lastName', testUser.lastName);
      expect(response.body.data).not.toHaveProperty('password');
    });
    
    it('should include user statistics', async () => {
      const response = await apiClient.getProfile();
      
      expect(response.body.data).toHaveProperty('stats');
      expect(response.body.data.stats).toHaveProperty('totalReservations');
      expect(response.body.data.stats).toHaveProperty('totalSpent');
      expect(response.body.data.stats).toHaveProperty('memberSince');
    });
    
    it('should return 401 without token', async () => {
      apiClient.setAuthToken(null);
      const response = await apiClient.getProfile();
      
      expect(response.status).toBe(401);
    });
  });
  
  describe('PUT /api/users/profile', () => {
    it('should update user profile', async () => {
      const updates = {
        firstName: 'Updated',
        lastName: 'Name',
        phone: '+19876543210',
        preferences: {
          notifications: true,
          language: 'es'
        }
      };
      
      const response = await apiClient.updateProfile(updates);
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('firstName', updates.firstName);
      expect(response.body.data).toHaveProperty('lastName', updates.lastName);
      expect(response.body.data).toHaveProperty('phone', updates.phone);
      expect(response.body.data.preferences).toMatchObject(updates.preferences);
      
      // Verify database
      const user = await User.findById(testUser.id);
      expect(user.firstName).toBe(updates.firstName);
      expect(user.lastName).toBe(updates.lastName);
    });
    
    it('should not allow updating email to existing email', async () => {
      // Create another user
      const anotherUser = TestDataGenerator.generateUser();
      await apiClient.register(anotherUser);
      
      const response = await apiClient.updateProfile({
        email: anotherUser.email
      });
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Email already in use');
    });
    
    it('should allow updating email to same email', async () => {
      const response = await apiClient.updateProfile({
        email: testUser.email
      });
      
      expect(response.status).toBe(200);
    });
    
    it('should validate input data', async () => {
      const response = await apiClient.updateProfile({
        email: 'invalid-email',
        phone: 'invalid'
      });
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('errors');
      expect(response.body.errors.length).toBeGreaterThan(0);
    });
    
    it('should log profile update in audit log', async () => {
      await apiClient.updateProfile({
        firstName: 'Updated'
      });
      
      const auditLog = await AuditLog.findOne({
        userId: testUser.id,
        action: 'profile_update'
      });
      
      expect(auditLog).toBeTruthy();
      expect(auditLog.details).toHaveProperty('changes');
    });
  });
  
  describe('PUT /api/users/change-password', () => {
    it('should change password successfully', async () => {
      const newPassword = 'NewPassword123!@#';
      
      const response = await apiClient.changePassword(testUser.password, newPassword);
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      
      // Verify new password works
      const loginResponse = await apiClient.login({
        email: testUser.email,
        password: newPassword
      });
      
      expect(loginResponse.status).toBe(200);
    });
    
    it('should return 401 with wrong current password', async () => {
      const response = await apiClient.changePassword('WrongPassword123!', 'NewPassword123!');
      
      expect(response.status).toBe(401);
      expect(response.body).toHaveProperty('message', 'Current password is incorrect');
    });
    
    it('should validate new password strength', async () => {
      const response = await apiClient.changePassword(testUser.password, 'weak');
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('errors');
    });
    
    it('should not allow same password', async () => {
      const response = await apiClient.changePassword(testUser.password, testUser.password);
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'New password must be different from current password');
    });
  });
  
  describe('GET /api/users', () => {
    beforeEach(() => {
      apiClient.setAdminToken(testAdmin.token);
    });
    
    it('should list all users for admin', async () => {
      // Create additional users
      await apiClient.register(TestDataGenerator.generateUser());
      await apiClient.register(TestDataGenerator.generateUser());
      
      const response = await apiClient.getUsers();
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body.data).toHaveProperty('users');
      expect(response.body.data.users.length).toBeGreaterThanOrEqual(3);
      expect(response.body.data).toHaveProperty('pagination');
      expect(response.body.data.pagination).toHaveProperty('total');
      expect(response.body.data.pagination).toHaveProperty('page');
      expect(response.body.data.pagination).toHaveProperty('limit');
    });
    
    it('should filter users by role', async () => {
      const response = await apiClient.getUsers({ role: 'admin' });
      
      expect(response.status).toBe(200);
      expect(response.body.data.users.every(user => user.role === 'admin')).toBe(true);
    });
    
    it('should search users by name', async () => {
      await apiClient.register(TestDataGenerator.generateUser({
        firstName: 'John',
        lastName: 'Doe'
      }));
      
      const response = await apiClient.getUsers({ search: 'John' });
      
      expect(response.status).toBe(200);
      expect(response.body.data.users.some(user => user.firstName === 'John')).toBe(true);
    });
    
    it('should search users by email', async () => {
      const uniqueEmail = `unique${Date.now()}@example.com`;
      await apiClient.register(TestDataGenerator.generateUser({ email: uniqueEmail }));
      
      const response = await apiClient.getUsers({ search: uniqueEmail });
      
      expect(response.status).toBe(200);
      expect(response.body.data.users[0].email).toBe(uniqueEmail);
    });
    
    it('should paginate results', async () => {
      const response = await apiClient.getUsers({ page: 1, limit: 2 });
      
      expect(response.status).toBe(200);
      expect(response.body.data.users.length).toBeLessThanOrEqual(2);
      expect(response.body.data.pagination).toHaveProperty('page', 1);
      expect(response.body.data.pagination).toHaveProperty('limit', 2);
    });
    
    it('should sort results', async () => {
      const response = await apiClient.getUsers({
        sortBy: 'createdAt',
        sortOrder: 'desc'
      });
      
      const dates = response.body.data.users.map(u => new Date(u.createdAt));
      expect(dates).toEqual([...dates].sort((a, b) => b - a));
    });
    
    it('should return 403 for non-admin users', async () => {
      apiClient.setAuthToken(testUser.token);
      const response = await apiClient.getUsers();
      
      expect(response.status).toBe(403);
      expect(response.body).toHaveProperty('message', 'Access denied');
    });
  });
  
  describe('GET /api/users/:id', () => {
    let targetUser;
    
    beforeEach(async () => {
      const userResponse = await apiClient.register(TestDataGenerator.generateUser());
      targetUser = userResponse.body.data.user;
    });
    
    it('should get user by id for admin', async () => {
      apiClient.setAdminToken(testAdmin.token);
      const response = await apiClient.getUserById(targetUser._id);
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('email', targetUser.email);
      expect(response.body.data).not.toHaveProperty('password');
    });
    
    it('should allow user to get their own profile by id', async () => {
      const response = await apiClient.getUserById(testUser.id);
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('email', testUser.email);
    });
    
    it('should return 403 for accessing other user profile', async () => {
      const { token } = await apiClient.register(TestDataGenerator.generateUser());
      apiClient.setAuthToken(token);
      
      const response = await apiClient.getUserById(testUser.id);
      
      expect(response.status).toBe(403);
      expect(response.body).toHaveProperty('message', 'Access denied');
    });
    
    it('should return 404 for non-existent user', async () => {
      const nonExistentId = '507f1f77bcf86cd799439011';
      apiClient.setAdminToken(testAdmin.token);
      
      const response = await apiClient.getUserById(nonExistentId);
      
      expect(response.status).toBe(404);
      expect(response.body).toHaveProperty('message', 'User not found');
    });
  });
  
  describe('DELETE /api/users/:id', () => {
    let userToDelete;
    
    beforeEach(async () => {
      const userResponse = await apiClient.register(TestDataGenerator.generateUser());
      userToDelete = userResponse.body.data.user;
      apiClient.setAdminToken(testAdmin.token);
    });
    
    it('should delete user as admin', async () => {
      const response = await apiClient.deleteUser(userToDelete._id);
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      
      const deletedUser = await User.findById(userToDelete._id);
      expect(deletedUser).toBeNull();
    });
    
    it('should not allow user to delete themselves', async () => {
      const response = await apiClient.deleteUser(testAdmin.id);
      
      expect(response.status).toBe(403);
      expect(response.body).toHaveProperty('message', 'Cannot delete your own account');
    });
    
    it('should handle deletion with existing data', async () => {
      // Create user with reservations
      const userData = TestDataGenerator.generateUser();
      const userResponse = await apiClient.register(userData);
      const user = userResponse.body.data.user;
      
      // Create parking spot and reservation
      const spotData = TestDataGenerator.generateParkingSpot();
      const spotResponse = await apiClient.createParkingSpot(spotData);
      
      const reservationData = TestDataGenerator.generateReservation(user._id, spotResponse.body.data._id);
      await apiClient.createReservation(reservationData);
      
      // Delete user (should cascade or handle gracefully)
      const response = await apiClient.deleteUser(user._id);
      
      expect(response.status).toBe(200);
      
      // User should be deleted
      const deletedUser = await User.findById(user._id);
      expect(deletedUser).toBeNull();
    });
    
    it('should require admin role', async () => {
      apiClient.setAuthToken(testUser.token);
      const response = await apiClient.deleteUser(userToDelete._id);
      
      expect(response.status).toBe(403);
    });
  });
});