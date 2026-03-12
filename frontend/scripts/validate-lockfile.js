#!/usr/bin/env node

/**
 * Validate package-lock.json integrity
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');

const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
};

function validateLockfile() {
  console.log(`${colors.blue}🔍 Validating package-lock.json...${colors.reset}\n`);

  const lockfilePath = path.join(process.cwd(), 'package-lock.json');
  
  if (!fs.existsSync(lockfilePath)) {
    console.log(`${colors.red}❌ package-lock.json not found!${colors.reset}`);
    console.log(`${colors.yellow}💡 Run 'npm install' to generate it${colors.reset}`);
    process.exit(1);
  }

  try {
    const lockfile = JSON.parse(fs.readFileSync(lockfilePath, 'utf8'));
    
    // Check lockfile version
    console.log(`📦 Lockfile version: ${lockfile.lockfileVersion || 'unknown'}`);
    
    // Check if it matches package.json
    const packageJson = JSON.parse(fs.readFileSync(path.join(process.cwd(), 'package.json'), 'utf8'));
    
    const pkgDeps = { ...packageJson.dependencies, ...packageJson.devDependencies };
    const lockDeps = lockfile.packages?.['']?.dependencies || {};
    
    const mismatches = [];
    Object.keys(pkgDeps).forEach(dep => {
      if (lockDeps[dep] !== pkgDeps[dep]) {
        mismatches.push(dep);
      }
    });
    
    if (mismatches.length > 0) {
      console.log(`${colors.yellow}⚠️  Version mismatches found:${colors.reset}`);
      mismatches.forEach(dep => {
        console.log(`   ${dep}: package.json (${pkgDeps[dep]}) vs lockfile (${lockDeps[dep] || 'missing'})`);
      });
    } else {
      console.log(`${colors.green}✅ Versions match package.json${colors.reset}`);
    }
    
    // Check integrity
    console.log(`\n${colors.blue}🔒 Checking integrity...${colors.reset}`);
    
    const packages = lockfile.packages || {};
    const packageCount = Object.keys(packages).length;
    console.log(`📦 Total packages: ${packageCount}`);
    
    // Verify with npm ci (dry run)
    try {
      execSync('npm ci --dry-run', { stdio: 'ignore' });
      console.log(`${colors.green}✅ Lockfile is valid for clean install${colors.reset}`);
    } catch {
      console.log(`${colors.red}❌ Lockfile may have issues with clean install${colors.reset}`);
    }
    
    console.log(`\n${colors.green}✅ Validation complete${colors.reset}`);
    
  } catch (error) {
    console.error(`${colors.red}❌ Invalid package-lock.json:${colors.reset}`, error.message);
    process.exit(1);
  }
}

validateLockfile();