// parking-management/backend/tests/e2e/workflows/complete-user-journey.test.js
const E2EClient = require('../helpers/e2e-client');
const TestDataFactory = require('../helpers/test-data-factory');

describe('Complete User Journey', () => {
  let client;
  let adminClient;
  let testSpot;
  
  beforeAll(async () => {
    adminClient = new E2EClient();
    const adminData = TestDataFactory.generateUser({ role: 'admin' });
    await adminClient.register(adminData);
    
    // Create test parking spot
    const spotData = TestDataFactory.generateParkingSpot();
    const spotResponse = await adminClient.createParkingSpot(spotData);
    testSpot = spotResponse.body.data;
  });
  
  it('should complete full user journey: registration to reservation completion', async () => {
    const journeyStart = Date.now();
    client = new E2EClient();
    
    // Step 1: User Registration
    console.log('Step 1: User Registration');
    const userData = TestDataFactory.generateUser();
    const registerResponse = await client.register(userData);
    
    expect(registerResponse.status).toBe(201);
    expect(registerResponse.body.data.user.email).toBe(userData.email);
    
    // Step 2: Login
    console.log('Step 2: Login');
    const loginResponse = await client.login(userData.email, userData.password);
    
    expect(loginResponse.status).toBe(200);
    expect(loginResponse.body.data).toHaveProperty('token');
    
    // Step 3: Update Profile
    console.log('Step 3: Update Profile');
    const profileUpdates = {
      firstName: 'Updated',
      lastName: 'Name',
      phone: '+19876543210',
      preferences: {
        notifications: true,
        language: 'es'
      }
    };
    
    const profileResponse = await client.updateProfile(profileUpdates);
    
    expect(profileResponse.status).toBe(200);
    expect(profileResponse.body.data.firstName).toBe(profileUpdates.firstName);
    
    // Step 4: Add Vehicle
    console.log('Step 4: Add Vehicle');
    const vehicleData = TestDataFactory.generateVehicle();
    const vehicleResponse = await client.addVehicle(vehicleData);
    
    expect(vehicleResponse.status).toBe(201);
    expect(vehicleResponse.body.data).toHaveProperty('plateNumber', vehicleData.plateNumber);
    
    // Step 5: Search Parking Spots
    console.log('Step 5: Search Parking Spots');
    const spotsResponse = await client.getParkingSpots({
      lat: testSpot.location.latitude,
      lng: testSpot.location.longitude,
      radius: 1000,
      status: 'available'
    });
    
    expect(spotsResponse.status).toBe(200);
    expect(spotsResponse.body.data.spots.length).toBeGreaterThan(0);
    
    // Step 6: Select Spot and Check Availability
    console.log('Step 6: Check Availability');
    const startTime = new Date(Date.now() + 86400000); // tomorrow
    const endTime = new Date(startTime.getTime() + 7200000); // 2 hours later
    
    const availabilityResponse = await client.getParkingSpotById(testSpot._id, {
      startTime: startTime.toISOString(),
      endTime: endTime.toISOString()
    });
    
    expect(availabilityResponse.body.data.availability.isAvailable).toBe(true);
    
    // Step 7: Create Reservation
    console.log('Step 7: Create Reservation');
    const reservationData = {
      spotId: testSpot._id,
      startTime: startTime.toISOString(),
      endTime: endTime.toISOString(),
      vehicleNumber: vehicleData.plateNumber,
      vehicleType: vehicleData.type
    };
    
    const reservationResponse = await client.createReservation(reservationData);
    
    expect(reservationResponse.status).toBe(201);
    expect(reservationResponse.body.data).toHaveProperty('status', 'confirmed');
    expect(reservationResponse.body.data).toHaveProperty('totalAmount');
    
    const reservation = reservationResponse.body.data;
    
    // Step 8: View Reservation Details
    console.log('Step 8: View Reservation Details');
    const detailsResponse = await client.getReservationById(reservation._id);
    
    expect(detailsResponse.status).toBe(200);
    expect(detailsResponse.body.data).toHaveProperty('spot');
    expect(detailsResponse.body.data.spot).toHaveProperty('name');
    
    // Step 9: Process Payment
    console.log('Step 9: Process Payment');
    const paymentData = {
      reservationId: reservation._id,
      amount: reservation.totalAmount,
      method: 'credit_card',
      cardDetails: {
        number: '4111111111111111',
        expiry: '12/25',
        cvv: '123',
        name: 'Test User'
      }
    };
    
    const paymentResponse = await client.processPayment(paymentData);
    
    expect(paymentResponse.status).toBe(201);
    expect(paymentResponse.body.data).toHaveProperty('status', 'completed');
    
    // Step 10: Get Payment Receipt
    console.log('Step 10: Get Payment Receipt');
    const receiptResponse = await client.getPaymentStatus(paymentResponse.body.data._id);
    
    expect(receiptResponse.status).toBe(200);
    expect(receiptResponse.body.data).toHaveProperty('transactionId');
    
    // Step 11: Extend Reservation
    console.log('Step 11: Extend Reservation');
    const newEndTime = new Date(endTime.getTime() + 3600000); // +1 hour
    const extendResponse = await client.extendReservation(reservation._id, newEndTime.toISOString());
    
    expect(extendResponse.status).toBe(200);
    expect(new Date(extendResponse.body.data.endTime).getTime()).toBe(newEndTime.getTime());
    
    // Step 12: Process Additional Payment
    console.log('Step 12: Process Additional Payment');
    const additionalAmount = extendResponse.body.data.additionalCharge;
    
    const additionalPayment = await client.processPayment({
      reservationId: reservation._id,
      amount: additionalAmount,
      method: 'credit_card',
      cardDetails: {
        number: '4111111111111111',
        expiry: '12/25',
        cvv: '123'
      }
    });
    
    expect(additionalPayment.status).toBe(201);
    
    // Step 13: View Reservation History
    console.log('Step 13: View Reservation History');
    const historyResponse = await client.getReservations({
      startDate: new Date(Date.now() - 86400000).toISOString(),
      endDate: new Date(Date.now() + 86400000 * 7).toISOString()
    });
    
    expect(historyResponse.status).toBe(200);
    expect(historyResponse.body.data.reservations.length).toBeGreaterThan(0);
    
    // Step 14: Cancel Reservation (if needed)
    console.log('Step 14: Cancel Reservation');
    const cancelResponse = await client.cancelReservation(reservation._id);
    
    expect(cancelResponse.status).toBe(200);
    expect(cancelResponse.body.data).toHaveProperty('status', 'cancelled');
    expect(cancelResponse.body.data).toHaveProperty('refund');
    
    // Step 15: Verify Refund
    console.log('Step 15: Verify Refund');
    const finalPaymentStatus = await client.getPaymentStatus(paymentResponse.body.data._id);
    expect(finalPaymentStatus.body.data.status).toBe('refunded');
    
    const journeyEnd = Date.now();
    const journeyDuration = (journeyEnd - journeyStart) / 1000;
    
    console.log(`Complete user journey completed in ${journeyDuration} seconds`);
    
    // Final assertions
    expect(journeyDuration).toBeLessThan(60000); // Should complete within 60 seconds
  });
  
  it('should handle concurrent user journeys', async () => {
    const numUsers = 5;
    const journeys = [];
    
    console.log(`Starting ${numUsers} concurrent user journeys`);
    
    // Create multiple users and run journeys in parallel
    for (let i = 0; i < numUsers; i++) {
      const journey = (async () => {
        const userClient = new E2EClient();
        const userData = TestDataFactory.generateUser();
        
        // Register
        await userClient.register(userData);
        
        // Login
        await userClient.login(userData.email, userData.password);
        
        // Create reservation
        const startTime = new Date(Date.now() + (i + 1) * 86400000);
        const endTime = new Date(startTime.getTime() + 7200000);
        
        const reservation = await userClient.createReservation({
          spotId: testSpot._id,
          startTime: startTime.toISOString(),
          endTime: endTime.toISOString(),
          vehicleNumber: `CONCURRENT${i}`
        });
        
        // Process payment
        if (reservation.status === 201) {
          await userClient.processPayment({
            reservationId: reservation.body.data._id,
            amount: reservation.body.data.totalAmount,
            method: 'credit_card',
            cardDetails: {
              number: '4111111111111111',
              expiry: '12/25',
              cvv: '123'
            }
          });
        }
        
        return { user: userData.email, reservation: reservation.body.data };
      })();
      
      journeys.push(journey);
    }
    
    // Wait for all journeys to complete
    const results = await Promise.all(journeys);
    
    expect(results).toHaveLength(numUsers);
    expect(results.every(r => r.reservation)).toBe(true);
    
    // Verify no overlapping reservations
    const reservations = await adminClient.getReservations();
    const spotReservations = reservations.body.data.reservations.filter(
      r => r.spotId === testSpot._id
    );
    
    // Check for overlaps
    let hasOverlap = false;
    for (let i = 0; i < spotReservations.length; i++) {
      for (let j = i + 1; j < spotReservations.length; j++) {
        const r1 = spotReservations[i];
        const r2 = spotReservations[j];
        
        if (r1.startTime < r2.endTime && r2.startTime < r1.endTime) {
          hasOverlap = true;
          break;
        }
      }
    }
    
    expect(hasOverlap).toBe(false);
    console.log(`Successfully completed ${numUsers} concurrent journeys`);
  });
});