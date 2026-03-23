// parking-management/backend/tests/unit/test_api/helpers/setup.js
const mongoose = require('mongoose');
const { MongoMemoryServer } = require('mongodb-memory-server');
const { app } = require('../../../../src/app');
const request = require('supertest');

let mongod;

// Global test variables
global.testApp = app;
global.testRequest = request;

// Setup before all tests
beforeAll(async () => {
  // Create in-memory MongoDB
  mongod = await MongoMemoryServer.create();
  const uri = mongod.getUri();
  
  await mongoose.connect(uri, {
    useNewUrlParser: true,
    useUnifiedTopology: true
  });
  
  // Set test environment
  process.env.NODE_ENV = 'test';
  process.env.JWT_SECRET = 'test-secret-key';
  process.env.JWT_EXPIRES_IN = '1h';
  process.env.PORT = 3001;
});

// Cleanup after all tests
afterAll(async () => {
  await mongoose.disconnect();
  await mongod.stop();
});

// Clean database after each test
afterEach(async () => {
  const collections = mongoose.connection.collections;
  for (const key in collections) {
    await collections[key].deleteMany();
  }
});