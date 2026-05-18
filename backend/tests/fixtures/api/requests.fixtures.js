// parking-management/backend/tests/fixtures/api/requests.fixtures.js
const requestFixtures = {
  // Auth requests
  auth: {
    validRegister: {
      email: 'newuser@example.com',
      password: 'Test123!@#',
      firstName: 'New',
      lastName: 'User',
      phone: '+1234567890'
    },
    validLogin: {
      email: 'existing@example.com',
      password: 'Test123!@#'
    },
    invalidLogin: {
      email: 'wrong@example.com',
      password: 'wrongpassword'
    },
    changePassword: {
      currentPassword: 'OldPassword123!',
      newPassword: 'NewPassword456!@#'
    },
    forgotPassword: {
      email: 'reset@example.com'
    },
    resetPassword: {
      token: 'reset-token-123',
      newPassword: 'ResetPassword123!'
    }
  },
  
  // User requests
  users: {
    updateProfile: {
      firstName: 'Updated',
      lastName: 'Name',
      phone: '+1987654321',
      preferences: {
        notifications: true,
        language: 'es',
        timezone: 'America/Los_Angeles'
      }
    },
    updateVehicle: {
      plateNumber: 'XYZ789',
      make: 'Honda',
      model: 'Civic',
      year: 2022,
      color: 'Blue'
    },
    addPaymentMethod: {
      type: 'credit_card',
      cardNumber: '4111111111111111',
      expiryMonth: 12,
      expiryYear: 2025,
      cvv: '123',
      nameOnCard: 'John Doe'
    }
  },
  
  // Parking spot requests
  parkingSpots: {
    create: {
      name: 'New Spot',
      location: {
        latitude: 40.7128,
        longitude: -74.0060,
        address: '123 Test Ave'
      },
      type: 'standard',
      pricePerHour: 15.00,
      amenities: ['security', 'lighting']
    },
    update: {
      pricePerHour: 20.00,
      status: 'maintenance'
    },
    search: {
      lat: 40.7128,
      lng: -74.0060,
      radius: 1000,
      type: 'ev',
      minPrice: 10,
      maxPrice: 25,
      amenities: ['security', 'cctv']
    }
  },
  
  // Reservation requests
  reservations: {
    create: {
      startTime: new Date(Date.now() + 86400000).toISOString(),
      endTime: new Date(Date.now() + 90000000).toISOString(),
      vehicleNumber: 'ABC123',
      vehicleType: 'sedan',
      notes: 'Please park near elevator'
    },
    extend: {
      newEndTime: new Date(Date.now() + 10800000).toISOString()
    },
    filter: {
      status: 'confirmed',
      startDate: new Date().toISOString(),
      endDate: new Date(Date.now() + 604800000).toISOString()
    }
  },
  
  // Payment requests
  payments: {
    creditCard: {
      method: 'credit_card',
      cardDetails: {
        number: '4111111111111111',
        expiry: '12/25',
        cvv: '123',
        name: 'John Doe'
      }
    },
    paypal: {
      method: 'paypal',
      email: 'user@example.com'
    },
    applePay: {
      method: 'apple_pay',
      token: 'apple_pay_token_123'
    }
  },
  
  // Admin requests
  admin: {
    updateSettings: {
      maxReservationDuration: 48,
      cancellationWindow: 2,
      defaultPricePerHour: 12.50,
      maintenanceMode: false
    },
    generateReport: {
      type: 'revenue',
      period: 'monthly',
      startDate: new Date(Date.now() - 2592000000).toISOString(),
      endDate: new Date().toISOString(),
      format: 'json'
    }
  }
};

module.exports = requestFixtures;