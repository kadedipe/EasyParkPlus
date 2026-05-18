// parking-management/backend/tests/unit/test_services/jest.config.js
module.exports = {
  testEnvironment: 'node',
  rootDir: '../../..',
  testMatch: [
    '**/tests/unit/test_services/**/*.test.js',
    '**/tests/unit/test_services/**/*.spec.js'
  ],
  setupFilesAfterEnv: ['<rootDir>/tests/unit/test_services/helpers/setup.js'],
  testTimeout: 30000,
  collectCoverageFrom: [
    'src/services/*.js',
    '!src/services/index.js',
    '!src/services/__mocks__/*.js'
  ],
  coverageThreshold: {
    global: {
      branches: 85,
      functions: 90,
      lines: 90,
      statements: 90
    }
  },
  coverageDirectory: 'coverage/services',
  verbose: true,
  clearMocks: true,
  resetMocks: true,
  restoreMocks: true
};