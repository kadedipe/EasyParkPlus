#!/usr/bin/env node

/**
 * Validate that all files are properly formatted
 * Run with: node scripts/validate-formatting.js
 */

const { execSync } = require('child_process');
const path = require('path');

const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
};

console.log(`${colors.bright}${colors.blue}🔍 Checking code formatting...${colors.reset}\n`);

try {
  execSync('prettier --check .', { 
    stdio: 'inherit',
    cwd: path.join(__dirname, '..'),
  });
  
  console.log(`\n${colors.green}✅ All files are properly formatted!${colors.reset}\n`);
  
} catch (error) {
  console.log(`\n${colors.red}❌ Some files need formatting${colors.reset}`);
  console.log(`\n${colors.yellow}💡 Run 'npm run format' to fix formatting${colors.reset}\n`);
  process.exit(1);
}