#!/usr/bin/env node

/**
 * Validate .gitignore file
 * Check for common missing patterns and sensitive files
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
};

const REQUIRED_PATTERNS = [
  'node_modules/',
  'dist/',
  'build/',
  '.env',
  '.DS_Store',
  '*.log',
];

const SENSITIVE_PATTERNS = [
  '*.pem',
  '*.key',
  '*.crt',
  'secrets/',
  'credentials.json',
  'service-account.json',
  '.env',
  '.env.*',
];

function validateGitignore() {
  console.log(`${colors.bright}${colors.blue}🔍 Validating .gitignore...${colors.reset}\n`);

  const gitignorePath = path.join(process.cwd(), '.gitignore');
  
  if (!fs.existsSync(gitignorePath)) {
    console.log(`${colors.red}❌ .gitignore file not found!${colors.reset}`);
    process.exit(1);
  }

  const content = fs.readFileSync(gitignorePath, 'utf8');
  const lines = content.split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('#'));

  console.log(`📄 Found ${lines.length} ignore patterns\n`);

  // Check required patterns
  console.log(`${colors.bright}Required Patterns:${colors.reset}`);
  REQUIRED_PATTERNS.forEach(pattern => {
    const exists = lines.some(l => l.includes(pattern));
    console.log(`  ${exists ? '✅' : '❌'} ${pattern}`);
  });

  console.log('\n');

  // Check for sensitive files in git
  try {
    const untracked = execSync('git ls-files --others --exclude-standard', { encoding: 'utf8' })
      .split('\n')
      .filter(Boolean);
    
    if (untracked.length > 0) {
      console.log(`${colors.yellow}⚠️  Untracked files:${colors.reset}`);
      untracked.slice(0, 10).forEach(file => console.log(`   ${file}`));
      if (untracked.length > 10) {
        console.log(`   ... and ${untracked.length - 10} more`);
      }
    } else {
      console.log(`${colors.green}✅ No untracked files${colors.reset}`);
    }
  } catch (error) {
    // Not a git repository
  }

  console.log('\n');

  // Check for sensitive patterns
  console.log(`${colors.bright}Sensitive Patterns Check:${colors.reset}`);
  SENSITIVE_PATTERNS.forEach(pattern => {
    const matches = lines.some(l => l.includes(pattern));
    console.log(`  ${matches ? '✅' : '⚠️'} ${pattern}`);
  });

  console.log('\n');

  // Check for comments
  const comments = content.split('\n').filter(l => l.trim().startsWith('#')).length;
  console.log(`📝 Documentation: ${comments} comment lines`);

  console.log(`\n${colors.green}✅ .gitignore validation complete${colors.reset}`);
}

validateGitignore();