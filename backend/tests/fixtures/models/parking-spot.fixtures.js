// parking-management/backend/tests/fixtures/models/parking-spot.fixtures.js
const parkingSpotFixtures = {
  // Standard parking spot
  standard: {
    name: 'A1',
    location: {
      type: 'Point',
      coordinates: [-74.0060, 40.7128],
      address: '123 Main Street',
      city: 'New York',
      state: 'NY',
      zipCode: '10001',
      country: 'USA'
    },
    type: 'standard',
    pricePerHour: 10.00,
    status: 'available',
    amenities: ['security', 'lighting', 'cctv'],
    dimensions: {
      width: 8.5,
      length: 18.0
    },
    isActive: true
  },
  
  // EV charging spot
  ev: {
    name: 'EV1',
    location: {
      type: 'Point',
      coordinates: [-74.0065, 40.7130],
      address: '124 Main Street',
      city: 'New York',
      state: 'NY',
      zipCode: '10001'
    },
    type: 'ev',
    pricePerHour: 15.00,
    status: 'available',
    amenities: ['security', 'lighting', 'ev_charger', 'cctv'],
    evCharger: {
      type: 'level2',
      power: 7.2,
      connector: 'J1772'
    },
    isActive: true
  },
  
  // Disabled parking spot
  disabled: {
    name: 'D1',
    location: {
      type: 'Point',
      coordinates: [-74.0070, 40.7125],
      address: '125 Main Street',
      city: 'New York',
      state: 'NY',
      zipCode: '10001'
    },
    type: 'disabled',
    pricePerHour: 10.00,
    status: 'available',
    amenities: ['security', 'lighting', 'handicap_access', 'wide_space'],
    dimensions: {
      width: 12.0,
      length: 20.0
    },
    isActive: true
  },
  
  // Motorcycle spot
  motorcycle: {
    name: 'M1',
    location: {
      type: 'Point',
      coordinates: [-74.0075, 40.7135],
      address: '126 Main Street',
      city: 'New York',
      state: 'NY',
      zipCode: '10001'
    },
    type: 'motorcycle',
    pricePerHour: 5.00,
    status: 'available',
    amenities: ['security', 'motorcycle_stand'],
    dimensions: {
      width: 4.0,
      length: 8.0
    },
    isActive: true
  },
  
  // Occupied spot
  occupied: {
    name: 'O1',
    location: {
      type: 'Point',
      coordinates: [-74.0080, 40.7140],
      address: '127 Main Street',
      city: 'New York',
      state: 'NY',
      zipCode: '10001'
    },
    type: 'standard',
    pricePerHour: 12.00,
    status: 'occupied',
    currentReservation: null,
    amenities: ['security', 'lighting'],
    isActive: true
  },
  
  // Under maintenance
  maintenance: {
    name: 'MNT1',
    location: {
      type: 'Point',
      coordinates: [-74.0085, 40.7145],
      address: '128 Main Street',
      city: 'New York',
      state: 'NY',
      zipCode: '10001'
    },
    type: 'standard',
    pricePerHour: 8.00,
    status: 'maintenance',
    amenities: ['security'],
    maintenanceHistory: [
      {
        startDate: new Date(),
        reason: 'Regular maintenance',
        estimatedEndDate: new Date(Date.now() + 86400000)
      }
    ],
    isActive: true
  },
  
  // Premium spot (higher price)
  premium: {
    name: 'P1',
    location: {
      type: 'Point',
      coordinates: [-74.0090, 40.7150],
      address: '129 Main Street',
      city: 'New York',
      state: 'NY',
      zipCode: '10001'
    },
    type: 'standard',
    pricePerHour: 25.00,
    status: 'available',
    amenities: ['security', 'lighting', 'cctv', 'covered', 'valet'],
    isPremium: true,
    isActive: true
  },
  
  // Multiple spots for bulk operations
  bulk: [
    {
      name: 'B1',
      location: { type: 'Point', coordinates: [-74.0100, 40.7160] },
      type: 'standard',
      pricePerHour: 10.00,
      status: 'available'
    },
    {
      name: 'B2',
      location: { type: 'Point', coordinates: [-74.0110, 40.7170] },
      type: 'standard',
      pricePerHour: 12.00,
      status: 'available'
    },
    {
      name: 'B3',
      location: { type: 'Point', coordinates: [-74.0120, 40.7180] },
      type: 'ev',
      pricePerHour: 15.00,
      status: 'available'
    }
  ],
  
  // Invalid spot data
  invalid: {
    missingName: {
      location: {
        type: 'Point',
        coordinates: [-74.0060, 40.7128]
      },
      pricePerHour: 10.00
    },
    invalidPrice: {
      name: 'Invalid',
      location: {
        type: 'Point',
        coordinates: [-74.0060, 40.7128]
      },
      pricePerHour: -5.00
    },
    invalidLocation: {
      name: 'Invalid',
      location: {
        type: 'Invalid',
        coordinates: []
      },
      pricePerHour: 10.00
    }
  }
};

module.exports = parkingSpotFixtures;