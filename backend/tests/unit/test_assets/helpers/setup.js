// parking-management/backend/tests/unit/test_assets/helpers/setup.js
const mongoose = require('mongoose');
const { MongoMemoryServer } = require('mongodb-memory-server');
const fs = require('fs-extra');
const path = require('path');
const { app } = require('../../../../src/app');
const request = require('supertest');

let mongod;

// Test directories
const TEST_UPLOAD_DIR = path.join(__dirname, '../uploads');
const TEST_TEMP_DIR = path.join(__dirname, '../temp');
const TEST_IMAGE_DIR = path.join(__dirname, '../images');
const TEST_DOCUMENT_DIR = path.join(__dirname, '../documents');

// Global test variables
global.testApp = app;
global.testRequest = request;
global.testUploadDir = TEST_UPLOAD_DIR;
global.testTempDir = TEST_TEMP_DIR;

// Setup before all tests
beforeAll(async () => {
  // Create in-memory MongoDB
  mongod = await MongoMemoryServer.create();
  const uri = mongod.getUri();
  
  await mongoose.connect(uri, {
    useNewUrlParser: true,
    useUnifiedTopology: true
  });
  
  // Create test directories
  await fs.ensureDir(TEST_UPLOAD_DIR);
  await fs.ensureDir(TEST_TEMP_DIR);
  await fs.ensureDir(TEST_IMAGE_DIR);
  await fs.ensureDir(TEST_DOCUMENT_DIR);
  
  // Set test environment
  process.env.NODE_ENV = 'test';
  process.env.UPLOAD_DIR = TEST_UPLOAD_DIR;
  process.env.MAX_FILE_SIZE = '5242880'; // 5MB
  process.env.ALLOWED_IMAGE_TYPES = 'image/jpeg,image/png,image/gif,image/webp';
  process.env.ALLOWED_DOCUMENT_TYPES = 'application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  process.env.JWT_SECRET = 'test-secret-key';
});

// Cleanup after all tests
afterAll(async () => {
  await mongoose.disconnect();
  await mongod.stop();
  
  // Clean up test directories
  await fs.remove(TEST_UPLOAD_DIR);
  await fs.remove(TEST_TEMP_DIR);
  await fs.remove(TEST_IMAGE_DIR);
  await fs.remove(TEST_DOCUMENT_DIR);
});

// Clean database and temp files after each test
afterEach(async () => {
  const collections = mongoose.connection.collections;
  for (const key in collections) {
    await collections[key].deleteMany();
  }
  
  // Clean temp files
  const tempFiles = await fs.readdir(TEST_TEMP_DIR);
  for (const file of tempFiles) {
    await fs.remove(path.join(TEST_TEMP_DIR, file));
  }
});