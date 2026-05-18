// parking-management/backend/tests/e2e/helpers/global-teardown.js
module.exports = async () => {
  const mongoose = require('mongoose');
  const fs = require('fs-extra');
  
  if (mongoose.connection.readyState === 1) {
    await mongoose.disconnect();
  }
  
  if (global.__TEST_SERVER__) {
    await global.__TEST_SERVER__.close();
  }
  
  if (global.__REDIS_CLIENT__) {
    await global.__REDIS_CLIENT__.quit();
  }
  
  // Clean up test directories
  const testUploads = global.__TEST_UPLOAD_DIR__;
  if (testUploads) {
    await fs.remove(testUploads);
  }
  
  console.log('E2E test environment cleaned up');
};