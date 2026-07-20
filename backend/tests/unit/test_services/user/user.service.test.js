// parking-management/backend/tests/unit/test_services/user/user.service.test.js
const UserService = require('../../../../src/services/user.service');
const TestDataFactory = require('../helpers/test-data-factory');
const { User, AuditLog } = require('../../../../src/models');

describe('UserService', () => {
  let userService;
  
  beforeEach(() => {
    userService = new UserService();
  });
  
  describe('createUser', () => {
    it('should create user successfully', async () => {
      const userData = TestDataFactory.generateUser();
      
      const user = await userService.createUser(userData);
      
      expect(user).toBeDefined();
      expect(user.email).toBe(userData.email);
      expect(user.firstName).toBe(userData.firstName);
      expect(user.password).not.toBe(userData.password);
    });
    
    it('should encrypt sensitive data', async () => {
      const userData = TestDataFactory.generateUser({
        phone: '+1234567890',
        ssn: '123-45-6789'
      });
      
      const user = await userService.createUser(userData);
      
      expect(user.phone).not.toBe(userData.phone);
      expect(user.ssn).not.toBe(userData.ssn);
    });
  });
  
  describe('getUserById', () => {
    let user;
    
    beforeEach(async () => {
      user = await User.create(TestDataFactory.generateUser());
    });
    
    it('should get user by id', async () => {
      const foundUser = await userService.getUserById(user._id);
      
      expect(foundUser).toBeDefined();
      expect(foundUser._id.toString()).toBe(user._id.toString());
      expect(foundUser.email).toBe(user.email);
    });
    
    it('should throw error for non-existent user', async () => {
      const fakeId = '507f1f77bcf86cd799439011';
      
      await expect(userService.getUserById(fakeId))
        .rejects
        .toThrow('User not found');
    });
    
    it('should include user statistics', async () => {
      const userWithStats = await userService.getUserById(user._id, true);
      
      expect(userWithStats).toHaveProperty('stats');
      expect(userWithStats.stats).toHaveProperty('totalReservations');
      expect(userWithStats.stats).toHaveProperty('totalSpent');
      expect(userWithStats.stats).toHaveProperty('memberSince');
    });
  });
  
  describe('updateUser', () => {
    let user;
    
    beforeEach(async () => {
      user = await User.create(TestDataFactory.generateUser());
    });
    
    it('should update user successfully', async () => {
      const updates = {
        firstName: 'Updated',
        lastName: 'Name',
        phone: '+1987654321',
        preferences: {
          notifications: true,
          language: 'es'
        }
      };
      
      const updatedUser = await userService.updateUser(user._id, updates);
      
      expect(updatedUser.firstName).toBe(updates.firstName);
      expect(updatedUser.lastName).toBe(updates.lastName);
      expect(updatedUser.phone).toBe(updates.phone);
      expect(updatedUser.preferences).toMatchObject(updates.preferences);
    });
    
    it('should not allow updating email to existing email', async () => {
      const anotherUser = await User.create(TestDataFactory.generateUser());
      
      await expect(userService.updateUser(user._id, { email: anotherUser.email }))
        .rejects
        .toThrow('Email already in use');
    });
    
    it('should log profile updates', async () => {
      await userService.updateUser(user._id, { firstName: 'Updated' });
      
      const auditLog = await AuditLog.findOne({
        userId: user._id,
        action: 'profile_update'
      });
      
      expect(auditLog).toBeTruthy();
      expect(auditLog.details).toHaveProperty('changes');
    });
  });
  
  describe('getUsers', () => {
    beforeEach(async () => {
      await User.create(TestDataFactory.generateUser({ firstName: 'Alice' }));
      await User.create(TestDataFactory.generateUser({ firstName: 'Bob', role: 'admin' }));
      await User.create(TestDataFactory.generateUser({ firstName: 'Charlie' }));
    });
    
    it('should get all users with pagination', async () => {
      const result = await userService.getUsers({ page: 1, limit: 2 });
      
      expect(result).toHaveProperty('users');
      expect(result).toHaveProperty('pagination');
      expect(result.users).toHaveLength(2);
      expect(result.pagination).toHaveProperty('total', 3);
      expect(result.pagination).toHaveProperty('page', 1);
      expect(result.pagination).toHaveProperty('pages', 2);
    });
    
    it('should filter by role', async () => {
      const result = await userService.getUsers({ role: 'admin' });
      
      expect(result.users).toHaveLength(1);
      expect(result.users[0].role).toBe('admin');
    });
    
    it('should search by name', async () => {
      const result = await userService.getUsers({ search: 'Alice' });
      
      expect(result.users).toHaveLength(1);
      expect(result.users[0].firstName).toBe('Alice');
    });
    
    it('should sort results', async () => {
      const result = await userService.getUsers({
        sortBy: 'firstName',
        sortOrder: 'desc'
      });
      
      const names = result.users.map(u => u.firstName);
      expect(names).toEqual([...names].sort().reverse());
    });
  });
  
  describe('deleteUser', () => {
    let user;
    
    beforeEach(async () => {
      user = await User.create(TestDataFactory.generateUser());
    });
    
    it('should delete user successfully', async () => {
      await userService.deleteUser(user._id);
      
      const deletedUser = await User.findById(user._id);
      expect(deletedUser).toBeNull();
    });
    
    it('should anonymize user data', async () => {
      await userService.deleteUser(user._id, { anonymize: true });
      
      const anonymizedUser = await User.findById(user._id);
      expect(anonymizedUser.email).toContain('deleted');
      expect(anonymizedUser.firstName).toBe('Deleted');
      expect(anonymizedUser.lastName).toBe('User');
      expect(anonymizedUser.phone).toBeNull();
    });
    
    it('should throw error for non-existent user', async () => {
      const fakeId = '507f1f77bcf86cd799439011';
      
      await expect(userService.deleteUser(fakeId))
        .rejects
        .toThrow('User not found');
    });
  });
});