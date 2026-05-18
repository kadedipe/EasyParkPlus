// parking-management/backend/tests/fixtures/models/user.fixtures.js
const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

const userFixtures = {
  // Valid user data
  valid: {
    email: 'john.doe@example.com',
    password: 'Test123!@#',
    firstName: 'John',
    lastName: 'Doe',
    phone: '+1234567890',
    role: 'user',
    isActive: true,
    emailVerified: true,
    preferences: {
      notifications: true,
      language: 'en',
      timezone: 'America/New_York'
    }
  },
  
  admin: {
    email: 'admin@parking.com',
    password: 'Admin123!@#',
    firstName: 'Admin',
    lastName: 'User',
    phone: '+1987654321',
    role: 'admin',
    isActive: true,
    emailVerified: true,
    preferences: {
      notifications: true,
      language: 'en',
      timezone: 'America/New_York'
    }
  },
  
  manager: {
    email: 'manager@parking.com',
    password: 'Manager123!@#',
    firstName: 'Manager',
    lastName: 'User',
    phone: '+1122334455',
    role: 'manager',
    isActive: true,
    emailVerified: true
  },
  
  // Invalid user data
  invalid: {
    missingEmail: {
      password: 'Test123!@#',
      firstName: 'No',
      lastName: 'Email'
    },
    invalidEmail: {
      email: 'invalid-email',
      password: 'Test123!@#',
      firstName: 'Invalid',
      lastName: 'Email'
    },
    weakPassword: {
      email: 'weak@example.com',
      password: 'weak',
      firstName: 'Weak',
      lastName: 'Password'
    },
    missingRequired: {
      email: 'missing@example.com',
      password: 'Test123!@#'
      // missing firstName and lastName
    }
  },
  
  // Users with specific properties
  withVehicle: {
    email: 'with.vehicle@example.com',
    password: 'Vehicle123!@#',
    firstName: 'Vehicle',
    lastName: 'Owner',
    phone: '+1234567890',
    vehicles: [
      {
        plateNumber: 'ABC123',
        make: 'Tesla',
        model: 'Model 3',
        year: 2023,
        color: 'Red',
        isDefault: true
      }
    ]
  },
  
  withPaymentMethod: {
    email: 'payment.user@example.com',
    password: 'Payment123!@#',
    firstName: 'Payment',
    lastName: 'User',
    paymentMethods: [
      {
        type: 'credit_card',
        last4: '4242',
        expiryMonth: 12,
        expiryYear: 2025,
        isDefault: true
      }
    ]
  },
  
  inactive: {
    email: 'inactive@example.com',
    password: 'Inactive123!@#',
    firstName: 'Inactive',
    lastName: 'User',
    isActive: false,
    deactivatedAt: new Date()
  },
  
  locked: {
    email: 'locked@example.com',
    password: 'Locked123!@#',
    firstName: 'Locked',
    lastName: 'User',
    isLocked: true,
    lockUntil: new Date(Date.now() + 3600000),
    loginAttempts: 5
  },
  
  // Pre-hashed passwords for testing
  preHashed: async () => {
    const salt = await bcrypt.genSalt(10);
    const hashedPassword = await bcrypt.hash('Test123!@#', salt);
    
    return {
      email: 'prehashed@example.com',
      password: hashedPassword,
      firstName: 'Prehashed',
      lastName: 'User'
    };
  }
};

module.exports = userFixtures;