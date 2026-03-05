#!/usr/bin/env node

/**
 * Debug Prettier configuration
 * Run with: node scripts/debug-prettier.js
 */

const prettier = require('prettier');
const fs = require('fs');
const path = require('path');

async function debugPrettier() {
  console.log('🔍 Prettier Debug Information\n');
  
  // Get current config
  const config = await prettier.resolveConfig(process.cwd());
  console.log('📋 Current Configuration:');
  console.log(JSON.stringify(config, null, 2));
  console.log('\n');
  
  // Check if config file exists
  const configFiles = [
    '.prettierrc',
    '.prettierrc.json',
    '.prettierrc.js',
    '.prettierrc.yaml',
    '.prettierrc.yml',
    '.prettierrc.toml',
    'prettier.config.js',
  ];
  
  console.log('📁 Config Files Found:');
  let found = false;
  for (const file of configFiles) {
    const filePath = path.join(process.cwd(), file);
    if (fs.existsSync(filePath)) {
      console.log(`  ✅ ${file}`);
      found = true;
    }
  }
  if (!found) {
    console.log('  ❌ No config file found (using defaults)');
  }
  console.log('\n');
  
  // Check ignore file
  const ignoreFile = path.join(process.cwd(), '.prettierignore');
  if (fs.existsSync(ignoreFile)) {
    const ignoreContent = fs.readFileSync(ignoreFile, 'utf8');
    const ignoreCount = ignoreContent.split('\n').filter(line => line.trim() && !line.startsWith('#')).length;
    console.log(`📝 .prettierignore found with ${ignoreCount} ignore patterns`);
  } else {
    console.log('⚠️  No .prettierignore file found');
  }
  console.log('\n');
  
  // Test formatting a simple file
  console.log('🧪 Testing Formatting:');
  const testCode = 'const   foo   =   "bar";';
  const formatted = await prettier.format(testCode, { ...config, parser: 'babel' });
  console.log(`  Original: ${testCode}`);
  console.log(`  Formatted: ${formatted.trim()}`);
  
  if (testCode !== formatted) {
    console.log('  ✅ Formatting is working');
  } else {
    console.log('  ❌ Formatting not working as expected');
  }
  console.log('\n');
  
  // Check version
  console.log(`📦 Prettier Version: ${prettier.version}`);
}

debugPrettier().catch(console.error);