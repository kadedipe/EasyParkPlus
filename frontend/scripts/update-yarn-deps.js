#!/usr/bin/env node

/**
 * Safe dependency update script for Yarn
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function askQuestion(question) {
  return new Promise((resolve) => {
    rl.question(question, resolve);
  });
}

async function updateDependencies() {
  console.log(`${colors.blue}🔄 Updating dependencies safely with Yarn...${colors.reset}\n`);

  // Check Yarn version
  let isYarnV2 = false;
  try {
    const yarnVersion = execSync('yarn --version', { encoding: 'utf8' }).trim();
    isYarnV2 = parseInt(yarnVersion.split('.')[0]) >= 2;
    console.log(`${colors.magenta}📦 Yarn version: ${yarnVersion}${colors.reset}`);
  } catch {
    console.log(`${colors.red}❌ Yarn not found${colors.reset}`);
    process.exit(1);
  }

  // Backup current files
  console.log(`\n${colors.yellow}📦 Backing up current files...${colors.reset}`);
  
  if (fs.existsSync('package.json')) {
    fs.copyFileSync('package.json', 'package.json.backup');
  }
  if (fs.existsSync('yarn.lock')) {
    fs.copyFileSync('yarn.lock', 'yarn.lock.backup');
  }
  if (fs.existsSync('.yarnrc.yml')) {
    fs.copyFileSync('.yarnrc.yml', '.yarnrc.yml.backup');
  }

  try {
    // Check for outdated packages
    console.log(`\n${colors.blue}🔍 Checking for outdated packages...${colors.reset}`);
    execSync('yarn outdated', { stdio: 'inherit' });
    
    const answer = await askQuestion(`\n${colors.yellow}⚠️  Proceed with updates? (y/N) ${colors.reset}`);
    
    if (answer.toLowerCase() !== 'y') {
      console.log(`\n${colors.yellow}Update cancelled${colors.reset}`);
      cleanup();
      process.exit(0);
    }

    // Update all dependencies
    console.log(`\n${colors.blue}📦 Updating dependencies...${colors.reset}`);
    
    if (isYarnV2) {
      execSync('yarn up \'*\'', { stdio: 'inherit' });
    } else {
      execSync('yarn upgrade --latest', { stdio: 'inherit' });
    }
    
    // Run tests
    console.log(`\n${colors.blue}🧪 Running tests...${colors.reset}`);
    execSync('yarn test', { stdio: 'inherit' });
    
    console.log(`\n${colors.green}✅ Update successful!${colors.reset}`);
    
    // Clean up backups
    fs.unlinkSync('package.json.backup');
    fs.unlinkSync('yarn.lock.backup');
    if (fs.existsSync('.yarnrc.yml.backup')) {
      fs.unlinkSync('.yarnrc.yml.backup');
    }
    
    // Show what was updated
    console.log(`\n${colors.cyan}📊 Update summary:${colors.reset}`);
    execSync('yarn outdated', { stdio: 'inherit' });
    
  } catch (error) {
    console.error(`\n${colors.red}❌ Update failed:${colors.reset}`, error.message);
    
    // Restore from backup
    console.log(`\n${colors.yellow}🔄 Restoring from backup...${colors.reset}`);
    restore();
    process.exit(1);
  } finally {
    rl.close();
  }
}

function restore() {
  if (fs.existsSync('package.json.backup')) {
    fs.copyFileSync('package.json.backup', 'package.json');
    fs.unlinkSync('package.json.backup');
  }
  if (fs.existsSync('yarn.lock.backup')) {
    fs.copyFileSync('yarn.lock.backup', 'yarn.lock');
    fs.unlinkSync('yarn.lock.backup');
  }
  if (fs.existsSync('.yarnrc.yml.backup')) {
    fs.copyFileSync('.yarnrc.yml.backup', '.yarnrc.yml');
    fs.unlinkSync('.yarnrc.yml.backup');
  }
}

function cleanup() {
  if (fs.existsSync('package.json.backup')) {
    fs.unlinkSync('package.json.backup');
  }
  if (fs.existsSync('yarn.lock.backup')) {
    fs.unlinkSync('yarn.lock.backup');
  }
  if (fs.existsSync('.yarnrc.yml.backup')) {
    fs.unlinkSync('.yarnrc.yml.backup');
  }
}

updateDependencies();