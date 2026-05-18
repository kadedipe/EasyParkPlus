// parking-management/backend/tests/fixtures/models/reservation.fixtures.js
const mongoose = require('mongoose');
const reservationFixtures = {
  // Active reservation
  active: {
    startTime: new Date(Date.now() + 3600000), // 1 hour from now
    endTime: new Date(Date.now() + 7200000),   // 2 hours from now
    vehicleNumber: 'ABC123',
    vehicleType: 'sedan',
    status: 'confirmed',
    paymentStatus: 'pending',
    totalAmount: 20.00
  },
  
  // Past reservation
  past: {
    startTime: new Date(Date.now() - 7200000), // 2 hours ago
    endTime: new Date(Date.now() - 3600000),   // 1 hour ago
    vehicleNumber: 'XYZ789',
    vehicleType: 'suv',
    status: 'completed',
    paymentStatus: 'paid',
    totalAmount: 15.00
  },
  
  // Cancelled reservation
  cancelled: {
    startTime: new Date(Date.now() + 86400000), // tomorrow
    endTime: new Date(Date.now() + 90000000),
    vehicleNumber: 'DEF456',
    vehicleType: 'truck',
    status: 'cancelled',
    paymentStatus: 'refunded',
    totalAmount: 30.00,
    cancelledAt: new Date(),
    cancellationReason: 'User cancelled'
  },
  
  // Ongoing reservation (currently active)
  ongoing: {
    startTime: new Date(Date.now() - 1800000), // 30 minutes ago
    endTime: new Date(Date.now() + 1800000),   // 30 minutes from now
    vehicleNumber: 'GHI789',
    vehicleType: 'sedan',
    status: 'active',
    paymentStatus: 'paid',
    totalAmount: 10.00
  },
  
  // Long-term reservation
  longTerm: {
    startTime: new Date(Date.now() + 86400000), // tomorrow
    endTime: new Date(Date.now() + 604800000),  // 7 days from now
    vehicleNumber: 'JKL012',
    vehicleType: 'suv',
    status: 'confirmed',
    paymentStatus: 'paid',
    totalAmount: 350.00
  },
  
  // Short-term reservation (30 minutes)
  shortTerm: {
    startTime: new Date(Date.now() + 1800000), // 30 minutes from now
    endTime: new Date(Date.now() + 3600000),   // 1 hour from now
    vehicleNumber: 'MNO345',
    vehicleType: 'motorcycle',
    status: 'confirmed',
    paymentStatus: 'pending',
    totalAmount: 5.00
  },
  
  // Reservation with promo code
  withPromo: {
    startTime: new Date(Date.now() + 86400000),
    endTime: new Date(Date.now() + 90000000),
    vehicleNumber: 'PQR678',
    vehicleType: 'sedan',
    status: 'confirmed',
    paymentStatus: 'pending',
    totalAmount: 18.00,
    promoCode: 'WELCOME10',
    discountApplied: 10
  },
  
  // Reservations for testing conflicts
  conflictScenarios: {
    overlapping: {
      first: {
        startTime: new Date(Date.now() + 3600000),
        endTime: new Date(Date.now() + 7200000)
      },
      second: {
        startTime: new Date(Date.now() + 5400000), // overlaps
        endTime: new Date(Date.now() + 9000000)
      }
    },
    adjacent: {
      first: {
        startTime: new Date(Date.now() + 3600000),
        endTime: new Date(Date.now() + 7200000)
      },
      second: {
        startTime: new Date(Date.now() + 7200000), // exactly adjacent
        endTime: new Date(Date.now() + 10800000)
      }
    },
    contained: {
      first: {
        startTime: new Date(Date.now() + 3600000),
        endTime: new Date(Date.now() + 10800000)
      },
      second: {
        startTime: new Date(Date.now() + 5400000), // inside first
        endTime: new Date(Date.now() + 9000000)
      }
    }
  },
  
  // Invalid reservation data
  invalid: {
    pastStartTime: {
      startTime: new Date(Date.now() - 3600000),
      endTime: new Date(Date.now() + 3600000),
      vehicleNumber: 'ABC123'
    },
    endBeforeStart: {
      startTime: new Date(Date.now() + 7200000),
      endTime: new Date(Date.now() + 3600000),
      vehicleNumber: 'ABC123'
    },
    missingVehicle: {
      startTime: new Date(Date.now() + 3600000),
      endTime: new Date(Date.now() + 7200000)
    },
    invalidDuration: {
      startTime: new Date(Date.now() + 3600000),
      endTime: new Date(Date.now() + 1800000), // 30 minutes (too short)
      vehicleNumber: 'ABC123'
    },
    tooLong: {
      startTime: new Date(Date.now() + 3600000),
      endTime: new Date(Date.now() + 604800000 * 2), // 14 days (too long)
      vehicleNumber: 'ABC123'
    }
  }
};

module.exports = reservationFixtures;