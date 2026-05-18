// parking-management/backend/tests/fixtures/data/vehicles.fixtures.js
const vehicleFixtures = {
  // Sedans
  sedans: [
    {
      plateNumber: 'SED001',
      make: 'Toyota',
      model: 'Camry',
      year: 2022,
      color: 'Silver',
      type: 'sedan',
      vin: '1HGBH41JXMN109186'
    },
    {
      plateNumber: 'SED002',
      make: 'Honda',
      model: 'Accord',
      year: 2023,
      color: 'Black',
      type: 'sedan'
    },
    {
      plateNumber: 'SED003',
      make: 'Tesla',
      model: 'Model 3',
      year: 2023,
      color: 'Red',
      type: 'sedan',
      isElectric: true
    }
  ],
  
  // SUVs
  suvs: [
    {
      plateNumber: 'SUV001',
      make: 'Ford',
      model: 'Explorer',
      year: 2022,
      color: 'Blue',
      type: 'suv'
    },
    {
      plateNumber: 'SUV002',
      make: 'Toyota',
      model: 'RAV4',
      year: 2023,
      color: 'White',
      type: 'suv'
    },
    {
      plateNumber: 'SUV003',
      make: 'Tesla',
      model: 'Model Y',
      year: 2023,
      color: 'Gray',
      type: 'suv',
      isElectric: true
    }
  ],
  
  // Trucks
  trucks: [
    {
      plateNumber: 'TRK001',
      make: 'Ford',
      model: 'F-150',
      year: 2022,
      color: 'Red',
      type: 'truck'
    },
    {
      plateNumber: 'TRK002',
      make: 'Ram',
      model: '1500',
      year: 2023,
      color: 'Black',
      type: 'truck'
    }
  ],
  
  // Motorcycles
  motorcycles: [
    {
      plateNumber: 'MOTO01',
      make: 'Harley-Davidson',
      model: 'Street Glide',
      year: 2022,
      color: 'Orange',
      type: 'motorcycle'
    },
    {
      plateNumber: 'MOTO02',
      make: 'Yamaha',
      model: 'R6',
      year: 2023,
      color: 'Blue',
      type: 'motorcycle'
    }
  ],
  
  // Electric vehicles
  electric: [
    {
      plateNumber: 'EV001',
      make: 'Tesla',
      model: 'Model S',
      year: 2023,
      color: 'White',
      type: 'sedan',
      isElectric: true,
      batteryCapacity: 100
    },
    {
      plateNumber: 'EV002',
      make: 'Ford',
      model: 'Mustang Mach-E',
      year: 2023,
      color: 'Red',
      type: 'suv',
      isElectric: true,
      batteryCapacity: 88
    },
    {
      plateNumber: 'EV003',
      make: 'Hyundai',
      model: 'Ioniq 5',
      year: 2023,
      color: 'Teal',
      type: 'suv',
      isElectric: true,
      batteryCapacity: 77
    }
  ],
  
  // Invalid vehicles for validation testing
  invalid: [
    {
      // Missing plate number
      make: 'Toyota',
      model: 'Camry',
      year: 2022
    },
    {
      // Invalid year
      plateNumber: 'INV001',
      make: 'Toyota',
      model: 'Camry',
      year: 1899
    },
    {
      // Future year
      plateNumber: 'INV002',
      make: 'Toyota',
      model: 'Camry',
      year: 2030
    }
  ],
  
  // Default vehicle for testing
  default: {
    plateNumber: 'DEF123',
    make: 'Default',
    model: 'Vehicle',
    year: 2023,
    color: 'White',
    type: 'sedan'
  }
};

module.exports = vehicleFixtures;