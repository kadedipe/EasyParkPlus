#!/usr/bin/env node

/**
 * Check for outdated dependencies and security vulnerabilities
 */

const { execSync } = require('child_process');
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
};

console.log(`${colors.blue}🔍 Checking dependencies...${colors.reset}\n`);

try {
  // Check for outdated packages
  console.log(`${colors.yellow}📦 Outdated packages:${colors.reset}`);
  execSync('npm outdated', { stdio: 'inherit' });
  
  console.log('\n');
  
  // Check for security vulnerabilities
  console.log(`${colors.yellow}🔒 Security audit:${colors.reset}`);
  execSync('npm audit', { stdio: 'inherit' });
  
  console.log(`\n${colors.green}✅ Dependency check complete${colors.reset}`);
} catch (error) {
  // npm outdated and audit return non-zero exit codes when issues found
  console.log(`\n${colors.yellow}⚠️  Some dependencies need attention${colors.reset}`);
}