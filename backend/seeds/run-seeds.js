// parking-management/backend/seeds/run-seeds.js
const { Pool } = require('pg');
const fs = require('fs').promises;
const path = require('path');
require('dotenv').config();

class SeedRunner {
    constructor() {
        this.pool = new Pool({
            host: process.env.DB_HOST || 'localhost',
            port: process.env.DB_PORT || 5432,
            database: process.env.DB_NAME || 'parking_management',
            user: process.env.DB_USER || 'postgres',
            password: process.env.DB_PASSWORD,
        });
        
        this.seedsTable = 'seed_history';
        this.seedsDir = __dirname;
        this.environment = process.env.NODE_ENV || 'development';
    }
    
    async initialize() {
        const client = await this.pool.connect();
        try {
            await client.query(`
                CREATE TABLE IF NOT EXISTS ${this.seedsTable} (
                    id SERIAL PRIMARY KEY,
                    seed_file VARCHAR(255) NOT NULL UNIQUE,
                    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    executed_by VARCHAR(100) DEFAULT CURRENT_USER,
                    duration_ms INTEGER,
                    status VARCHAR(20) DEFAULT 'success',
                    records_inserted INTEGER,
                    environment VARCHAR(50)
                );
            `);
            console.log('✅ Seeds history table initialized');
        } finally {
            client.release();
        }
    }
    
    async getExecutedSeeds() {
        const client = await this.pool.connect();
        try {
            const result = await client.query(
                `SELECT seed_file FROM ${this.seedsTable} 
                 WHERE status = 'success' AND environment = $1
                 ORDER BY id`,
                [this.environment]
            );
            return result.rows.map(row => row.seed_file);
        } finally {
            client.release();
        }
    }
    
    async getSeedFiles() {
        const files = await fs.readdir(this.seedsDir);
        const seedFiles = files
            .filter(file => file.endsWith('.sql') && file.match(/^\d{2}_.*\.sql$/))
            .sort();
        
        return seedFiles.map(file => ({
            name: file,
            path: path.join(this.seedsDir, file),
            order: parseInt(file.substring(0, 2))
        }));
    }
    
    async executeSeed(file, isDryRun = false) {
        const client = await this.pool.connect();
        const startTime = Date.now();
        
        try {
            const sql = await fs.readFile(file.path, 'utf8');
            
            if (isDryRun) {
                console.log(`[DRY RUN] Would execute: ${file.name}`);
                console.log(`[DRY RUN] SQL length: ${sql.length} characters`);
                return { success: true, recordsInserted: 0 };
            }
            
            // Execute seed in transaction
            await client.query('BEGIN');
            const result = await client.query(sql);
            await client.query('COMMIT');
            
            const duration = Date.now() - startTime;
            
            // Estimate records inserted (rough approximation)
            const insertMatches = sql.match(/INSERT INTO/gi);
            const recordsInserted = insertMatches ? insertMatches.length : 0;
            
            // Record seed execution
            await client.query(
                `INSERT INTO ${this.seedsTable} 
                 (seed_file, duration_ms, status, records_inserted, environment)
                 VALUES ($1, $2, $3, $4, $5)`,
                [file.name, duration, 'success', recordsInserted, this.environment]
            );
            
            console.log(`✅ Executed: ${file.name} (${duration}ms, ~${recordsInserted} records)`);
            return { success: true, recordsInserted };
            
        } catch (error) {
            await client.query('ROLLBACK');
            console.error(`❌ Failed: ${file.name}`);
            console.error(error.message);
            
            await client.query(
                `INSERT INTO ${this.seedsTable} 
                 (seed_file, duration_ms, status, environment)
                 VALUES ($1, $2, 'failed', $3)`,
                [file.name, Date.now() - startTime, this.environment]
            );
            
            return { success: false, error: error.message };
        } finally {
            client.release();
        }
    }
    
    async seed(options = {}) {
        const { dryRun = false, force = false, specific = null } = options;
        
        console.log(`\n🌱 Starting database seeding (${this.environment} environment)`);
        console.log('=' .repeat(60));
        
        await this.initialize();
        
        const executedSeeds = await this.getExecutedSeeds();
        let seedFiles = await this.getSeedFiles();
        
        if (specific) {
            seedFiles = seedFiles.filter(file => file.name.includes(specific));
            if (seedFiles.length === 0) {
                console.error(`❌ No seed files found matching: ${specific}`);
                return false;
            }
        }
        
        if (!force) {
            seedFiles = seedFiles.filter(file => !executedSeeds.includes(file.name));
        }
        
        if (seedFiles.length === 0) {
            console.log('📭 No pending seeds to execute');
            return true;
        }
        
        console.log(`\n📋 Found ${seedFiles.length} pending seed(s):`);
        seedFiles.forEach(file => console.log(`   - ${file.name}`));
        
        if (dryRun) {
            console.log('\n[DRY RUN] No changes were made to the database');
            return true;
        }
        
        console.log('\n🚀 Executing seeds...\n');
        
        let totalRecords = 0;
        let successCount = 0;
        
        for (const file of seedFiles) {
            const result = await this.executeSeed(file);
            if (result.success) {
                successCount++;
                totalRecords += result.recordsInserted || 0;
            } else {
                console.error(`\n❌ Seeding failed at ${file.name}`);
                console.error(`Error: ${result.error}`);
                return false;
            }
        }
        
        console.log('\n' + '=' .repeat(60));
        console.log(`✅ Seeding completed successfully!`);
        console.log(`   Seeds executed: ${successCount}/${seedFiles.length}`);
        console.log(`   Total records inserted: ~${totalRecords}`);
        console.log('=' .repeat(60));
        
        return true;
    }
    
    async reset() {
        console.log('\n⚠️  WARNING: This will reset all seeded data!');
        console.log('This operation is irreversible.\n');
        
        const readline = require('readline').createInterface({
            input: process.stdin,
            output: process.stdout
        });
        
        const answer = await new Promise(resolve => {
            readline.question('Type "RESET" to confirm: ', resolve);
        });
        
        readline.close();
        
        if (answer !== 'RESET') {
            console.log('Reset cancelled.');
            return false;
        }
        
        console.log('\n🔄 Resetting seed data...');
        
        const client = await this.pool.connect();
        try {
            await client.query('BEGIN');
            
            // Truncate tables in reverse order
            await client.query('TRUNCATE TABLE payments CASCADE');
            await client.query('TRUNCATE TABLE reservations CASCADE');
            await client.query('TRUNCATE TABLE promo_code_usage CASCADE');
            await client.query('TRUNCATE TABLE promo_codes CASCADE');
            await client.query('TRUNCATE TABLE user_vehicles CASCADE');
            await client.query('TRUNCATE TABLE user_addresses CASCADE');
            await client.query('TRUNCATE TABLE users CASCADE');
            
            // Reset seed history
            await client.query(`DELETE FROM ${this.seedsTable} WHERE environment = $1`, 
                               [this.environment]);
            
            await client.query('COMMIT');
            
            console.log('✅ Database reset successfully');
            return true;
        } catch (error) {
            await client.query('ROLLBACK');
            console.error('❌ Reset failed:', error.message);
            return false;
        } finally {
            client.release();
        }
    }
    
    async status() {
        console.log('\n📊 Seeding Status\n');
        console.log('=' .repeat(60));
        
        const client = await this.pool.connect();
        try {
            const result = await client.query(
                `SELECT seed_file, executed_at, duration_ms, status, records_inserted
                 FROM ${this.seedsTable}
                 WHERE environment = $1
                 ORDER BY executed_at DESC`,
                [this.environment]
            );
            
            if (result.rows.length === 0) {
                console.log('No seeds have been executed yet.');
            } else {
                console.log(`Environment: ${this.environment}\n`);
                result.rows.forEach(row => {
                    const statusIcon = row.status === 'success' ? '✅' : '❌';
                    console.log(`${statusIcon} ${row.seed_file}`);
                    console.log(`   Executed: ${row.executed_at}`);
                    console.log(`   Duration: ${row.duration_ms}ms`);
                    console.log(`   Records: ~${row.records_inserted || 0}\n`);
                });
            }
        } finally {
            client.release();
        }
        
        console.log('=' .repeat(60));
    }
    
    async close() {
        await this.pool.end();
    }
}

// CLI Interface
const command = process.argv[2];
const args = process.argv.slice(3);

const runner = new SeedRunner();

(async () => {
    try {
        switch (command) {
            case 'seed':
                await runner.seed({
                    dryRun: args.includes('--dry-run'),
                    force: args.includes('--force'),
                    specific: args.find(arg => arg !== '--dry-run' && arg !== '--force')
                });
                break;
            case 'reset':
                await runner.reset();
                break;
            case 'status':
                await runner.status();
                break;
            default:
                console.log(`
🌱 Database Seeding Tool

Usage: node run-seeds.js <command> [options]

Commands:
  seed              Run pending seed files
  reset             Reset all seeded data (destructive!)
  status            Show seeding history

Options:
  --dry-run         Preview what would be executed
  --force           Force re-run already executed seeds
  <pattern>         Only run seeds matching pattern

Examples:
  node run-seeds.js seed
  node run-seeds.js seed --dry-run
  node run-seeds.js seed --force
  node run-seeds.js seed users
  node run-seeds.js reset
  node run-seeds.js status
                `);
        }
    } catch (error) {
        console.error('Error:', error.message);
        process.exit(1);
    } finally {
        await runner.close();
    }
})();