// parking-management/backend/tests/fixtures/models/index.js
const userFixtures = require('./user.fixtures');
const parkingSpotFixtures = require('./parking-spot.fixtures');
const reservationFixtures = require('./reservation.fixtures');
const paymentFixtures = require('./payment.fixtures');

module.exports = {
  users: userFixtures,
  parkingSpots: parkingSpotFixtures,
  reservations: reservationFixtures,
  payments: paymentFixtures
};