// parking-management/backend/tests/unit/test_api/jest.config.js
module.exports = {
  // Test environment
  testEnvironment: 'node',
  
  // Root directory
  rootDir: '../../..',
  
  // Test match patterns
  testMatch: [
    '**/tests/unit/test_api/**/*.test.js',
    '**/tests/unit/test_api/**/*.spec.js'
  ],
  
  // Setup files
  setupFilesAfterEnv: ['<rootDir>/tests/unit/test_api/helpers/setup.js'],
  
  // Test timeout
  testTimeout: 30000,
  
  // Coverage configuration
  collectCoverageFrom: [
    'src/controllers/**/*.js',
    'src/routes/**/*.js',
    'src/middleware/**/*.js',
    '!src/**/*.test.js'
  ],
  
  coverageDirectory: 'coverage/api-tests',
  
  // Verbose output
  verbose: true,
  
  // Clear mocks between tests
  clearMocks: true,
  resetMocks: true,
  restoreMocks: true
};