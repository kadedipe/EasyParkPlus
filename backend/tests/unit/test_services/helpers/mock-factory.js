// parking-management/backend/tests/unit/test_services/helpers/mock-factory.js
class MockFactory {
  static createMockUser(overrides = {}) {
    return {
      _id: '507f1f77bcf86cd799439011',
      email: 'test@example.com',
      password: 'hashedPassword123',
      firstName: 'Test',
      lastName: 'User',
      phone: '+1234567890',
      role: 'user',
      isActive: true,
      emailVerified: true,
      createdAt: new Date(),
      updatedAt: new Date(),
      save: jest.fn().mockResolvedValue(true),
      toJSON: jest.fn().mockReturnValue({
        _id: '507f1f77bcf86cd799439011',
        email: 'test@example.com',
        firstName: 'Test',
        lastName: 'User'
      }),
      comparePassword: jest.fn(),
      ...overrides
    };
  }
  
  static createMockParkingSpot(overrides = {}) {
    return {
      _id: '507f1f77bcf86cd799439012',
      name: 'A1',
      location: {
        type: 'Point',
        coordinates: [-74.0060, 40.7128],
        address: '123 Test St'
      },
      type: 'standard',
      pricePerHour: 10,
      status: 'available',
      amenities: ['security', 'lighting'],
      isActive: true,
      createdAt: new Date(),
      updatedAt: new Date(),
      save: jest.fn().mockResolvedValue(true),
      ...overrides
    };
  }
  
  static createMockReservation(overrides = {}) {
    return {
      _id: '507f1f77bcf86cd799439013',
      userId: '507f1f77bcf86cd799439011',
      spotId: '507f1f77bcf86cd799439012',
      startTime: new Date(Date.now() + 3600000),
      endTime: new Date(Date.now() + 7200000),
      vehicleNumber: 'ABC123',
      status: 'confirmed',
      totalAmount: 20,
      createdAt: new Date(),
      updatedAt: new Date(),
      save: jest.fn().mockResolvedValue(true),
      populate: jest.fn().mockReturnThis(),
      ...overrides
    };
  }
  
  static createMockPayment(overrides = {}) {
    return {
      _id: '507f1f77bcf86cd799439014',
      reservationId: '507f1f77bcf86cd799439013',
      amount: 20,
      method: 'credit_card',
      status: 'completed',
      transactionId: 'txn_test_123',
      createdAt: new Date(),
      updatedAt: new Date(),
      save: jest.fn().mockResolvedValue(true),
      ...overrides
    };
  }
  
  static createMockRequest(overrides = {}) {
    return {
      user: { id: '507f1f77bcf86cd799439011', role: 'user' },
      body: {},
      params: {},
      query: {},
      headers: {},
      ip: '127.0.0.1',
      ...overrides
    };
  }
  
  static createMockResponse() {
    const res = {};
    res.status = jest.fn().mockReturnValue(res);
    res.json = jest.fn().mockReturnValue(res);
    res.send = jest.fn().mockReturnValue(res);
    res.setHeader = jest.fn().mockReturnValue(res);
    return res;
  }
  
  static createMockNext() {
    return jest.fn();
  }
}

module.exports = MockFactory;