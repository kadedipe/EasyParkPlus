// parking-management/backend/tests/e2e/run-e2e-tests.js
#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs-extra');
const path = require('path');

const runE2ETests = async () => {
  console.log('🚀 Starting E2E Test Suite');
  console.log('================================\n');
  
  // Create test reports directory
  const reportsDir = path.join(__dirname, 'reports');
  await fs.ensureDir(reportsDir);
  
  // Set test environment
  process.env.NODE_ENV = 'test';
  process.env.TEST_MODE = 'true';
  
  const testSuites = [
    { name: 'Authentication', pattern: 'tests/e2e/auth' },
    { name: 'Parking Spots', pattern: 'tests/e2e/parking' },
    { name: 'Reservations', pattern: 'tests/e2e/reservations' },
    { name: 'Payments', pattern: 'tests/e2e/payments' },
    { name: 'Admin', pattern: 'tests/e2e/admin' },
    { name: 'Workflows', pattern: 'tests/e2e/workflows' },
    { name: 'Performance', pattern: 'tests/e2e/performance' },
    { name: 'Security', pattern: 'tests/e2e/security' }
  ];
  
  let totalTests = 0;
  let passedTests = 0;
  let failedTests = 0;
  
  for (const suite of testSuites) {
    console.log(`\n📋 Running ${suite.name} Tests`);
    console.log('--------------------------------');
    
    try {
      const output = execSync(
        `npx jest --config tests/e2e/jest.config.js ${suite.pattern} --json --outputFile=${reportsDir}/${suite.name.toLowerCase()}-report.json`,
        { encoding: 'utf8', stdio: 'pipe' }
      );
      
      const report = JSON.parse(
        await fs.readFile(
          path.join(reportsDir, `${suite.name.toLowerCase()}-report.json`),
          'utf8'
        )
      );
      
      totalTests += report.numTotalTests;
      passedTests += report.numPassedTests;
      failedTests += report.numFailedTests;
      
      console.log(`✅ Passed: ${report.numPassedTests}`);
      console.log(`❌ Failed: ${report.numFailedTests}`);
      console.log(`⏱️  Time: ${(report.testResults.reduce((acc, test) => acc + test.endTime - test.startTime, 0) / 1000).toFixed(2)}s`);