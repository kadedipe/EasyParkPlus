// parking-management/backend/tests/fixtures/data/locations.fixtures.js
const locationFixtures = {
  // NYC locations
  nyc: {
    timesSquare: {
      latitude: 40.7580,
      longitude: -73.9855,
      address: 'Times Square, New York, NY',
      city: 'New York',
      state: 'NY',
      zipCode: '10036'
    },
    centralPark: {
      latitude: 40.7851,
      longitude: -73.9683,
      address: 'Central Park, New York, NY',
      city: 'New York',
      state: 'NY',
      zipCode: '10022'
    },
    brooklyn: {
      latitude: 40.6782,
      longitude: -73.9442,
      address: 'Brooklyn Bridge Park, Brooklyn, NY',
      city: 'Brooklyn',
      state: 'NY',
      zipCode: '11201'
    },
    jfkAirport: {
      latitude: 40.6413,
      longitude: -73.7781,
      address: 'JFK Airport, Queens, NY',
      city: 'Queens',
      state: 'NY',
      zipCode: '11430'
    }
  },
  
  // San Francisco locations
  sf: {
    unionSquare: {
      latitude: 37.7880,
      longitude: -122.4075,
      address: 'Union Square, San Francisco, CA',
      city: 'San Francisco',
      state: 'CA',
      zipCode: '94108'
    },
    fishermanWharf: {
      latitude: 37.8080,
      longitude: -122.4177,
      address: 'Fisherman\'s Wharf, San Francisco, CA',
      city: 'San Francisco',
      state: 'CA',
      zipCode: '94133'
    },
    goldenGate: {
      latitude: 37.8199,
      longitude: -122.4783,
      address: 'Golden Gate Bridge, San Francisco, CA',
      city: 'San Francisco',
      state: 'CA',
      zipCode: '94129'
    }
  },
  
  // LA locations
  la: {
    hollywood: {
      latitude: 34.0928,
      longitude: -118.3287,
      address: 'Hollywood Boulevard, Los Angeles, CA',
      city: 'Los Angeles',
      state: 'CA',
      zipCode: '90028'
    },
    santaMonica: {
      latitude: 34.0195,
      longitude: -118.4912,
      address: 'Santa Monica Pier, Santa Monica, CA',
      city: 'Santa Monica',
      state: 'CA',
      zipCode: '90401'
    }
  },
  
  // Test locations (nearby for radius tests)
  testCluster: {
    center: {
      latitude: 40.7128,
      longitude: -74.0060
    },
    nearby: [
      { latitude: 40.7130, longitude: -74.0062, distance: 25 },
      { latitude: 40.7135, longitude: -74.0065, distance: 80 },
      { latitude: 40.7140, longitude: -74.0070, distance: 150 }
    ],
    far: [
      { latitude: 40.7200, longitude: -74.0150, distance: 1000 },
      { latitude: 40.7300, longitude: -74.0250, distance: 2000 }
    ]
  },
  
  // Boundaries for geofencing
  boundaries: {
    manhattan: {
      north: 40.8797,
      south: 40.6795,
      east: -73.9038,
      west: -74.0413
    },
    downtown: {
      north: 40.7282,
      south: 40.7008,
      east: -73.9840,
      west: -74.0145
    }
  }
};

module.exports = locationFixtures;