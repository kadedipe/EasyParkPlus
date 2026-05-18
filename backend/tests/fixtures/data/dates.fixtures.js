// parking-management/backend/tests/fixtures/data/dates.fixtures.js
const dateFixtures = {
  // Current date references
  now: new Date(),
  today: new Date().setHours(0, 0, 0, 0),
  tomorrow: new Date(Date.now() + 86400000),
  yesterday: new Date(Date.now() - 86400000),
  
  // Time ranges
  ranges: {
    morning: { start: '09:00', end: '11:00' },
    afternoon: { start: '13:00', end: '17:00' },
    evening: { start: '18:00', end: '22:00' },
    night: { start: '23:00', end: '05:00' },
    fullDay: { start: '00:00', end: '23:59' }
  },
  
  // Specific time periods
  periods: {
    oneHour: 3600000,
    twoHours: 7200000,
    fourHours: 14400000,
    eightHours: 28800000,
    oneDay: 86400000,
    oneWeek: 604800000,
    oneMonth: 2592000000,
    oneYear: 31536000000
  },
  
  // Holiday dates (for testing peak periods)
  holidays: {
    newYears: { month: 0, day: 1 },
    independence: { month: 6, day: 4 },
    thanksgiving: { month: 10, day: 4 }, // 4th Thursday of November
    christmas: { month: 11, day: 25 }
  },
  
  // Reservation test times
  reservationTimes: {
    futureReservation: {
      start: new Date(Date.now() + 86400000),
      end: new Date(Date.now() + 90000000)
    },
    pastReservation: {
      start: new Date(Date.now() - 86400000),
      end: new Date(Date.now() - 82800000)
    },
    activeReservation: {
      start: new Date(Date.now() - 1800000),
      end: new Date(Date.now() + 1800000)
    },
    overlappingReservation: {
      first: {
        start: new Date(Date.now() + 3600000),
        end: new Date(Date.now() + 7200000)
      },
      second: {
        start: new Date(Date.now() + 5400000),
        end: new Date(Date.now() + 9000000)
      }
    }
  },
  
  // Helper functions
  helpers: {
    addHours: (date, hours) => new Date(date.getTime() + hours * 3600000),
    addDays: (date, days) => new Date(date.getTime() + days * 86400000),
    isWeekend: (date) => date.getDay() === 0 || date.getDay() === 6,
    isBusinessHour: (date) => {
      const hour = date.getHours();
      return hour >= 9 && hour <= 17;
    }
  }
};

module.exports = dateFixtures;