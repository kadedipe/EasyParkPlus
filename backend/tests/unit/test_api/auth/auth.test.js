// parking-management/backend/tests/unit/test_api/auth/auth.test.js
const APIClient = require('../helpers/api-client');
const TestDataGenerator = require('../helpers/test-data');
const { User } = require('../../../../src/models');

describe('Authentication API', () => {
  let apiClient;
  
  beforeEach(() => {
    apiClient = new APIClient();
  });
  
  describe('POST /api/auth/register', () => {
    it('should register a new user successfully', async () => {
      const userData = TestDataGenerator.generateUser();
      
      const response = await apiClient.register(userData);
      
      expect(response.status).toBe(201);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body.data).toHaveProperty('user');
      expect(response.body.data.user).toHaveProperty('email', userData.email);
      expect(response.body.data.user).not.toHaveProperty('password');
      expect(response.body.data).toHaveProperty('token');
      
      // Verify user was created in database
      const user = await User.findOne({ email: userData.email });
      expect(user).toBeTruthy();
      expect(user.firstName).toBe(userData.firstName);
    });
    
    it('should validate email format', async () => {
      const userData = TestDataGenerator.generateUser({ email: 'invalid-email' });
      
      const response = await apiClient.register(userData);
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('success', false);
      expect(response.body).toHaveProperty('errors');
      expect(response.body.errors).toContainEqual(
        expect.objectContaining({ field: 'email' })
      );
    });
    
    it('should enforce password strength requirements', async () => {
      const userData = TestDataGenerator.generateUser({ password: 'weak' });
      
      const response = await apiClient.register(userData);
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('success', false);
      expect(response.body.errors).toContainEqual(
        expect.objectContaining({ field: 'password' })
      );
    });
    
    it('should require all required fields', async () => {
      const response = await apiClient.register({ email: 'test@example.com' });
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('errors');
      expect(response.body.errors.length).toBeGreaterThan(1);
    });
    
    it('should reject duplicate email registration', async () => {
      const userData = TestDataGenerator.generateUser();
      await apiClient.register(userData);
      
      const response = await apiClient.register(userData);
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Email already registered');
    });
    
    it('should hash password before saving', async () => {
      const userData = TestDataGenerator.generateUser();
      await apiClient.register(userData);
      
      const user = await User.findOne({ email: userData.email });
      expect(user.password).not.toBe(userData.password);
      const bcrypt = require('bcryptjs');
      const isValid = await bcrypt.compare(userData.password, user.password);
      expect(isValid).toBe(true);
    });
  });
  
  describe('POST /api/auth/login', () => {
    let testUser;
    
    beforeEach(async () => {
      testUser = TestDataGenerator.generateUser();
      await apiClient.register(testUser);
    });
    
    it('should login successfully with correct credentials', async () => {
      const response = await apiClient.login({
        email: testUser.email,
        password: testUser.password
      });
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body.data).toHaveProperty('token');
      expect(response.body.data.user).toHaveProperty('email', testUser.email);
      
      // Verify token is valid
      const jwt = require('jsonwebtoken');
      const decoded = jwt.verify(response.body.data.token, process.env.JWT_SECRET);
      expect(decoded).toHaveProperty('email', testUser.email);
    });
    
    it('should return 401 with wrong password', async () => {
      const response = await apiClient.login({
        email: testUser.email,
        password: 'WrongPassword123!'
      });
      
      expect(response.status).toBe(401);
      expect(response.body).toHaveProperty('message', 'Invalid credentials');
    });
    
    it('should return 401 with non-existent email', async () => {
      const response = await apiClient.login({
        email: 'nonexistent@example.com',
        password: 'Password123!'
      });
      
      expect(response.status).toBe(401);
      expect(response.body).toHaveProperty('message', 'Invalid credentials');
    });
    
    it('should track failed login attempts', async () => {
      // Attempt 4 failed logins
      for (let i = 0; i < 4; i++) {
        await apiClient.login({
          email: testUser.email,
          password: 'WrongPassword'
        });
      }
      
      // Check login attempts count
      const user = await User.findOne({ email: testUser.email });
      expect(user.loginAttempts).toBe(4);
      expect(user.isLocked).toBe(false);
      
      // 5th failed attempt should lock account
      await apiClient.login({
        email: testUser.email,
        password: 'WrongPassword'
      });
      
      const lockedUser = await User.findOne({ email: testUser.email });
      expect(lockedUser.isLocked).toBe(true);
      expect(lockedUser.lockUntil).toBeDefined();
      
      // Attempt login with correct password
      const response = await apiClient.login({
        email: testUser.email,
        password: testUser.password
      });
      
      expect(response.status).toBe(423);
      expect(response.body).toHaveProperty('message', 'Account locked. Try again later');
    });
    
    it('should reset login attempts on successful login', async () => {
      // Failed attempts
      for (let i = 0; i < 3; i++) {
        await apiClient.login({
          email: testUser.email,
          password: 'WrongPassword'
        });
      }
      
      // Successful login
      await apiClient.login({
        email: testUser.email,
        password: testUser.password
      });
      
      const user = await User.findOne({ email: testUser.email });
      expect(user.loginAttempts).toBe(0);
    });
  });
  
  describe('POST /api/auth/logout', () => {
    let authToken;
    
    beforeEach(async () => {
      const userData = TestDataGenerator.generateUser();
      const registerResponse = await apiClient.register(userData);
      authToken = registerResponse.body.data.token;
      apiClient.setAuthToken(authToken);
    });
    
    it('should logout successfully', async () => {
      const response = await apiClient.logout();
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('message', 'Logged out successfully');
    });
    
    it('should invalidate token after logout', async () => {
      await apiClient.logout();
      
      // Try to use the same token
      const profileResponse = await apiClient.getProfile();
      expect(profileResponse.status).toBe(401);
    });
    
    it('should return 401 without token', async () => {
      apiClient.setAuthToken(null);
      const response = await apiClient.logout();
      
      expect(response.status).toBe(401);
    });
  });
  
  describe('POST /api/auth/refresh-token', () => {
    let authToken;
    
    beforeEach(async () => {
      const userData = TestDataGenerator.generateUser();
      const registerResponse = await apiClient.register(userData);
      authToken = registerResponse.body.data.token;
      apiClient.setAuthToken(authToken);
    });
    
    it('should refresh token successfully', async () => {
      const response = await apiClient.refreshToken();
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body.data).toHaveProperty('token');
      expect(response.body.data.token).not.toBe(authToken);
      
      // Verify new token works
      apiClient.setAuthToken(response.body.data.token);
      const profileResponse = await apiClient.getProfile();
      expect(profileResponse.status).toBe(200);
    });
    
    it('should return 401 with invalid token', async () => {
      apiClient.setAuthToken('invalid-token');
      const response = await apiClient.refreshToken();
      
      expect(response.status).toBe(401);
    });
  });
  
  describe('POST /api/auth/forgot-password', () => {
    let testUser;
    
    beforeEach(async () => {
      testUser = TestDataGenerator.generateUser();
      await apiClient.register(testUser);
    });
    
    it('should send password reset email', async () => {
      const response = await apiClient.forgotPassword(testUser.email);
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('message', 'Password reset email sent');
      
      // Verify reset token was created
      const user = await User.findOne({ email: testUser.email });
      expect(user.resetPasswordToken).toBeTruthy();
      expect(user.resetPasswordExpires).toBeTruthy();
      expect(user.resetPasswordExpires.getTime()).toBeGreaterThan(Date.now());
    });
    
    it('should return 404 for non-existent email', async () => {
      const response = await apiClient.forgotPassword('nonexistent@example.com');
      
      expect(response.status).toBe(404);
      expect(response.body).toHaveProperty('message', 'No user found with this email');
    });
    
    it('should validate email format', async () => {
      const response = await apiClient.forgotPassword('invalid-email');
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('errors');
    });
  });
  
  describe('POST /api/auth/reset-password', () => {
    let testUser;
    let resetToken;
    
    beforeEach(async () => {
      testUser = TestDataGenerator.generateUser();
      await apiClient.register(testUser);
      
      // Generate reset token
      const forgotResponse = await apiClient.forgotPassword(testUser.email);
      
      const user = await User.findOne({ email: testUser.email });
      resetToken = user.resetPasswordToken;
    });
    
    it('should reset password successfully', async () => {
      const newPassword = 'NewPassword123!@#';
      
      const response = await apiClient.resetPassword(resetToken, newPassword);
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('message', 'Password reset successfully');
      
      // Verify new password works
      const loginResponse = await apiClient.login({
        email: testUser.email,
        password: newPassword
      });
      
      expect(loginResponse.status).toBe(200);
      
      // Verify old password doesn't work
      const oldLoginResponse = await apiClient.login({
        email: testUser.email,
        password: testUser.password
      });
      
      expect(oldLoginResponse.status).toBe(401);
      
      // Verify reset token is cleared
      const user = await User.findOne({ email: testUser.email });
      expect(user.resetPasswordToken).toBeNull();
      expect(user.resetPasswordExpires).toBeNull();
    });
    
    it('should return 400 with invalid token', async () => {
      const response = await apiClient.resetPassword('invalid-token', 'NewPassword123!');
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Invalid or expired token');
    });
    
    it('should return 400 with expired token', async () => {
      // Simulate expired token
      const user = await User.findOne({ email: testUser.email });
      user.resetPasswordExpires = new Date(Date.now() - 3600000);
      await user.save();
      
      const response = await apiClient.resetPassword(resetToken, 'NewPassword123!');
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Invalid or expired token');
    });
    
    it('should validate new password strength', async () => {
      const response = await apiClient.resetPassword(resetToken, 'weak');
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('errors');
      expect(response.body.errors).toContainEqual(
        expect.objectContaining({ field: 'newPassword' })
      );
    });
  });
});