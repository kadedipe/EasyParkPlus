// parking-management/backend/tests/unit/test_assets/jest.config.js
module.exports = {
  testEnvironment: 'node',
  rootDir: '../../..',
  testMatch: [
    '**/tests/unit/test_assets/**/*.test.js',
    '**/tests/unit/test_assets/**/*.spec.js'
  ],
  setupFilesAfterEnv: ['<rootDir>/tests/unit/test_assets/helpers/setup.js'],
  testTimeout: 30000,
  collectCoverageFrom: [
    'src/services/asset.service.js',
    'src/services/upload.service.js',
    'src/services/image.service.js',
    'src/controllers/asset.controller.js',
    'src/middleware/upload.middleware.js',
    '!src/**/*.test.js'
  ],
  coverageDirectory: 'coverage/assets-tests',
  verbose: true,
  clearMocks: true,
  resetMocks: true,
  restoreMocks: true,
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@assets/(.*)$': '<rootDir>/src/assets/$1',
    '^@uploads/(.*)$': '<rootDir>/uploads/$1'
  }
};