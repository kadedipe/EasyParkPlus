// parking-management/backend/tests/e2e/helpers/global-setup.js
const { MongoMemoryServer } = require('mongodb-memory-server');
const mongoose = require('mongoose');
const redis = require('redis-mock');
const { app } = require('../../../src/app');

let mongod;
let server;

module.exports = async () => {
  // Start in-memory MongoDB
  mongod = await MongoMemoryServer.create();
  const uri = mongod.getUri();
  
  await mongoose.connect(uri, {
    useNewUrlParser: true,
    useUnifiedTopology: true
  });
  
  // Mock Redis
  const redisClient = redis.createClient();
  global.__REDIS_CLIENT__ = redisClient;
  
  // Start test server
  const port = process.env.TEST_PORT || 3001;
  server = app.listen(port);
  global.__TEST_SERVER__ = server;
  global.__TEST_PORT__ = port;
  
  // Set environment variables
  process.env.NODE_ENV = 'test';
  process.env.JWT_SECRET = 'e2e-test-secret-key';
  process.env.JWT_REFRESH_SECRET = 'e2e-test-refresh-key';
  process.env.TEST_MODE = 'true';
  
  // Create test directories
  const fs = require('fs-extra');
  const path = require('path');
  const testUploads = path.join(__dirname, '../uploads');
  const testLogs = path.join(__dirname, '../logs');
  
  await fs.ensureDir(testUploads);
  await fs.ensureDir(testLogs);
  
  global.__TEST_UPLOAD_DIR__ = testUploads;
  
  console.log(`E2E test server running on port ${port}`);
};

module.exports.teardown = async () => {
  await mongoose.disconnect();
  await global.__TEST_SERVER__.close();
  await global.__REDIS_CLIENT__.quit();
  
  // Clean up test directories
  const fs = require('fs-extra');
  await fs.remove(global.__TEST_UPLOAD_DIR__);
};