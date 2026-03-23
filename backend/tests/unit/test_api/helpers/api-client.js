// parking-management/backend/tests/unit/test_api/helpers/api-client.js
const request = require('supertest');
const { app } = require('../../../../src/app');

class APIClient {
  constructor() {
    this.app = app;
    this.authToken = null;
    this.adminToken = null;
  }
  
  setAuthToken(token) {
    this.authToken = token;
  }
  
  setAdminToken(token) {
    this.adminToken = token;
  }
  
  getAuthHeaders() {
    return this.authToken ? { Authorization: `Bearer ${this.authToken}` } : {};
  }
  
  getAdminHeaders() {
    return this.adminToken ? { Authorization: `Bearer ${this.adminToken}` } : {};
  }
  
  // Auth endpoints
  async register(userData) {
    return request(this.app)
      .post('/api/auth/register')
      .send(userData);
  }
  
  async login(credentials) {
    const response = await request(this.app)
      .post('/api/auth/login')
      .send(credentials);
    
    if (response.body.success && response.body.data.token) {
      this.setAuthToken(response.body.data.token);
    }
    
    return response;
  }
  
  async logout() {
    return request(this.app)
      .post('/api/auth/logout')
      .set(this.getAuthHeaders());
  }
  
  async refreshToken() {
    return request(this.app)
      .post('/api/auth/refresh-token')
      .set(this.getAuthHeaders());
  }
  
  async forgotPassword(email) {
    return request(this.app)
      .post('/api/auth/forgot-password')
      .send({ email });
  }
  
  async resetPassword(token, newPassword) {
    return request(this.app)
      .post('/api/auth/reset-password')
      .send({ token, newPassword });
  }
  
  // User endpoints
  async getProfile() {
    return request(this.app)
      .get('/api/users/profile')
      .set(this.getAuthHeaders());
  }
  
  async updateProfile(updates) {
    return request(this.app)
      .put('/api/users/profile')
      .set(this.getAuthHeaders())
      .send(updates);
  }
  
  async changePassword(currentPassword, newPassword) {
    return request(this.app)
      .put('/api/users/change-password')
      .set(this.getAuthHeaders())
      .send({ currentPassword, newPassword });
  }
  
  async getUsers(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `/api/users${queryString ? `?${queryString}` : ''}`;
    
    return request(this.app)
      .get(url)
      .set(this.getAdminHeaders());
  }
  
  async getUserById(userId) {
    return request(this.app)
      .get(`/api/users/${userId}`)
      .set(this.getAuthHeaders());
  }
  
  async deleteUser(userId) {
    return request(this.app)
      .delete(`/api/users/${userId}`)
      .set(this.getAdminHeaders());
  }
  
  // Parking spot endpoints
  async getParkingSpots(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `/api/parking-spots${queryString ? `?${queryString}` : ''}`;
    
    return request(this.app)
      .get(url)
      .set(this.getAuthHeaders());
  }
  
  async getNearbySpots(lat, lng, radius = 1000) {
    return request(this.app)
      .get('/api/parking-spots/nearby')
      .query({ lat, lng, radius })
      .set(this.getAuthHeaders());
  }
  
  async getParkingSpotById(spotId, queryParams = {}) {
    const queryString = new URLSearchParams(queryParams).toString();
    const url = `/api/parking-spots/${spotId}${queryString ? `?${queryString}` : ''}`;
    
    return request(this.app)
      .get(url)
      .set(this.getAuthHeaders());
  }
  
  async createParkingSpot(spotData) {
    return request(this.app)
      .post('/api/parking-spots')
      .set(this.getAdminHeaders())
      .send(spotData);
  }
  
  async updateParkingSpot(spotId, updates) {
    return request(this.app)
      .put(`/api/parking-spots/${spotId}`)
      .set(this.getAdminHeaders())
      .send(updates);
  }
  
  async deleteParkingSpot(spotId) {
    return request(this.app)
      .delete(`/api/parking-spots/${spotId}`)
      .set(this.getAdminHeaders());
  }
  
  // Reservation endpoints
  async createReservation(reservationData) {
    return request(this.app)
      .post('/api/reservations')
      .set(this.getAuthHeaders())
      .send(reservationData);
  }
  
  async getReservations(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `/api/reservations${queryString ? `?${queryString}` : ''}`;
    
    return request(this.app)
      .get(url)
      .set(this.getAuthHeaders());
  }
  
  async getReservationById(reservationId) {
    return request(this.app)
      .get(`/api/reservations/${reservationId}`)
      .set(this.getAuthHeaders());
  }
  
  async cancelReservation(reservationId) {
    return request(this.app)
      .put(`/api/reservations/${reservationId}/cancel`)
      .set(this.getAuthHeaders());
  }
  
  async extendReservation(reservationId, newEndTime) {
    return request(this.app)
      .put(`/api/reservations/${reservationId}/extend`)
      .set(this.getAuthHeaders())
      .send({ newEndTime });
  }
  
  // Payment endpoints
  async processPayment(paymentData) {
    return request(this.app)
      .post('/api/payments')
      .set(this.getAuthHeaders())
      .send(paymentData);
  }
  
  async getPaymentStatus(paymentId) {
    return request(this.app)
      .get(`/api/payments/${paymentId}`)
      .set(this.getAuthHeaders());
  }
  
  async refundPayment(paymentId) {
    return request(this.app)
      .post(`/api/payments/${paymentId}/refund`)
      .set(this.getAuthHeaders());
  }
  
  // Admin endpoints
  async getDashboardStats() {
    return request(this.app)
      .get('/api/admin/dashboard')
      .set(this.getAdminHeaders());
  }
  
  async getRevenueReport(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `/api/admin/reports/revenue${queryString ? `?${queryString}` : ''}`;
    
    return request(this.app)
      .get(url)
      .set(this.getAdminHeaders());
  }
  
  async getOccupancyReport(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `/api/admin/reports/occupancy${queryString ? `?${queryString}` : ''}`;
    
    return request(this.app)
      .get(url)
      .set(this.getAdminHeaders());
  }
}

module.exports = APIClient;