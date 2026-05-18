// parking-management/backend/tests/e2e/helpers/test-data-factory.js
const { faker } = require('@faker-js/faker');

class TestDataFactory {
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
  
  static generateParkingSpot(overrides = {}) {
    return {
      name: `${faker.string.alpha(1).toUpperCase()}${faker.number.int({ min: 1, max: 100 })}`,
      location: {
        latitude: faker.location.latitude({ min: 40.7, max: 40.8 }),
        longitude: faker.location.longitude({ min: -74.05, max: -73.95 }),
        address: faker.location.streetAddress(),
        city: faker.location.city(),
        state: 'NY',
        zipCode: faker.location.zipCode()
      },
      type: faker.helpers.arrayElement(['standard', 'ev', 'disabled', 'motorcycle']),
      pricePerHour: faker.number.float({ min: 5, max: 30, precision: 0.01 }),
      amenities: faker.helpers.arrayElements(
        ['security', 'lighting', 'covered', 'ev_charger', 'cctv'],
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
      vehicleType: faker.helpers.arrayElement(['sedan', 'suv', 'truck']),
      ...overrides
    };
  }
  
  static generatePayment(reservationId, overrides = {}) {
    return {
      reservationId,
      amount: faker.number.float({ min: 10, max: 100, precision: 0.01 }),
      method: faker.helpers.arrayElement(['credit_card', 'paypal', 'apple_pay']),
      cardDetails: {
        number: '4111111111111111',
        expiry: '12/25',
        cvv: '123',
        name: faker.person.fullName()
      },
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
  
  static generatePromoCode(overrides = {}) {
    return {
      code: faker.string.alphanumeric(8).toUpperCase(),
      type: faker.helpers.arrayElement(['percentage', 'fixed']),
      value: faker.number.float({ min: 5, max: 50 }),
      validFrom: faker.date.past(),
      validTo: faker.date.future(),
      ...overrides
    };
  }
}

module.exports = TestDataFactory;