// parking-management/backend/tests/unit/test_services/auth/auth.service.test.js
const AuthService = require('../../../../src/services/auth.service');
const UserService = require('../../../../src/services/user.service');
const TokenService = require('../../../../src/services/token.service');
const EmailService = require('../../../../src/services/email.service');
const TestDataFactory = require('../helpers/test-data-factory');
const MockFactory = require('../helpers/mock-factory');
const { User, BlacklistedToken } = require('../../../../src/models');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

describe('AuthService', () => {
  let authService;
  let userService;
  let tokenService;
  let emailService;
  
  beforeEach(() => {
    userService = new UserService();
    tokenService = new TokenService();
    emailService = new EmailService();
    authService = new AuthService(userService, tokenService, emailService);
  });
  
  describe('register', () => {
    it('should register a new user successfully', async () => {
      const userData = TestDataFactory.generateUser();
      
      const result = await authService.register(userData);
      
      expect(result).toHaveProperty('success', true);
      expect(result).toHaveProperty('user');
      expect(result).toHaveProperty('tokens');
      expect(result.user).toHaveProperty('email', userData.email);
      expect(result.user).not.toHaveProperty('password');
      expect(result.tokens).toHaveProperty('accessToken');
      expect(result.tokens).toHaveProperty('refreshToken');
      
      // Verify user was created in database
      const user = await User.findOne({ email: userData.email });
      expect(user).toBeTruthy();
      expect(user.firstName).toBe(userData.firstName);
    });
    
    it('should hash password before saving', async () => {
      const userData = TestDataFactory.generateUser();
      
      await authService.register(userData);
      
      const user = await User.findOne({ email: userData.email });
      expect(user.password).not.toBe(userData.password);
      const isValid = await bcrypt.compare(userData.password, user.password);
      expect(isValid).toBe(true);
    });
    
    it('should throw error if email already exists', async () => {
      const userData = TestDataFactory.generateUser();
      await User.create(userData);
      
      await expect(authService.register(userData))
        .rejects
        .toThrow('Email already registered');
    });
    
    it('should validate email format', async () => {
      const invalidEmail = TestDataFactory.generateUser({ email: 'invalid-email' });
      
      await expect(authService.register(invalidEmail))
        .rejects
        .toThrow('Invalid email format');
    });
    
    it('should validate password strength', async () => {
      const weakPassword = TestDataFactory.generateUser({ password: 'weak' });
      
      await expect(authService.register(weakPassword))
        .rejects
        .toThrow('Password too weak');
    });
    
    it('should send welcome email', async () => {
      const userData = TestDataFactory.generateUser();
      
      await authService.register(userData);
      
      expect(emailService.sendWelcomeEmail).toHaveBeenCalledWith(
        userData.email,
        userData.firstName
      );
    });
  });
  
  describe('login', () => {
    let testUser;
    let plainPassword;
    
    beforeEach(async () => {
      plainPassword = 'Test123!@#';
      const hashedPassword = await bcrypt.hash(plainPassword, 10);
      testUser = await User.create({
        ...TestDataFactory.generateUser(),
        password: hashedPassword
      });
    });
    
    it('should login successfully with correct credentials', async () => {
      const result = await authService.login(testUser.email, plainPassword);
      
      expect(result).toHaveProperty('success', true);
      expect(result).toHaveProperty('user');
      expect(result).toHaveProperty('tokens');
      expect(result.user).toHaveProperty('email', testUser.email);
      expect(result.tokens.accessToken).toBeDefined();
      expect(result.tokens.refreshToken).toBeDefined();
    });
    
    it('should throw error with wrong password', async () => {
      await expect(authService.login(testUser.email, 'WrongPassword123!'))
        .rejects
        .toThrow('Invalid credentials');
    });
    
    it('should throw error with non-existent email', async () => {
      await expect(authService.login('nonexistent@example.com', 'Password123!'))
        .rejects
        .toThrow('Invalid credentials');
    });
    
    it('should track failed login attempts', async () => {
      for (let i = 0; i < 4; i++) {
        await expect(authService.login(testUser.email, 'WrongPassword'))
          .rejects
          .toThrow('Invalid credentials');
      }
      
      const user = await User.findById(testUser._id);
      expect(user.loginAttempts).toBe(4);
      
      // 5th failed attempt should lock account
      await expect(authService.login(testUser.email, 'WrongPassword'))
        .rejects
        .toThrow('Account locked');
      
      const lockedUser = await User.findById(testUser._id);
      expect(lockedUser.isLocked).toBe(true);
    });
    
    it('should reset login attempts on successful login', async () => {
      // Failed attempts
      for (let i = 0; i < 3; i++) {
        await expect(authService.login(testUser.email, 'WrongPassword'))
          .rejects
          .toThrow('Invalid credentials');
      }
      
      // Successful login
      await authService.login(testUser.email, plainPassword);
      
      const user = await User.findById(testUser._id);
      expect(user.loginAttempts).toBe(0);
    });
    
    it('should not allow login for locked account', async () => {
      // Lock account
      for (let i = 0; i < 5; i++) {
        await expect(authService.login(testUser.email, 'WrongPassword'))
          .rejects
          .toThrow();
      }
      
      await expect(authService.login(testUser.email, plainPassword))
        .rejects
        .toThrow('Account locked');
    });
  });
  
  describe('logout', () => {
    let accessToken;
    let refreshToken;
    
    beforeEach(async () => {
      const userData = TestDataFactory.generateUser();
      const user = await User.create(userData);
      accessToken = tokenService.generateAccessToken(user);
      refreshToken = tokenService.generateRefreshToken(user);
    });
    
    it('should logout successfully', async () => {
      const result = await authService.logout(accessToken, refreshToken);
      
      expect(result).toHaveProperty('success', true);
      
      // Verify tokens are blacklisted
      const blacklistedAccess = await BlacklistedToken.findOne({ token: accessToken });
      expect(blacklistedAccess).toBeTruthy();
      
      const blacklistedRefresh = await BlacklistedToken.findOne({ token: refreshToken });
      expect(blacklistedRefresh).toBeTruthy();
    });
    
    it('should throw error with invalid token', async () => {
      await expect(authService.logout('invalid-token', 'invalid-refresh'))
        .rejects
        .toThrow('Invalid token');
    });
  });
  
  describe('refreshToken', () => {
    let user;
    let refreshToken;
    
    beforeEach(async () => {
      user = await User.create(TestDataFactory.generateUser());
      refreshToken = tokenService.generateRefreshToken(user);
    });
    
    it('should refresh token successfully', async () => {
      const result = await authService.refreshToken(refreshToken);
      
      expect(result).toHaveProperty('accessToken');
      expect(result).toHaveProperty('refreshToken');
      expect(result.accessToken).not.toBeNull();
      expect(result.refreshToken).not.toBe(refreshToken);
      
      // Verify old refresh token is blacklisted
      const blacklisted = await BlacklistedToken.findOne({ token: refreshToken });
      expect(blacklisted).toBeTruthy();
    });
    
    it('should throw error with invalid refresh token', async () => {
      await expect(authService.refreshToken('invalid-token'))
        .rejects
        .toThrow('Invalid refresh token');
    });
    
    it('should throw error with expired refresh token', async () => {
      const expiredToken = jwt.sign(
        { id: user._id },
        process.env.JWT_REFRESH_SECRET,
        { expiresIn: '-1h' }
      );
      
      await expect(authService.refreshToken(expiredToken))
        .rejects
        .toThrow('Refresh token expired');
    });
  });
  
  describe('changePassword', () => {
    let user;
    let plainPassword;
    
    beforeEach(async () => {
      plainPassword = 'OldPassword123!';
      const hashedPassword = await bcrypt.hash(plainPassword, 10);
      user = await User.create({
        ...TestDataFactory.generateUser(),
        password: hashedPassword
      });
    });
    
    it('should change password successfully', async () => {
      const newPassword = 'NewPassword123!@#';
      
      const result = await authService.changePassword(
        user._id,
        plainPassword,
        newPassword
      );
      
      expect(result).toHaveProperty('success', true);
      
      // Verify new password works
      const updatedUser = await User.findById(user._id);
      const isValid = await bcrypt.compare(newPassword, updatedUser.password);
      expect(isValid).toBe(true);
    });
    
    it('should throw error with wrong current password', async () => {
      await expect(authService.changePassword(
        user._id,
        'WrongPassword123!',
        'NewPassword123!'
      )).rejects.toThrow('Current password is incorrect');
    });
    
    it('should validate new password strength', async () => {
      await expect(authService.changePassword(
        user._id,
        plainPassword,
        'weak'
      )).rejects.toThrow('New password too weak');
    });
    
    it('should not allow same password', async () => {
      await expect(authService.changePassword(
        user._id,
        plainPassword,
        plainPassword
      )).rejects.toThrow('New password must be different');
    });
  });
  
  describe('forgotPassword', () => {
    let user;
    
    beforeEach(async () => {
      user = await User.create(TestDataFactory.generateUser());
    });
    
    it('should send password reset email', async () => {
      const result = await authService.forgotPassword(user.email);
      
      expect(result).toHaveProperty('success', true);
      expect(emailService.sendPasswordReset).toHaveBeenCalled();
      
      // Verify reset token was created
      const updatedUser = await User.findById(user._id);
      expect(updatedUser.resetPasswordToken).toBeDefined();
      expect(updatedUser.resetPasswordExpires).toBeDefined();
    });
    
    it('should throw error for non-existent email', async () => {
      await expect(authService.forgotPassword('nonexistent@example.com'))
        .rejects
        .toThrow('No user found with this email');
    });
  });
  
  describe('resetPassword', () => {
    let user;
    let resetToken;
    
    beforeEach(async () => {
      user = await User.create(TestDataFactory.generateUser());
      resetToken = tokenService.generatePasswordResetToken(user);
      user.resetPasswordToken = resetToken;
      user.resetPasswordExpires = new Date(Date.now() + 3600000);
      await user.save();
    });
    
    it('should reset password successfully', async () => {
      const newPassword = 'NewPassword123!@#';
      
      const result = await authService.resetPassword(resetToken, newPassword);
      
      expect(result).toHaveProperty('success', true);
      
      // Verify new password works
      const updatedUser = await User.findById(user._id);
      const isValid = await bcrypt.compare(newPassword, updatedUser.password);
      expect(isValid).toBe(true);
      expect(updatedUser.resetPasswordToken).toBeNull();
      expect(updatedUser.resetPasswordExpires).toBeNull();
    });
    
    it('should throw error with invalid token', async () => {
      await expect(authService.resetPassword('invalid-token', 'NewPassword123!'))
        .rejects
        .toThrow('Invalid or expired token');
    });
    
    it('should throw error with expired token', async () => {
      user.resetPasswordExpires = new Date(Date.now() - 3600000);
      await user.save();
      
      await expect(authService.resetPassword(resetToken, 'NewPassword123!'))
        .rejects
        .toThrow('Invalid or expired token');
    });
  });
});