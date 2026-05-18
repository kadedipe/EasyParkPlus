// parking-management/backend/tests/e2e/jest.config.js
module.exports = {
  testEnvironment: 'node',
  rootDir: '../..',
  testMatch: [
    '**/tests/e2e/**/*.test.js',
    '**/tests/e2e/**/*.spec.js'
  ],
  setupFilesAfterEnv: ['<rootDir>/tests/e2e/helpers/setup.js'],
  testTimeout: 60000,
  globalSetup: '<rootDir>/tests/e2e/helpers/global-setup.js',
  globalTeardown: '<rootDir>/tests/e2e/helpers/global-teardown.js',
  collectCoverageFrom: [
    'src/**/*.js',
    '!src/**/*.test.js',
    '!src/server.js'
  ],
  coverageDirectory: 'coverage/e2e',
  verbose: true,
  bail: false,
  forceExit: true,
  detectOpenHandles: true
};