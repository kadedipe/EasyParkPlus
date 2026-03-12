#!/usr/bin/env node

/**
 * Migrate from npm to yarn
 */

const { execSync } = require('child_process');
const fs = require('fs');

const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
};

function migrateToYarn() {
  console.log(`${colors.blue}🔄 Migrating from npm to yarn...${colors.reset}\n`);

  // Check if yarn is installed
  try {
    execSync('yarn --version', { stdio: 'ignore' });
  } catch {
    console.log(`${colors.red}❌ Yarn is not installed. Install it first:${colors.reset}`);
    console.log('   npm install -g yarn');
    process.exit(1);
  }

  // Check for package-lock.json
  if (fs.existsSync('package-lock.json')) {
    console.log(`${colors.yellow}📦 Found package-lock.json${colors.reset}`);
    
    // Backup
    fs.copyFileSync('package-lock.json', 'package-lock.json.backup');
    console.log(`${colors.green}✅ Backed up package-lock.json${colors.reset}`);
  }

  // Remove node_modules and package-lock
  console.log(`\n${colors.yellow}🧹 Cleaning npm artifacts...${colors.reset}`);
  execSync('rm -rf node_modules package-lock.json', { stdio: 'inherit' });

  // Install with yarn
  console.log(`\n${colors.blue}📦 Installing with yarn...${colors.reset}`);
  execSync('yarn install', { stdio: 'inherit' });

  // Verify
  console.log(`\n${colors.blue}🔍 Verifying installation...${colors.reset}`);
  execSync('yarn list --depth=0', { stdio: 'inherit' });

  console.log(`\n${colors.green}✅ Migration complete!${colors.reset}`);
  console.log(`\n${colors.yellow}Next steps:${colors.reset}`);
  console.log(`   1. Remove package-lock.json.backup if everything works`);
  console.log(`   2. Update your CI/CD to use 'yarn install --frozen-lockfile'`);
  console.log(`   3. Commit the new yarn.lock file`);
}

migrateToYarn();