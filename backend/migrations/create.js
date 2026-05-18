// parking-management/backend/migrations/create.js
const fs = require('fs').promises;
const path = require('path');

async function createMigration(name) {
    if (!name) {
        console.error('❌ Please provide a migration name');
        console.log('Usage: npm run migrate:create <migration_name>');
        process.exit(1);
    }
    
    const timestamp = new Date().toISOString().replace(/[-:T.Z]/g, '').slice(0, 14);
    const filename = `${timestamp}_${name}`;
    
    const upFile = path.join(__dirname, `${filename}.up.sql`);
    const downFile = path.join(__dirname, `${filename}.down.sql`);
    
    const upTemplate = `-- Migration: ${name}
-- Version: ${timestamp}
-- Direction: UP
-- Author: ${process.env.USER || 'System'}
-- Date: ${new Date().toISOString()}

BEGIN;

-- Add your migration SQL here

COMMIT;
`;
    
    const downTemplate = `-- Migration: ${name}
-- Version: ${timestamp}
-- Direction: DOWN
-- Author: ${process.env.USER || 'System'}
-- Date: ${new Date().toISOString()}

BEGIN;

-- Add your rollback SQL here

COMMIT;
`;
    
    await fs.writeFile(upFile, upTemplate);
    await fs.writeFile(downFile, downTemplate);
    
    console.log(`✅ Created migration files:`);
    console.log(`   📄 ${upFile}`);
    console.log(`   📄 ${downFile}`);
}

createMigration(process.argv[2]);