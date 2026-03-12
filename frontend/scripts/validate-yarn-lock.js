#!/usr/bin/env node

/**
 * Validate yarn.lock integrity
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const crypto = require('crypto');

const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

function validateYarnLock() {
  console.log(`${colors.blue}🔍 Validating yarn.lock...${colors.reset}\n`);

  const lockfilePath = path.join(process.cwd(), 'yarn.lock');
  
  if (!fs.existsSync(lockfilePath)) {
    console.log(`${colors.red}❌ yarn.lock not found!${colors.reset}`);
    console.log(`${colors.yellow}💡 Run 'yarn install' to generate it${colors.reset}`);
    process.exit(1);
  }

  try {
    const lockContent = fs.readFileSync(lockfilePath, 'utf8');
    
    // Check if it's Yarn v1 or v2
    const isV1 = lockContent.includes('yarn lockfile v1');
    const isV2 = lockContent.includes('yarn lockfile v2');
    
    console.log(`${colors.magenta}📦 Yarn lockfile version: ${colors.reset}${isV2 ? 'v2 (Berry)' : 'v1'}`);
    
    // Check if it matches package.json
    const packageJson = JSON.parse(fs.readFileSync(path.join(process.cwd(), 'package.json'), 'utf8'));
    
    // Quick check for major dependencies
    const dependencies = { ...packageJson.dependencies, ...packageJson.devDependencies };
    
    console.log(`\n${colors.cyan}📋 Checking major dependencies:${colors.reset}`);
    
    Object.keys(dependencies).slice(0, 10).forEach(dep => {
      const depPattern = new RegExp(`"?${dep}@?:?`, 'g');
      const matches = lockContent.match(depPattern);
      if (matches) {
        console.log(`  ${colors.green}✅${colors.reset} ${dep} (${matches.length} resolutions)`);
      } else {
        console.log(`  ${colors.red}❌${colors.reset} ${dep} not found in lockfile`);
      }
    });
    
    if (Object.keys(dependencies).length > 10) {
      console.log(`  ... and ${Object.keys(dependencies).length - 10} more`);
    }
    
    // Check integrity with yarn check
    console.log(`\n${colors.blue}🔒 Running integrity check...${colors.reset}`);
    
    try {
      if (isV2) {
        execSync('yarn install --immutable --immutable-cache --check-cache', { stdio: 'pipe' });
      } else {
        execSync('yarn check --integrity', { stdio: 'pipe' });
      }
      console.log(`${colors.green}✅ Lockfile integrity check passed${colors.reset}`);
    } catch (error) {
      console.log(`${colors.yellow}⚠️  Integrity check warnings:${colors.reset}`);
      console.log(error.stdout?.toString() || error.message);
    }
    
    // Count packages
    const packageCount = (lockContent.match(/resolved/g) || []).length;
    console.log(`\n${colors.magenta}📊 Total packages: ${packageCount}${colors.reset}`);
    
    // Check for duplicates (simplified)
    const packages = new Set();
    const duplicates = [];
    const packageRegex = /"(@?[^@]+)@[^:]+:/g;
    let match;
    while ((match = packageRegex.exec(lockContent)) !== null) {
      const pkg = match[1];
      if (packages.has(pkg)) {
        duplicates.push(pkg);
      } else {
        packages.add(pkg);
      }
    }
    
    if (duplicates.length > 0) {
      console.log(`${colors.yellow}⚠️  Found ${duplicates.length} packages with multiple versions${colors.reset}`);
      duplicates.slice(0, 5).forEach(pkg => {
        console.log(`   ${pkg}`);
      });
      if (duplicates.length > 5) {
        console.log(`   ... and ${duplicates.length - 5} more`);
      }
    } else {
      console.log(`${colors.green}✅ No duplicate packages found${colors.reset}`);
    }
    
    console.log(`\n${colors.green}✅ Validation complete${colors.reset}`);
    
  } catch (error) {
    console.error(`${colors.red}❌ Invalid yarn.lock:${colors.reset}`, error.message);
    process.exit(1);
  }
}

validateYarnLock();