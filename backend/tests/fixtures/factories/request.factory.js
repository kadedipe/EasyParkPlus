// parking-management/backend/tests/fixtures/factories/request.factory.js
const { faker } = require('@faker-js/faker');

class RequestFactory {
  static createAuthRequest(overrides = {}) {
    return {
      email: faker.internet.email().toLowerCase(),
      password: 'Test123!@#',
      firstName: faker.person.firstName(),
      lastName: faker.person.lastName(),
      phone: faker.phone.number('+1##########'),
      ...overrides
    };
  }
  
  static createLoginRequest(overrides = {}) {
    return {
      email: faker.internet.email().toLowerCase(),
      password: 'Test123!@#',
      ...overrides
    };
  }
  
  static createParkingSpotRequest(overrides = {}) {
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
  
  static createReservationRequest(spotId, overrides = {}) {
    const startTime = faker.date.future({ years: 0.1 });
    const duration = faker.number.int({ min: 1, max: 4 });
    const endTime = new Date(startTime.getTime() + duration * 60 * 60 * 1000);
    
    return {
      spotId,
      startTime: startTime.toISOString(),
      endTime: endTime.toISOString(),
      vehicleNumber: faker.vehicle.vrm(),
      vehicleType: faker.helpers.arrayElement(['sedan', 'suv', 'truck', 'motorcycle']),
      notes: faker.lorem.sentence(),
      ...overrides
    };
  }
  
  static createPaymentRequest(reservationId, overrides = {}) {
    return {
      reservationId,
      amount: faker.number.float({ min: 10, max: 100, precision: 0.01 }),
      method: faker.helpers.arrayElement(['credit_card', 'debit_card', 'paypal', 'apple_pay']),
      cardDetails: {
        number: '4111111111111111',
        expiry: '12/25',
        cvv: '123',
        name: faker.person.fullName()
      },
      ...overrides
    };
  }
  
  static createProfileUpdateRequest(overrides = {}) {
    return {
      firstName: faker.person.firstName(),
      lastName: faker.person.lastName(),
      phone: faker.phone.number('+1##########'),
      preferences: {
        notifications: faker.datatype.boolean(),
        language: faker.helpers.arrayElement(['en', 'es', 'fr']),
        timezone: 'America/New_York'
      },
      ...overrides
    };
  }
  
  static createVehicleRequest(overrides = {}) {
    return {
      plateNumber: faker.vehicle.vrm(),
      make: faker.vehicle.manufacturer(),
      model: faker.vehicle.model(),
      year: faker.number.int({ min: 2000, max: 2024 }),
      color: faker.vehicle.color(),
      type: faker.helpers.arrayElement(['sedan', 'suv', 'truck', 'motorcycle']),
      ...overrides
    };
  }
  
  static createReviewRequest(spotId, overrides = {}) {
    return {
      spotId,
      rating: faker.number.int({ min: 1, max: 5 }),
      comment: faker.lorem.paragraph(),
      ...overrides
    };
  }
  
  static createQueryParams(overrides = {}) {
    return {
      page: faker.number.int({ min: 1, max: 10 }),
      limit: faker.number.int({ min: 10, max: 100 }),
      sortBy: faker.helpers.arrayElement(['createdAt', 'price', 'name']),
      sortOrder: faker.helpers.arrayElement(['asc', 'desc']),
      ...overrides
    };
  }
}

module.exports = RequestFactory;