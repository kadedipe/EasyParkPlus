// parking-management/backend/tests/unit/test_api/runner.js
const { runTests } = require('jest');

const runApiTests = async () => {
  const config = {
    config: './jest.config.js',
    coverage: true,
    verbose: true,
    testMatch: ['**/test_api/**/*.test.js'],
    testTimeout: 30000,
    maxWorkers: 4,
    bail: false,
    forceExit: true,
    detectOpenHandles: true
  };
  
  try {
    const results = await runTests(config);
    
    if (results.results.numFailedTests > 0) {
      console.error(`${results.results.numFailedTests} API tests failed`);
      process.exit(1);
    } else {
      console.log('All API tests passed!');
      process.exit(0);
    }
  } catch (error) {
    console.error('Error running API tests:', error);
    process.exit(1);
  }
};

runApiTests();