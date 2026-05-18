// parking-management/backend/tests/fixtures/factories/model.factory.js
const { faker } = require('@faker-js/faker');
const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

class ModelFactory {
  static async createUser(overrides = {}) {
    const defaultUser = {
      email: faker.internet.email().toLowerCase(),
      password: await bcrypt.hash('Test123!@#', 10),
      firstName: faker.person.firstName(),
      lastName: faker.person.lastName(),
      phone: faker.phone.number('+1##########'),
      role: 'user',
      isActive: true,
      emailVerified: true,
      preferences: {
        notifications: true,
        language: 'en',
        timezone: 'America/New_York'
      }
    };
    
    return { ...defaultUser, ...overrides };
  }
  
  static async createParkingSpot(overrides = {}) {
    const defaultSpot = {
      name: `${faker.string.alpha(1).toUpperCase()}${faker.number.int({ min: 1, max: 100 })}`,
      location: {
        type: 'Point',
        coordinates: [
          faker.location.longitude({ min: -74.05, max: -73.95 }),
          faker.location.latitude({ min: 40.7, max: 40.8 })
        ],
        address: faker.location.streetAddress(),
        city: faker.location.city(),
        state: 'NY',
        zipCode: faker.location.zipCode()
      },
      type: faker.helpers.arrayElement(['standard', 'ev', 'disabled', 'motorcycle']),
      pricePerHour: faker.number.float({ min: 5, max: 30, precision: 0.01 }),
      status: 'available',
      amenities: faker.helpers.arrayElements(
        ['security', 'lighting', 'covered', 'ev_charger', 'cctv'],
        { min: 1, max: 3 }
      ),
      isActive: true
    };
    
    return { ...defaultSpot, ...overrides };
  }
  
  static async createReservation(userId, spotId, overrides = {}) {
    const startTime = faker.date.future({ years: 0.1 });
    const duration = faker.number.int({ min: 1, max: 4 });
    const endTime = new Date(startTime.getTime() + duration * 60 * 60 * 1000);
    
    const defaultReservation = {
      userId,
      spotId,
      startTime,
      endTime,
      vehicleNumber: faker.vehicle.vrm(),
      vehicleType: faker.helpers.arrayElement(['sedan', 'suv', 'truck', 'motorcycle']),
      status: 'confirmed',
      paymentStatus: 'pending',
      totalAmount: 0, // Will be calculated
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    return { ...defaultReservation, ...overrides };
  }
  
  static async createPayment(reservationId, overrides = {}) {
    const defaultPayment = {
      reservationId,
      amount: faker.number.float({ min: 10, max: 100, precision: 0.01 }),
      method: faker.helpers.arrayElement(['credit_card', 'debit_card', 'paypal', 'apple_pay']),
      status: 'completed',
      transactionId: `txn_${faker.string.alphanumeric(16)}`,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    return { ...defaultPayment, ...overrides };
  }
  
  static async createNotification(userId, overrides = {}) {
    const defaultNotification = {
      userId,
      type: faker.helpers.arrayElement(['reservation_reminder', 'payment_receipt', 'promotion', 'alert']),
      title: faker.lorem.sentence(),
      body: faker.lorem.paragraph(),
      read: false,
      priority: faker.helpers.arrayElement(['low', 'medium', 'high']),
      metadata: {
        action: faker.helpers.arrayElement(['view', 'pay', 'cancel']),
        resourceId: new mongoose.Types.ObjectId()
      },
      createdAt: new Date()
    };
    
    return { ...defaultNotification, ...overrides };
  }
  
  static async createAuditLog(userId, action, overrides = {}) {
    const defaultLog = {
      userId,
      action,
      resource: faker.helpers.arrayElement(['user', 'parking_spot', 'reservation', 'payment', 'settings']),
      resourceId: new mongoose.Types.ObjectId(),
      details: {
        ip: faker.internet.ip(),
        userAgent: faker.internet.userAgent(),
        timestamp: new Date()
      },
      severity: faker.helpers.arrayElement(['info', 'warning', 'error']),
      createdAt: new Date()
    };
    
    return { ...defaultLog, ...overrides };
  }
  
  static async createPromoCode(overrides = {}) {
    const defaultPromo = {
      code: faker.string.alphanumeric(8).toUpperCase(),
      type: faker.helpers.arrayElement(['percentage', 'fixed']),
      value: faker.number.float({ min: 5, max: 50 }),
      validFrom: faker.date.past(),
      validTo: faker.date.future(),
      usageLimit: faker.number.int({ min: 10, max: 1000 }),
      usedCount: 0,
      isActive: true,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    return { ...defaultPromo, ...overrides };
  }
  
  // Bulk create helpers
  static async createManyUsers(count, overrides = {}) {
    const users = [];
    for (let i = 0; i < count; i++) {
      users.push(await this.createUser(overrides));
    }
    return users;
  }
  
  static async createManyParkingSpots(count, overrides = {}) {
    const spots = [];
    for (let i = 0; i < count; i++) {
      spots.push(await this.createParkingSpot(overrides));
    }
    return spots;
  }
  
  static async createManyReservations(userId, spotId, count, overrides = {}) {
    const reservations = [];
    for (let i = 0; i < count; i++) {
      reservations.push(await this.createReservation(userId, spotId, overrides));
    }
    return reservations;
  }
}

module.exports = ModelFactory;