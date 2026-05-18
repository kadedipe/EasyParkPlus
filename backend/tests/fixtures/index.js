// parking-management/backend/tests/fixtures/index.js
const ModelsFixtures = require('./models');
const ApiFixtures = require('./api');
const DataFixtures = require('./data');
const Factories = require('./factories');
const Helpers = require('./helpers');

module.exports = {
  models: ModelsFixtures,
  api: ApiFixtures,
  data: DataFixtures,
  factories: Factories,
  helpers: Helpers,
  
  // Common test data
  common: {
    testEmail: 'test@example.com',
    testPassword: 'Test123!@#',
    testPhone: '+1234567890',
    testJwtSecret: 'test-jwt-secret-key',
    
    dates: {
      future: new Date(Date.now() + 86400000),
      past: new Date(Date.now() - 86400000),
      farFuture: new Date(Date.now() + 604800000),
      farPast: new Date(Date.now() - 604800000)
    },
    
    ids: {
      valid: '507f1f77bcf86cd799439011',
      invalid: 'invalid-id',
      nonExistent: '507f1f77bcf86cd799439999'
    }
  }
};