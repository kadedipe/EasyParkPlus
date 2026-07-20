// parking-management/backend/tests/e2e/auth/auth-flow.test.js
const E2EClient = require('../helpers/e2e-client');
const TestDataFactory = require('../helpers/test-data-factory');

describe('Authentication E2E Flow', () => {
  let client;
  
  beforeEach(() => {
    client = new E2EClient();
  });
  
  describe('Complete User Registration and Login Flow', () => {
    it('should register, login, and access protected routes', async () => {
      // Step 1: Register new user
      const userData = TestDataFactory.generateUser();
      const registerResponse = await client.register(userData);
      
      expect(registerResponse.status).toBe(201);
      expect(registerResponse.body).toHaveProperty('success', true);
      expect(registerResponse.body.data).toHaveProperty('token');
      expect(registerResponse.body.data.user).toHaveProperty('email', userData.email);
      
      // Step 2: Login with registered user
      const loginResponse = await client.login(userData.email, userData.password);
      
      expect(loginResponse.status).toBe(200);
      expect(loginResponse.body.data).toHaveProperty('token');
      expect(loginResponse.body.data).toHaveProperty('refreshToken');
      
      // Step 3: Access protected profile endpoint
      const profileResponse = await client.getProfile();
      
      expect(profileResponse.status).toBe(200);
      expect(profileResponse.body.data).toHaveProperty('email', userData.email);
      expect(profileResponse.body.data).toHaveProperty('firstName', userData.firstName);
      
      // Step 4: Logout
      const logoutResponse = await client.logout();
      
      expect(logoutResponse.status).toBe(200);
      
      // Step 5: Verify token is invalidated
      const invalidProfileResponse = await client.getProfile();
      expect(invalidProfileResponse.status).toBe(401);
    });
    
    it('should handle password reset flow', async () => {
      // Step 1: Register user
      const userData = TestDataFactory.generateUser();
      await client.register(userData);
      
      // Step 2: Request password reset
      const forgotResponse = await client.forgotPassword(userData.email);
      expect(forgotResponse.status).toBe(200);
      
      // Step 3: Get reset token (simulate email)
      const user = await User.findOne({ email: userData.email });
      const resetToken = user.resetPasswordToken;
      
      // Step 4: Reset password
      const newPassword = 'NewPassword456!@#';
      const resetResponse = await client.resetPassword(resetToken, newPassword);
      expect(resetResponse.status).toBe(200);
      
      // Step 5: Login with new password
      const loginResponse = await client.login(userData.email, newPassword);
      expect(loginResponse.status).toBe(200);
      
      // Step 6: Old password should not work
      const oldLoginResponse = await client.login(userData.email, userData.password);
      expect(oldLoginResponse.status).toBe(401);
    });
    
    it('should handle token refresh flow', async () => {
      // Step 1: Register and login
      const userData = TestDataFactory.generateUser();
      await client.register(userData);
      await client.login(userData.email, userData.password);
      
      const originalToken = client.authToken;
      const refreshToken = client.refreshToken;
      
      // Step 2: Wait a bit (simulate token age)
      await client.wait(1000);
      
      // Step 3: Refresh token
      const refreshResponse = await client.refreshToken();
      expect(refreshResponse.status).toBe(200);
      expect(refreshResponse.body.data.token).not.toBe(originalToken);
      
      // Step 4: Verify new token works
      const profileResponse = await client.getProfile();
      expect(profileResponse.status).toBe(200);
      
      // Step 5: Verify old token is invalid
      client.setAuthToken(originalToken);
      const oldTokenResponse = await client.getProfile();
      expect(oldTokenResponse.status).toBe(401);
    });
    
    it('should lock account after multiple failed attempts', async () => {
      // Step 1: Register user
      const userData = TestDataFactory.generateUser();
      await client.register(userData);
      
      // Step 2: Attempt multiple failed logins
      for (let i = 0; i < 5; i++) {
        const failedResponse = await client.login(userData.email, 'WrongPassword123!');
        expect(failedResponse.status).toBe(401);
      }
      
      // Step 3: Account should be locked
      const lockResponse = await client.login(userData.email, userData.password);
      expect(lockResponse.status).toBe(423);
      expect(lockResponse.body).toHaveProperty('message', 'Account locked. Try again later');
      
      // Step 4: Wait for lock duration (simulate)
      await client.wait(300000); // 5 minutes
      
      // Step 5: Should be able to login after lock expires
      const unlockResponse = await client.login(userData.email, userData.password);
      expect(unlockResponse.status).toBe(200);
    });
  });
});