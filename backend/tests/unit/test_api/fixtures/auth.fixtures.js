// parking-management/backend/tests/unit/test_api/fixtures/auth.fixtures.js
module.exports = {
  validCredentials: {
    email: 'test@example.com',
    password: 'Test123!@#',
    firstName: 'Test',
    lastName: 'User',
    phone: '+1234567890'
  },
  
  invalidCredentials: [
    {
      email: 'test@example.com',
      password: 'wrong',
      expectedError: 'password'
    },
    {
      email: 'invalid-email',
      password: 'Test123!@#',
      expectedError: 'email'
    },
    {
      email: '',
      password: 'Test123!@#',
      expectedError: 'email'
    }
  ],
  
  weakPasswords: [
    '123456',
    'password',
    'qwerty',
    'abc123',
    'password123'
  ],
  
  testTokens: {
    expired: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjEyMzQ1Njc4OTAiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJleHAiOjE2MDAwMDAwMDB9.signature',
    invalid: 'invalid.token.here'
  }
};