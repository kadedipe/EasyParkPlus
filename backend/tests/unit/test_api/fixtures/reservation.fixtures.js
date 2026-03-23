// parking-management/backend/tests/unit/test_api/fixtures/reservation.fixtures.js
module.exports = {
  validReservation: {
    vehicleNumber: 'ABC123',
    vehicleType: 'sedan',
    notes: 'Please park near entrance'
  },
  
  invalidReservations: [
    {
      vehicleNumber: 'INVALID',
      expectedError: 'vehicleNumber'
    },
    {
      startTime: new Date(Date.now() - 3600000).toISOString(),
      expectedError: 'startTime'
    },
    {
      startTime: new Date(Date.now() + 7200000).toISOString(),
      endTime: new Date(Date.now() + 3600000).toISOString(),
      expectedError: 'endTime'
    }
  ],
  
  testVehicles: [
    { number: 'ABC123', type: 'sedan' },
    { number: 'XYZ789', type: 'suv' },
    { number: 'DEF456', type: 'truck' },
    { number: 'GHI789', type: 'motorcycle' }
  ],
  
  promoCodes: [
    { code: 'WELCOME10', discount: 10, type: 'percentage' },
    { code: 'SAVE20', discount: 20, type: 'percentage' },
    { code: 'FLAT50', discount: 50, type: 'fixed' }
  ]
};