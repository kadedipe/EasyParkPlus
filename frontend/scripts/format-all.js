#!/usr/bin/env node

/**
 * Format all files in the project
 * Run with: node scripts/format-all.js
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

console.log(`${colors.bright}${colors.blue}🔧 Formatting all files...${colors.reset}\n`);

try {
  // Run prettier
  execSync('prettier --write .', { 
    stdio: 'inherit',
    cwd: path.join(__dirname, '..'),
  });
  
  console.log(`\n${colors.green}✅ Formatting complete!${colors.reset}\n`);
  
  // Count formatted files
  const result = execSync('git diff --name-only', { encoding: 'utf8' });
  const files = result.split('\n').filter(Boolean);
  
  if (files.length > 0) {
    console.log(`${colors.yellow}📝 Formatted ${files.length} files:${colors.reset}`);
    files.slice(0, 10).forEach(file => {
      console.log(`   - ${file}`);
    });
    if (files.length > 10) {
      console.log(`   ... and ${files.length - 10} more`);
    }
  } else {
    console.log(`${colors.green}✨ No files needed formatting${colors.reset}`);
  }
  
} catch (error) {
  console.error(`${colors.red}❌ Formatting failed:${colors.reset}`, error.message);
  process.exit(1);
}