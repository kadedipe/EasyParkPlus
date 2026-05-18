// parking-management/backend/migrations/runner.js
const { Pool } = require('pg');
const fs = require('fs').promises;
const path = require('path');
require('dotenv').config();

class MigrationRunner {
    constructor() {
        this.pool = new Pool({
            host: process.env.DB_HOST || 'localhost',
            port: process.env.DB_PORT || 5432,
            database: process.env.DB_NAME || 'parking_management',
            user: process.env.DB_USER || 'postgres',
            password: process.env.DB_PASSWORD,
        });
        
        this.migrationsTable = 'schema_migrations';
        this.migrationsDir = __dirname;
    }
    
    async initialize() {
        const client = await this.pool.connect();
        try {
            await client.query(`
                CREATE TABLE IF NOT EXISTS ${this.migrationsTable} (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(14) NOT NULL UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    executed_by VARCHAR(100) DEFAULT CURRENT_USER,
                    duration_ms INTEGER,
                    checksum VARCHAR(64),
                    success BOOLEAN DEFAULT true
                );
            `);
            console.log('✅ Migrations table initialized');
        } finally {
            client.release();
        }
    }
    
    async getAppliedMigrations() {
        const client = await this.pool.connect();
        try {
            const result = await client.query(
                `SELECT version FROM ${this.migrationsTable} WHERE success = true ORDER BY version`
            );
            return result.rows.map(row => row.version);
        } finally {
            client.release();
        }
    }
    
    async getMigrationFiles() {
        const files = await fs.readdir(this.migrationsDir);
        const migrationFiles = files
            .filter(file => file.endsWith('.up.sql') && file.match(/^\d{14}_/))
            .sort();
        
        return migrationFiles.map(file => {
            const version = file.substring(0, 14);
            const name = file.substring(15, file.length - 6);
            return { version, name, file, path: path.join(this.migrationsDir, file) };
        });
    }
    
    async calculateChecksum(filePath) {
        const crypto = require('crypto');
        const content = await fs.readFile(filePath, 'utf8');
        return crypto.createHash('sha256').update(content).digest('hex');
    }
    
    async runMigration(file, direction = 'up') {
        const client = await this.pool.connect();
        const startTime = Date.now();
        
        try {
            await client.query('BEGIN');
            
            const sql = await fs.readFile(file.path, 'utf8');
            await client.query(sql);
            
            const duration = Date.now() - startTime;
            const checksum = await this.calculateChecksum(file.path);
            
            if (direction === 'up') {
                await client.query(
                    `INSERT INTO ${this.migrationsTable} (version, name, duration_ms, checksum, success)
                     VALUES ($1, $2, $3, $4, $5)`,
                    [file.version, file.name, duration, checksum, true]
                );
            }
            
            await client.query('COMMIT');
            console.log(`✅ Applied migration: ${file.name} (${duration}ms)`);
            return true;
        } catch (error) {
            await client.query('ROLLBACK');
            console.error(`❌ Failed migration: ${file.name}`);
            console.error(error);
            return false;
        } finally {
            client.release();
        }
    }
    
    async migrate() {
        console.log('🚀 Starting migrations...\n');
        
        await this.initialize();
        
        const appliedVersions = await this.getAppliedMigrations();
        const migrationFiles = await this.getMigrationFiles();
        
        const pendingMigrations = migrationFiles.filter(
            file => !appliedVersions.includes(file.version)
        );
        
        if (pendingMigrations.length === 0) {
            console.log('📭 No pending migrations');
            return;
        }
        
        console.log(`📋 Found ${pendingMigrations.length} pending migrations:\n`);
        
        for (const migration of pendingMigrations) {
            console.log(`Applying: ${migration.name}...`);
            const success = await this.runMigration(migration, 'up');
            if (!success) {
                console.error('❌ Migration failed. Stopping.');
                process.exit(1);
            }
        }
        
        console.log('\n🎉 All migrations completed successfully!');
    }
    
    async rollback(steps = 1) {
        console.log('🔄 Rolling back migrations...\n');
        
        await this.initialize();
        
        const client = await this.pool.connect();
        try {
            const result = await client.query(
                `SELECT version, name FROM ${this.migrationsTable} 
                 WHERE success = true ORDER BY version DESC LIMIT $1`,
                [steps]
            );
            
            const migrations = result.rows;
            
            if (migrations.length === 0) {
                console.log('📭 No migrations to rollback');
                return;
            }
            
            for (const migration of migrations) {
                const downFile = path.join(
                    this.migrationsDir,
                    `${migration.version}_${migration.name}.down.sql`
                );
                
                try {
                    await fs.access(downFile);
                    const sql = await fs.readFile(downFile, 'utf8');
                    
                    await client.query('BEGIN');
                    await client.query(sql);
                    await client.query(
                        `UPDATE ${this.migrationsTable} SET success = false WHERE version = $1`,
                        [migration.version]
                    );
                    await client.query('COMMIT');
                    
                    console.log(`✅ Rolled back: ${migration.name}`);
                } catch (error) {
                    await client.query('ROLLBACK');
                    console.error(`❌ Failed to rollback: ${migration.name}`);
                    console.error(error);
                    process.exit(1);
                }
            }
        } finally {
            client.release();
        }
        
        console.log('\n🎉 Rollback completed successfully!');
    }
    
    async status() {
        await this.initialize();
        
        const appliedVersions = await this.getAppliedMigrations();
        const migrationFiles = await this.getMigrationFiles();
        
        console.log('\n📊 Migration Status\n');
        console.log('=' .repeat(80));
        
        for (const file of migrationFiles) {
            const isApplied = appliedVersions.includes(file.version);
            const status = isApplied ? '✅ Applied' : '⏳ Pending';
            console.log(`${file.version} - ${file.name} [${status}]`);
        }
        
        console.log('=' .repeat(80));
        console.log(`\nTotal: ${migrationFiles.length} | Applied: ${appliedVersions.length} | Pending: ${migrationFiles.length - appliedVersions.length}\n`);
    }
    
    async close() {
        await this.pool.end();
    }
}

// CLI Interface
const command = process.argv[2];
const args = process.argv.slice(3);

const runner = new MigrationRunner();

(async () => {
    switch (command) {
        case 'migrate':
            await runner.migrate();
            break;
        case 'rollback':
            const steps = parseInt(args[0]) || 1;
            await runner.rollback(steps);
            break;
        case 'status':
            await runner.status();
            break;
        default:
            console.log(`
Usage: node runner.js <command>

Commands:
  migrate              Run all pending migrations
  rollback [steps]     Rollback last [steps] migrations (default: 1)
  status               Show migration status
            `);
    }
    
    await runner.close();
})();