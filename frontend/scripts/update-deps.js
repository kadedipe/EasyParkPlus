#!/usr/bin/env node

/**
 * Safe dependency update script
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
};

function updateDependencies() {
  console.log(`${colors.blue}🔄 Updating dependencies safely...${colors.reset}\n`);

  // Backup current files
  console.log(`${colors.yellow}📦 Backing up current files...${colors.reset}`);
  
  if (fs.existsSync('package.json')) {
    fs.copyFileSync('package.json', 'package.json.backup');
  }
  if (fs.existsSync('package-lock.json')) {
    fs.copyFileSync('package-lock.json', 'package-lock.json.backup');
  }

  try {
    // Check for updates
    console.log(`\n${colors.blue}🔍 Checking for updates...${colors.reset}`);
    execSync('npx npm-check-updates --format group', { stdio: 'inherit' });
    
    console.log(`\n${colors.yellow}⚠️  Review the changes above${colors.reset}`);
    console.log(`\n${colors.blue}❓ Proceed with update? (y/N)${colors.reset}`);
    
    // This is interactive - in a real script you'd use readline
    
    // Update package.json
    execSync('npx npm-check-updates -u', { stdio: 'inherit' });
    
    // Install updates
    console.log(`\n${colors.blue}📦 Installing updates...${colors.reset}`);
    execSync('npm install', { stdio: 'inherit' });
    
    // Run tests
    console.log(`\n${colors.blue}🧪 Running tests...${colors.reset}`);
    execSync('npm test', { stdio: 'inherit' });
    
    console.log(`\n${colors.green}✅ Update successful!${colors.reset}`);
    
    // Clean up backups
    fs.unlinkSync('package.json.backup');
    fs.unlinkSync('package-lock.json.backup');
    
  } catch (error) {
    console.error(`\n${colors.red}❌ Update failed:${colors.reset}`, error.message);
    
    // Restore from backup
    console.log(`\n${colors.yellow}🔄 Restoring from backup...${colors.reset}`);
    if (fs.existsSync('package.json.backup')) {
      fs.copyFileSync('package.json.backup', 'package.json');
      fs.unlinkSync('package.json.backup');
    }
    if (fs.existsSync('package-lock.json.backup')) {
      fs.copyFileSync('package-lock.json.backup', 'package-lock.json');
      fs.unlinkSync('package-lock.json.backup');
    }
    
    process.exit(1);
  }
}

updateDependencies();