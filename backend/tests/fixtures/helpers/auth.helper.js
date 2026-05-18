// parking-management/backend/tests/fixtures/helpers/auth.helper.js
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');

class AuthHelper {
  static generateToken(userId, role = 'user', expiresIn = '1h') {
    return jwt.sign(
      { id: userId, role },
      process.env.JWT_SECRET || 'test-secret',
      { expiresIn }
    );
  }
  
  static generateRefreshToken(userId, role = 'user') {
    return jwt.sign(
      { id: userId, role, type: 'refresh' },
      process.env.JWT_REFRESH_SECRET || 'test-refresh-secret',
      { expiresIn: '7d' }
    );
  }
  
  static async hashPassword(password) {
    const salt = await bcrypt.genSalt(10);
    return await bcrypt.hash(password, salt);
  }
  
  static async comparePassword(password, hashedPassword) {
    return await bcrypt.compare(password, hashedPassword);
  }
  
  static decodeToken(token) {
    try {
      return jwt.verify(token, process.env.JWT_SECRET || 'test-secret');
    } catch (error) {
      return null;
    }
  }
  
  static isTokenExpired(token) {
    const decoded = this.decodeToken(token);
    if (!decoded) return true;
    return decoded.exp < Date.now() / 1000;
  }
  
  static generateExpiredToken(userId, role = 'user') {
    return jwt.sign(
      { id: userId, role },
      process.env.JWT_SECRET || 'test-secret',
      { expiresIn: '-1h' }
    );
  }
  
  static getAuthHeaders(token) {
    return {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }
}

module.exports = AuthHelper;