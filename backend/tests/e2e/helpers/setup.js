// parking-management/backend/tests/e2e/helpers/setup.js
const request = require('supertest');
const mongoose = require('mongoose');
const { app } = require('../../../src/app');
const E2EClient = require('./e2e-client');
const TestDataFactory = require('./test-data-factory');
const { User, ParkingSpot, Reservation, Payment } = require('../../../src/models');

// Global test utilities
global.request = request;
global.app = app;
global.E2EClient = E2EClient;
global.TestDataFactory = TestDataFactory;

// Clean database between tests
beforeEach(async () => {
  const collections = mongoose.connection.collections;
  for (const key in collections) {
    await collections[key].deleteMany();
  }
});

afterEach(async () => {
  // Clear any pending timeouts or intervals
  jest.clearAllTimers();
});

// Global test helpers
global.createTestUser = async (overrides = {}) => {
  const userData = TestDataFactory.generateUser(overrides);
  const response = await request(app)
    .post('/api/auth/register')
    .send(userData);
  
  return {
    user: response.body.data.user,
    token: response.body.data.token,
    password: userData.password
  };
};

global.createTestAdmin = async () => {
  return createTestUser({ role: 'admin' });
};

global.createTestParkingSpot = async (adminToken, overrides = {}) => {
  const spotData = TestDataFactory.generateParkingSpot(overrides);
  const response = await request(app)
    .post('/api/parking-spots')
    .set('Authorization', `Bearer ${adminToken}`)
    .send(spotData);
  
  return response.body.data;
};

global.cleanupTestData = async () => {
  await User.deleteMany({});
  await ParkingSpot.deleteMany({});
  await Reservation.deleteMany({});
  await Payment.deleteMany({});
};