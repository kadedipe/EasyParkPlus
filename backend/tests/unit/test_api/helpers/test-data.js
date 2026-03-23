// parking-management/backend/tests/unit/test_api/helpers/test-data.js
const { faker } = require('@faker-js/faker');

class TestDataGenerator {
  static generateUser(overrides = {}) {
    return {
      email: faker.internet.email().toLowerCase(),
      password: 'Test123!@#',
      firstName: faker.person.firstName(),
      lastName: faker.person.lastName(),
      phone: faker.phone.number('+1##########'),
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
        latitude: faker.location.latitude({ min: 40.7, max: 40.8 }),
        longitude: faker.location.longitude({ min: -74.05, max: -73.95 }),
        address: faker.location.streetAddress()
      },
      type: faker.helpers.arrayElement(['standard', 'ev', 'disabled', 'motorcycle', 'compact']),
      pricePerHour: faker.number.float({ min: 5, max: 30, precision: 0.01 }),
      status: 'available',
      amenities: faker.helpers.arrayElements(
        ['security', 'lighting', 'covered', 'ev_charger', 'handicap_access', 'cctv'],
        { min: 1, max: 3 }
      ),
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
      startTime: startTime.toISOString(),
      endTime: endTime.toISOString(),
      vehicleNumber: faker.vehicle.vrm(),
      ...overrides
    };
  }
  
  static generatePayment(reservationId, overrides = {}) {
    return {
      reservationId,
      amount: faker.number.float({ min: 10, max: 100, precision: 0.01 }),
      method: faker.helpers.arrayElement(['credit_card', 'debit_card', 'paypal', 'apple_pay']),
      ...overrides
    };
  }
  
  static generateVehicle(overrides = {}) {
    return {
      plateNumber: faker.vehicle.vrm(),
      make: faker.vehicle.manufacturer(),
      model: faker.vehicle.model(),
      year: faker.number.int({ min: 2000, max: 2024 }),
      color: faker.vehicle.color(),
      ...overrides
    };
  }
  
  static generateReview(userId, spotId, overrides = {}) {
    return {
      userId,
      spotId,
      rating: faker.number.int({ min: 1, max: 5 }),
      comment: faker.lorem.paragraph(),
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
      ...overrides
    };
  }
  
  static generateNotification(userId, overrides = {}) {
    return {
      userId,
      type: faker.helpers.arrayElement(['reservation_reminder', 'payment_receipt', 'promotion', 'alert']),
      title: faker.lorem.sentence(),
      body: faker.lorem.paragraph(),
      read: false,
      ...overrides
    };
  }
  
  static generateAuditLog(userId, action, overrides = {}) {
    return {
      userId,
      action,
      resource: faker.helpers.arrayElement(['user', 'parking_spot', 'reservation', 'payment']),
      resourceId: new mongoose.Types.ObjectId(),
      details: { ip: faker.internet.ip(), userAgent: faker.internet.userAgent() },
      ...overrides
    };
  }
}

module.exports = TestDataGenerator;