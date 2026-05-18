// parking-management/backend/tests/fixtures/helpers/index.js
const DatabaseHelper = require('./database.helper');
const AuthHelper = require('./auth.helper');
const AssertionHelper = require('./assertion.helper');

module.exports = {
  database: DatabaseHelper,
  auth: AuthHelper,
  assertions: AssertionHelper
};