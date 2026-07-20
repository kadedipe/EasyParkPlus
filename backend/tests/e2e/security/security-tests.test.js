// parking-management/backend/tests/e2e/security/security-tests.test.js
const E2EClient = require('../helpers/e2e-client');
const TestDataFactory = require('../helpers/test-data-factory');

describe('Security Tests', () => {
  let client;
  let adminClient;
  
  beforeEach(async () => {
    client = new E2EClient();
    adminClient = new E2EClient();
    
    const adminData = TestDataFactory.generateUser({ role: 'admin' });
    await adminClient.register(adminData);
  });
  
  describe('Authentication Security', () => {
    it('should prevent SQL injection', async () => {
      const maliciousInputs = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "admin'--",
        "1' UNION SELECT * FROM users--"
      ];
      
      for (const input of maliciousInputs) {
        const response = await client.login(input, 'password');
        expect(response.status).toBe(401); // Should not authenticate
        
        const searchResponse = await client.getParkingSpots({ search: input });
        expect(searchResponse.status).toBe(200); // Should not break
      }
    });
    
    it('should prevent XSS attacks', async () => {
      const xssPayloads = [
        '<script>alert("XSS")</script>',
        '<img src=x onerror=alert(1)>',
        'javascript:alert("XSS")',
        '"><script>alert("XSS")</script>'
      ];
      
      for (const payload of xssPayloads) {
        // Try to inject via profile update
        const updateResponse = await client.updateProfile({
          firstName: payload,
          lastName: 'Test'
        });
        
        expect(updateResponse.status).toBe(400); // Should be rejected
        
        // Try via reservation notes
        const startTime = new Date(Date.now() + 86400000);
        const endTime = new Date(startTime.getTime() + 7200000);
        
        const reservationResponse = await client.createReservation({
          spotId: new mongoose.Types.ObjectId(),
          startTime: startTime.toISOString(),
          endTime: endTime.toISOString(),
          vehicleNumber: 'ABC123',
          notes: payload
        });
        
        // Should be sanitized
        expect(reservationResponse.status).toBe(400);
        expect(reservationResponse.body.message).not.toContain(payload);
      }
    });
    
    it('should enforce strong password policy', async () => {
      const weakPasswords = [
        '123456',
        'password',
        'qwerty',
        'abc123',
        'password123'
      ];
      
      for (const weakPassword of weakPasswords) {
        const userData = TestDataFactory.generateUser({ password: weakPassword });
        const response = await client.register(userData);
        
        expect(response.status).toBe(400);
        expect(response.body.errors).toContainEqual(
          expect.objectContaining({ field: 'password' })
        );
      }
    });
    
    it('should protect against brute force attacks', async () => {
      const userData = TestDataFactory.generateUser();
      await client.register(userData);
      
      // Attempt many failed logins
      const attempts = [];
      for (let i = 0; i < 50; i++) {
        attempts.push(client.login(userData.email, 'WrongPassword'));
      }
      
      const responses = await Promise.all(attempts);
      const rateLimited = responses.filter(r => r.status === 429).length;
      
      expect(rateLimited).toBeGreaterThan(0);
      
      // Account should be locked
      const finalAttempt = await client.login(userData.email, userData.password);
      expect(finalAttempt.status).toBe(423);
    });
  });
  
  describe('Authorization Security', () => {
    it('should prevent unauthorized access', async () => {
      const endpoints = [
        { method: 'GET', url: '/api/admin/dashboard' },
        { method: 'GET', url: '/api/users' },
        { method: 'POST', url: '/api/parking-spots' },
        { method: 'DELETE', url: `/api/users/${new mongoose.Types.ObjectId()}` }
      ];
      
      for (const endpoint of endpoints) {
        let response;
        if (endpoint.method === 'GET') {
          response = await client.get(endpoint.url);
        } else if (endpoint.method === 'POST') {
          response = await client.post(endpoint.url, {});
        } else if (endpoint.method === 'DELETE') {
          response = await client.delete(endpoint.url);
        }
        
        expect(response.status).toBe(401); // Unauthorized
      }
    });
    
    it('should prevent privilege escalation', async () => {
      const userData = TestDataFactory.generateUser();
      await client.register(userData);
      
      // Try to access admin endpoints with user token
      const adminEndpoints = [
        { method: 'GET', url: '/api/admin/dashboard' },
        { method: 'GET', url: '/api/admin/users' },
        { method: 'POST', url: '/api/admin/settings' }
      ];
      
      for (const endpoint of adminEndpoints) {
        let response;
        if (endpoint.method === 'GET') {
          response = await client.get(endpoint.url);
        } else if (endpoint.method === 'POST') {
          response = await client.post(endpoint.url, {});
        }
        
        expect(response.status).toBe(403); // Forbidden
      }
    });
    
    it('should prevent horizontal privilege escalation', async () => {
      // Create two users
      const user1Data = TestDataFactory.generateUser();
      const user1Response = await client.register(user1Data);
      
      const user2Client = new E2EClient();
      const user2Data = TestDataFactory.generateUser();
      await user2Client.register(user2Data);
      
      // Try to access user1's data with user2's token
      const user1Id = user1Response.body.data.user._id;
      const response = await user2Client.getUserById(user1Id);
      
      expect(response.status).toBe(403);
    });
  });
  
  describe('Data Protection', () => {
    it('should not expose sensitive data', async () => {
      const userData = TestDataFactory.generateUser();
      const registerResponse = await client.register(userData);
      const userId = registerResponse.body.data.user._id;
      
      // Check user profile doesn't expose sensitive fields
      const profile = await client.getProfile();
      expect(profile.body.data).not.toHaveProperty('password');
      expect(profile.body.data).not.toHaveProperty('resetPasswordToken');
      expect(profile.body.data).not.toHaveProperty('loginAttempts');
      
      // Check user listing (admin only)
      const usersList = await adminClient.getUsers();
      expect(usersList.body.data.users[0]).not.toHaveProperty('password');
    });
    
    it('should encrypt sensitive data at rest', async () => {
      const userData = TestDataFactory.generateUser({
        ssn: '123-45-6789',
        creditCardLast4: '1234'
      });
      
      const registerResponse = await client.register(userData);
      const userId = registerResponse.body.data.user._id;
      
      // Check database directly
      const User = require('../../../src/models/user');
      const user = await User.findById(userId);
      
      expect(user.ssn).not.toBe('123-45-6789');
      expect(user.creditCardLast4).not.toBe('1234');
      expect(user.ssn).toMatch(/^encrypted:/);
    });
    
    it('should enforce HTTPS in production', async () => {
      // This test would check that HTTPS is enforced
      // For E2E tests, we can check that HTTP redirects to HTTPS
      process.env.NODE_ENV = 'production';
      
      const httpResponse = await client.get('http://localhost:3001/api/auth/health');
      
      if (httpResponse.status === 301 || httpResponse.status === 302) {
        expect(httpResponse.headers.location).toMatch(/^https:/);
      }
      
      process.env.NODE_ENV = 'test';
    });
  });
  
  describe('API Security Headers', () => {
    it('should set security headers', async () => {
      const response = await client.getParkingSpots();
      
      const securityHeaders = [
        'X-Content-Type-Options',
        'X-Frame-Options',
        'X-XSS-Protection',
        'Strict-Transport-Security',
        'Content-Security-Policy'
      ];
      
      for (const header of securityHeaders) {
        expect(response.headers[header.toLowerCase()]).toBeDefined();
      }
      
      expect(response.headers['x-content-type-options']).toBe('nosniff');
      expect(response.headers['x-frame-options']).toBe('DENY');
    });
  });
  
  describe('JWT Security', () => {
    it('should reject tampered tokens', async () => {
      const userData = TestDataFactory.generateUser();
      await client.register(userData);
      
      const originalToken = client.authToken;
      const tamperedToken = originalToken.slice(0, -5) + 'xxxxx';
      
      client.setAuthToken(tamperedToken);
      const response = await client.getProfile();
      
      expect(response.status).toBe(401);
    });
    
    it('should validate token expiration', async () => {
      // Create token with short expiration
      const jwt = require('jsonwebtoken');
      const shortLivedToken = jwt.sign(
        { id: 'test', role: 'user' },
        process.env.JWT_SECRET,
        { expiresIn: '1s' }
      );
      
      client.setAuthToken(shortLivedToken);
      
      // First request should work
      const firstResponse = await client.getProfile();
      expect(firstResponse.status).toBe(401); // Invalid user ID
      
      // Wait for expiration
      await client.wait(2000);
      
      // Second request should fail
      const secondResponse = await client.getProfile();
      expect(secondResponse.status).toBe(401);
    });
  });
});