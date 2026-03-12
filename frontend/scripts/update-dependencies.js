#!/usr/bin/env node

/**
 * Update dependencies to latest versions
 */

const { execSync } = require('child_process');
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
};

console.log(`${colors.blue}🔄 Updating dependencies...${colors.reset}\n`);

try {
  // Update all dependencies
  execSync('npx npm-check-updates -u', { stdio: 'inherit' });
  
  console.log('\n');
  
  // Reinstall
  execSync('npm install', { stdio: 'inherit' });
  
  console.log(`\n${colors.green}✅ Dependencies updated${colors.reset}`);
} catch (error) {
  console.error(`\n${colors.red}❌ Update failed:${colors.reset}`, error.message);
  process.exit(1);
}