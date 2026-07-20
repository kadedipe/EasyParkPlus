// parking-management/backend/src/services/backupService.js
import { DeleteObjectCommand, ListObjectsCommand, PutObjectCommand, S3Client } from '@aws-sdk/client-s3';
import { exec } from 'child_process';
import { format } from 'date-fns';
import fs from 'fs';
import path from 'path';
import { createClient } from 'redis';
import { promisify } from 'util';
import { logger } from '../utils/logger.js';

const execAsync = promisify(exec);

class BackupService {
  constructor() {
    this.backupDir = process.env.BACKUP_DIR || './backups';
    this.retentionDays = parseInt(process.env.BACKUP_RETENTION_DAYS) || 30;
    this.dbName = process.env.DB_NAME || 'parking_db';
    this.dbUser = process.env.DB_USER || 'user';
    this.dbHost = process.env.DB_HOST || 'localhost';
    this.dbPort = process.env.DB_PORT || '5432';
    this.isBackupRunning = false;
    
    // S3 Configuration for offsite backups
    this.s3Client = new S3Client({
      region: process.env.AWS_REGION || 'us-east-1',
      credentials: {
        accessKeyId: process.env.AWS_ACCESS_KEY_ID,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
      },
    });
    this.s3Bucket = process.env.AWS_S3_BACKUP_BUCKET;

    // Redis client for backup status
    this.redisClient = createClient({
      url: process.env.REDIS_URL || 'redis://localhost:6379',
    });
    this.redisClient.connect().catch(err => {
      logger.error('Redis connection error:', err);
    });

    // Ensure backup directory exists
    this.ensureBackupDirectory();
  }

  /**
   * Ensure backup directory exists
   */
  ensureBackupDirectory() {
    if (!fs.existsSync(this.backupDir)) {
      fs.mkdirSync(this.backupDir, { recursive: true });
    }
  }

  /**
   * Create a full database backup
   */
  async createBackup(options = {}) {
    if (this.isBackupRunning) {
      logger.warn('Backup already in progress');
      return { success: false, message: 'Backup already in progress' };
    }

    this.isBackupRunning = true;
    const startTime = Date.now();

    try {
      const timestamp = format(new Date(), 'yyyy-MM-dd-HH-mm-ss');
      const backupName = `${this.dbName}-${timestamp}`;
      const backupPath = path.join(this.backupDir, `${backupName}.sql`);
      const compressedPath = `${backupPath}.gz`;

      logger.info(`Starting database backup: ${backupName}`);

      // Update backup status in Redis
      await this.setBackupStatus('running', { backupName, startTime: new Date().toISOString() });

      // Step 1: Create backup
      await this.createDatabaseBackup(backupPath);
      logger.info(`Database backup created: ${backupPath}`);

      // Step 2: Compress backup
      await this.compressBackup(backupPath, compressedPath);
      logger.info(`Backup compressed: ${compressedPath}`);

      // Step 3: Calculate checksum
      const checksum = await this.calculateChecksum(compressedPath);
      logger.info(`Backup checksum: ${checksum}`);

      // Step 4: Upload to S3 (if configured)
      let s3Url = null;
      if (this.s3Bucket) {
        s3Url = await this.uploadToS3(compressedPath, backupName);
        logger.info(`Backup uploaded to S3: ${s3Url}`);
      }

      // Step 5: Clean up old backups
      await this.cleanupOldBackups();

      // Step 6: Log backup metadata
      const metadata = {
        backupName,
        timestamp,
        size: fs.statSync(compressedPath).size,
        checksum,
        s3Url,
        duration: Date.now() - startTime,
        type: 'full',
        status: 'success',
      };

      await this.logBackupMetadata(metadata);

      // Update backup status
      await this.setBackupStatus('completed', metadata);

      logger.info(`Backup completed successfully: ${backupName}`, metadata);

      return {
        success: true,
        backupName,
        metadata,
        path: compressedPath,
      };

    } catch (error) {
      logger.error('Backup failed:', error);
      
      // Update backup status
      await this.setBackupStatus('failed', {
        error: error.message,
        timestamp: new Date().toISOString(),
      });

      return {
        success: false,
        error: error.message,
      };

    } finally {
      this.isBackupRunning = false;
    }
  }

  /**
   * Create database backup using pg_dump
   */
  async createDatabaseBackup(outputPath) {
    const command = `PGPASSWORD=${process.env.DB_PASSWORD} pg_dump -h ${this.dbHost} -p ${this.dbPort} -U ${this.dbUser} -d ${this.dbName} -F p -f ${outputPath}`;
    
    const { stdout, stderr } = await execAsync(command);
    
    if (stderr && !stderr.includes('warning')) {
      throw new Error(`pg_dump error: ${stderr}`);
    }
    
    return outputPath;
  }

  /**
   * Compress backup file
   */
  async compressBackup(inputPath, outputPath) {
    const command = `gzip -c ${inputPath} > ${outputPath}`;
    
    const { stderr } = await execAsync(command);
    
    if (stderr) {
      throw new Error(`Compression error: ${stderr}`);
    }
    
    // Remove uncompressed file
    fs.unlinkSync(inputPath);
    
    return outputPath;
  }

  /**
   * Calculate file checksum
   */
  async calculateChecksum(filePath) {
    const command = `sha256sum ${filePath}`;
    const { stdout } = await execAsync(command);
    return stdout.split(' ')[0];
  }

  /**
   * Upload backup to S3
   */
  async uploadToS3(filePath, backupName) {
    const key = `backups/${backupName}.sql.gz`;
    const fileContent = fs.readFileSync(filePath);
    
    const command = new PutObjectCommand({
      Bucket: this.s3Bucket,
      Key: key,
      Body: fileContent,
      ContentType: 'application/gzip',
      Metadata: {
        timestamp: new Date().toISOString(),
        backupName,
        checksum: await this.calculateChecksum(filePath),
      },
    });

    await this.s3Client.send(command);
    
    return `s3://${this.s3Bucket}/${key}`;
  }

  /**
   * Clean up old backups (local and S3)
   */
  async cleanupOldBackups() {
    // Clean local backups
    const files = fs.readdirSync(this.backupDir);
    const backupFiles = files.filter(f => f.endsWith('.sql.gz'));
    
    // Sort by timestamp (oldest first)
    backupFiles.sort((a, b) => {
      const aTime = fs.statSync(path.join(this.backupDir, a)).mtime;
      const bTime = fs.statSync(path.join(this.backupDir, b)).mtime;
      return aTime - bTime;
    });

    // Remove old backups
    const keepCount = Math.min(backupFiles.length, 7); // Keep last 7 daily backups
    const toDelete = backupFiles.slice(0, -keepCount);
    
    for (const file of toDelete) {
      const filePath = path.join(this.backupDir, file);
      fs.unlinkSync(filePath);
      logger.info(`Deleted old backup: ${file}`);
    }

    // Clean S3 backups if configured
    if (this.s3Bucket) {
      await this.cleanupS3Backups();
    }
  }

  /**
   * Clean up old S3 backups
   */
  async cleanupS3Backups() {
    const command = new ListObjectsCommand({
      Bucket: this.s3Bucket,
      Prefix: 'backups/',
    });

    const response = await this.s3Client.send(command);
    
    if (!response.Contents || response.Contents.length === 0) {
      return;
    }

    // Sort by last modified (oldest first)
    response.Contents.sort((a, b) => a.LastModified - b.LastModified);
    
    // Keep last 30 days of backups
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - this.retentionDays);
    
    const toDelete = response.Contents.filter(obj => obj.LastModified < cutoff);
    
    for (const obj of toDelete) {
      const deleteCommand = new DeleteObjectCommand({
        Bucket: this.s3Bucket,
        Key: obj.Key,
      });
      
      await this.s3Client.send(deleteCommand);
      logger.info(`Deleted old S3 backup: ${obj.Key}`);
    }
  }

  /**
   * Set backup status in Redis
   */
  async setBackupStatus(status, data = {}) {
    try {
      await this.redisClient.set(
        'backup:status',
        JSON.stringify({
          status,
          ...data,
          updatedAt: new Date().toISOString(),
        })
      );
    } catch (error) {
      logger.error('Failed to set backup status:', error);
    }
  }

  /**
   * Log backup metadata
   */
  async logBackupMetadata(metadata) {
    const metadataPath = path.join(this.backupDir, 'backup-metadata.json');
    
    let existingMetadata = [];
    if (fs.existsSync(metadataPath)) {
      const content = fs.readFileSync(metadataPath, 'utf8');
      existingMetadata = JSON.parse(content);
    }
    
    existingMetadata.push(metadata);
    
    // Keep only last 100 entries
    if (existingMetadata.length > 100) {
      existingMetadata = existingMetadata.slice(-100);
    }
    
    fs.writeFileSync(metadataPath, JSON.stringify(existingMetadata, null, 2));
  }

  /**
   * List available backups
   */
  listBackups() {
    const files = fs.readdirSync(this.backupDir);
    const backupFiles = files
      .filter(f => f.endsWith('.sql.gz'))
      .map(f => ({
        name: f,
        path: path.join(this.backupDir, f),
        size: fs.statSync(path.join(this.backupDir, f)).size,
        createdAt: fs.statSync(path.join(this.backupDir, f)).mtime,
      }))
      .sort((a, b) => b.createdAt - a.createdAt);
    
    return backupFiles;
  }

  /**
   * Restore database from backup
   */
  async restoreBackup(backupName) {
    const backupPath = path.join(this.backupDir, backupName);
    
    if (!fs.existsSync(backupPath)) {
      throw new Error(`Backup not found: ${backupName}`);
    }

    logger.info(`Starting database restore: ${backupName}`);

    try {
      // Step 1: Decompress backup
      const decompressedPath = backupPath.replace('.gz', '');
      await this.decompressBackup(backupPath, decompressedPath);
      
      // Step 2: Restore database
      await this.restoreDatabase(decompressedPath);
      
      // Step 3: Clean up decompressed file
      fs.unlinkSync(decompressedPath);
      
      logger.info(`Database restored successfully: ${backupName}`);
      
      return { success: true, backupName };
      
    } catch (error) {
      logger.error('Restore failed:', error);
      throw error;
    }
  }

  /**
   * Decompress backup file
   */
  async decompressBackup(inputPath, outputPath) {
    const command = `gunzip -c ${inputPath} > ${outputPath}`;
    const { stderr } = await execAsync(command);
    
    if (stderr) {
      throw new Error(`Decompression error: ${stderr}`);
    }
    
    return outputPath;
  }

  /**
   * Restore database using psql
   */
  async restoreDatabase(filePath) {
    const command = `PGPASSWORD=${process.env.DB_PASSWORD} psql -h ${this.dbHost} -p ${this.dbPort} -U ${this.dbUser} -d ${this.dbName} -f ${filePath}`;
    
    const { stderr } = await execAsync(command);
    
    if (stderr && !stderr.includes('ERROR')) {
      throw new Error(`Restore error: ${stderr}`);
    }
    
    return true;
  }

  /**
   * Get backup statistics
   */
  async getBackupStats() {
    const backups = this.listBackups();
    const totalSize = backups.reduce((sum, b) => sum + b.size, 0);
    
    let status = 'unknown';
    try {
      const statusData = await this.redisClient.get('backup:status');
      if (statusData) {
        status = JSON.parse(statusData);
      }
    } catch (error) {
      logger.error('Failed to get backup status:', error);
    }

    return {
      totalBackups: backups.length,
      totalSize: totalSize,
      lastBackup: backups[0] || null,
      status,
      retentionDays: this.retentionDays,
    };
  }
}

// Create singleton instance
export const backupService = new BackupService();

// Schedule automated backups
if (process.env.NODE_ENV === 'production') {
  // Run backup every day at 2 AM
  cron.schedule('0 2 * * *', async () => {
    logger.info('Scheduled backup started');
    try {
      await backupService.createBackup();
    } catch (error) {
      logger.error('Scheduled backup failed:', error);
    }
  });
}

export default backupService;