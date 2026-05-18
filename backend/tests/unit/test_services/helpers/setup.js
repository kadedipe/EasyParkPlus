// parking-management/backend/tests/unit/test_services/helpers/setup.js
const mongoose = require('mongoose');
const { MongoMemoryServer } = require('mongodb-memory-server');
const redis = require('redis-mock');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');

let mongod;

// Mock Redis
jest.mock('redis', () => redis);
jest.mock('ioredis', () => require('redis-mock'));

// Mock Email Service
jest.mock('../../../src/services/email.service', () => {
  return jest.fn().mockImplementation(() => ({
    sendEmail: jest.fn().mockResolvedValue(true),
    sendWelcomeEmail: jest.fn().mockResolvedValue(true),
    sendPasswordReset: jest.fn().mockResolvedValue(true),
    sendReservationConfirmation: jest.fn().mockResolvedValue(true),
    sendPaymentReceipt: jest.fn().mockResolvedValue(true)
  }));
});

// Mock Payment Gateway
jest.mock('../../../src/services/payment.service', () => {
  return jest.fn().mockImplementation(() => ({
    processPayment: jest.fn().mockResolvedValue({
      success: true,
      transactionId: 'txn_test_123',
      amount: 100
    }),
    refundPayment: jest.fn().mockResolvedValue({
      success: true,
      refundId: 'ref_123'
    })
  }));
});

// Mock SMS Service
jest.mock('../../../src/services/sms.service', () => {
  return jest.fn().mockImplementation(() => ({
    sendSMS: jest.fn().mockResolvedValue({ success: true, messageId: 'sms_123' })
  }));
});

// Mock Cache Service
jest.mock('../../../src/services/cache.service', () => {
  return jest.fn().mockImplementation(() => ({
    get: jest.fn(),
    set: jest.fn().mockResolvedValue(true),
    del: jest.fn().mockResolvedValue(true),
    flush: jest.fn().mockResolvedValue(true)
  }));
});

beforeAll(async () => {
  mongod = await MongoMemoryServer.create();
  const uri = mongod.getUri();
  
  await mongoose.connect(uri, {
    useNewUrlParser: true,
    useUnifiedTopology: true
  });
  
  process.env.NODE_ENV = 'test';
  process.env.JWT_SECRET = 'test-secret-key';
  process.env.JWT_REFRESH_SECRET = 'test-refresh-secret-key';
  process.env.ENCRYPTION_KEY = 'test-encryption-key-32-chars-long!!!';
});

afterAll(async () => {
  await mongoose.disconnect();
  await mongod.stop();
});

afterEach(async () => {
  const collections = mongoose.connection.collections;
  for (const key in collections) {
    await collections[key].deleteMany();
  }
  jest.clearAllMocks();
});

// Global test helpers
global.generateTestToken = (userId, role = 'user') => {
  return jwt.sign(
    { id: userId, role },
    process.env.JWT_SECRET,
    { expiresIn: '1h' }
  );
};

global.hashPassword = async (password) => {
  return await bcrypt.hash(password, 10);
};