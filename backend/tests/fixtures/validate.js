// parking-management/backend/tests/fixtures/validate.js
const fixtures = require('./index');

const validateFixtures = () => {
  console.log('🔍 Validating test fixtures...\n');
  
  let errors = [];
  let warnings = [];
  
  // Validate models
  console.log('📦 Validating model fixtures...');
  for (const [model, fixtures] of Object.entries(fixtures.models)) {
    if (fixtures.valid) {
      console.log(`  ✅ ${model}: valid fixture present`);
    }
    if (fixtures.invalid) {
      console.log(`  ✅ ${model}: invalid fixtures present`);
    }
    if (fixtures.bulk) {
      console.log(`  ✅ ${model}: bulk fixtures present`);
    }
  }
  
  // Validate API fixtures
  console.log('\n🌐 Validating API fixtures...');
  for (const [type, fixtures] of Object.entries(fixtures.api)) {
    const fixtureCount = Object.keys(fixtures).length;
    console.log(`  ✅ ${type}: ${fixtureCount} fixtures`);
  }
  
  // Validate data fixtures
  console.log('\n💾 Validating data fixtures...');
  for (const [category, data] of Object.entries(fixtures.data)) {
    const dataCount = Object.keys(data).length;
    console.log(`  ✅ ${category}: ${dataCount} fixtures`);
  }
  
  // Validate factories
  console.log('\n🏭 Validating factories...');
  for (const [factory, methods] of Object.entries(fixtures.factories)) {
    const methodCount = Object.keys(methods).filter(k => typeof methods[k] === 'function').length;
    console.log(`  ✅ ${factory}: ${methodCount} factory methods`);
  }
  
  // Validate helpers
  console.log('\n🛠️ Validating helpers...');
  for (const [helper, methods] of Object.entries(fixtures.helpers)) {
    const methodCount = Object.keys(methods).filter(k => typeof methods[k] === 'function').length;
    console.log(`  ✅ ${helper}: ${methodCount} helper methods`);
  }
  
  if (errors.length === 0 && warnings.length === 0) {
    console.log('\n🎉 All fixtures validated successfully!');
  } else {
    if (warnings.length > 0) {
      console.log('\n⚠️ Warnings:');
      warnings.forEach(w => console.log(`  ${w}`));
    }
    if (errors.length > 0) {
      console.log('\n❌ Errors:');
      errors.forEach(e => console.log(`  ${e}`));
      process.exit(1);
    }
  }
};

validateFixtures();