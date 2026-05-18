// parking-management/backend/tests/unit/test_services/helpers/test-data-factory.js
const { faker } = require('@faker-js/faker');
const mongoose = require('mongoose');

class TestDataFactory {
  static generateUser(overrides = {}) {
    return {
      email: faker.internet.email().toLowerCase(),
      password: 'Test123!@#',
      firstName: faker.person.firstName(),
      lastName: faker.person.lastName(),
      phone: faker.phone.number('+1##########'),
      role: 'user',
      isActive: true,
      emailVerified: true,
      ...overrides
    };
  }
  
  static generateAdmin(overrides = {}) {
    return this.generateUser({
      role: 'admin',
      ...overrides
    });
  }
  
  static generateParkingSpot(overrides = {}) {
    return {
      name: `${faker.string.alpha(1).toUpperCase()}${faker.number.int({ min: 1, max: 100 })}`,
      location: {
        type: 'Point',
        coordinates: [
          faker.location.longitude({ min: -74.05, max: -73.95 }),
          faker.location.latitude({ min: 40.7, max: 40.8 })
        ],
        address: faker.location.streetAddress(),
        city: faker.location.city(),
        state: faker.location.state(),
        zipCode: faker.location.zipCode()
      },
      type: faker.helpers.arrayElement(['standard', 'ev', 'disabled', 'motorcycle', 'compact']),
      pricePerHour: faker.number.float({ min: 5, max: 30, precision: 0.01 }),
      status: 'available',
      amenities: faker.helpers.arrayElements(
        ['security', 'lighting', 'covered', 'ev_charger', 'handicap_access', 'cctv', '24_7_access'],
        { min: 1, max: 4 }
      ),
      capacity: faker.number.int({ min: 1, max: 10 }),
      dimensions: {
        width: faker.number.float({ min: 8, max: 12, precision: 0.5 }),
        length: faker.number.float({ min: 16, max: 20, precision: 0.5 })
      },
      ...overrides
    };
  }
  
  static generateReservation(userId, spotId, overrides = {}) {
    const startTime = faker.date.future({ years: 0.1 });
    const duration = faker.number.int({ min: 1, max: 4 });
    const endTime = new Date(startTime.getTime() + duration * 60 * 60 * 1000);
    
    return {
      userId,
      spotId,
      startTime,
      endTime,
      vehicleNumber: faker.vehicle.vrm(),
      vehicleType: faker.helpers.arrayElement(['sedan', 'suv', 'truck', 'motorcycle']),
      status: 'confirmed',
      totalAmount: faker.number.float({ min: 10, max: 100, precision: 0.01 }),
      ...overrides
    };
  }
  
  static generatePayment(reservationId, overrides = {}) {
    return {
      reservationId,
      amount: faker.number.float({ min: 10, max: 100, precision: 0.01 }),
      method: faker.helpers.arrayElement(['credit_card', 'debit_card', 'paypal', 'apple_pay']),
      status: faker.helpers.arrayElement(['pending', 'completed', 'failed']),
      transactionId: `txn_${faker.string.alphanumeric(16)}`,
      ...overrides
    };
  }
  
  static generateNotification(userId, overrides = {}) {
    return {
      userId,
      type: faker.helpers.arrayElement(['reservation_reminder', 'payment_receipt', 'promotion', 'alert', 'system']),
      title: faker.lorem.sentence(),
      body: faker.lorem.paragraph(),
      read: false,
      priority: faker.helpers.arrayElement(['low', 'medium', 'high']),
      metadata: {
        action: faker.helpers.arrayElement(['view', 'pay', 'cancel', 'extend']),
        resourceId: new mongoose.Types.ObjectId()
      },
      ...overrides
    };
  }
  
  static generatePromoCode(overrides = {}) {
    return {
      code: faker.string.alphanumeric(8).toUpperCase(),
      type: faker.helpers.arrayElement(['percentage', 'fixed']),
      value: faker.number.float({ min: 5, max: 50 }),
      validFrom: faker.date.past(),
      validTo: faker.date.future(),
      usageLimit: faker.number.int({ min: 10, max: 1000 }),
      usedCount: 0,
      isActive: true,
      ...overrides
    };
  }
  
  static generateAuditLog(userId, action, overrides = {}) {
    return {
      userId,
      action,
      resource: faker.helpers.arrayElement(['user', 'parking_spot', 'reservation', 'payment', 'settings']),
      resourceId: new mongoose.Types.ObjectId(),
      details: {
        ip: faker.internet.ip(),
        userAgent: faker.internet.userAgent(),
        changes: overrides.changes || {}
      },
      severity: faker.helpers.arrayElement(['info', 'warning', 'error']),
      ...overrides
    };
  }
  
  static generateReport(overrides = {}) {
    return {
      type: faker.helpers.arrayElement(['revenue', 'occupancy', 'user_activity', 'maintenance']),
      period: faker.helpers.arrayElement(['daily', 'weekly', 'monthly', 'yearly']),
      startDate: faker.date.past(),
      endDate: faker.date.recent(),
      generatedBy: new mongoose.Types.ObjectId(),
      data: {},
      format: 'json',
      ...overrides
    };
  }
}

module.exports = TestDataFactory;