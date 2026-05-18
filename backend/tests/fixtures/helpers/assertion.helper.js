// parking-management/backend/tests/fixtures/helpers/assertion.helper.js
class AssertionHelper {
  static assertSuccessResponse(response, expectedStatus = 200) {
    expect(response.status).toBe(expectedStatus);
    expect(response.body).toHaveProperty('success', true);
  }
  
  static assertErrorResponse(response, expectedStatus, expectedMessage) {
    expect(response.status).toBe(expectedStatus);
    expect(response.body).toHaveProperty('success', false);
    if (expectedMessage) {
      expect(response.body.message).toContain(expectedMessage);
    }
  }
  
  static assertValidationErrors(response, expectedFields) {
    expect(response.status).toBe(400);
    expect(response.body).toHaveProperty('errors');
    expect(Array.isArray(response.body.errors)).toBe(true);
    
    if (expectedFields) {
      const errorFields = response.body.errors.map(e => e.field);
      expectedFields.forEach(field => {
        expect(errorFields).toContain(field);
      });
    }
  }
  
  static assertPagination(response, expectedPage, expectedLimit) {
    expect(response.body.data).toHaveProperty('pagination');
    expect(response.body.data.pagination).toHaveProperty('page', expectedPage);
    expect(response.body.data.pagination).toHaveProperty('limit', expectedLimit);
  }
  
  static assertDateRange(date, start, end) {
    const dateObj = new Date(date);
    expect(dateObj.getTime()).toBeGreaterThanOrEqual(new Date(start).getTime());
    expect(dateObj.getTime()).toBeLessThanOrEqual(new Date(end).getTime());
  }
  
  static assertIdsMatch(id1, id2) {
    expect(id1.toString()).toBe(id2.toString());
  }
  
  static assertObjectContains(obj, subset) {
    for (const [key, value] of Object.entries(subset)) {
      expect(obj).toHaveProperty(key);
      if (typeof value === 'object' && value !== null) {
        this.assertObjectContains(obj[key], value);
      } else {
        expect(obj[key]).toBe(value);
      }
    }
  }
  
  static assertArrayContains(array, item) {
    expect(array).toContainEqual(expect.objectContaining(item));
  }
  
  static assertResponseTime(response, maxTimeMs = 1000) {
    expect(response.headers['x-response-time']).toBeDefined();
    const responseTime = parseInt(response.headers['x-response-time']);
    expect(responseTime).toBeLessThan(maxTimeMs);
  }
}

module.exports = AssertionHelper;