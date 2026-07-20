#!/usr/bin/env node
// parking-management/backend/src/scripts/backup-cli.js
import { program } from 'commander';
import { backupService } from '../services/backupService.js';

program
  .name('backup')
  .description('Database backup management tool');

program
  .command('create')
  .description('Create a new backup')
  .action(async () => {
    console.log('Creating backup...');
    const result = await backupService.createBackup();
    if (result.success) {
      console.log(`✅ Backup created: ${result.backupName}`);
      console.log(`📦 Size: ${(result.metadata.size / 1024 / 1024).toFixed(2)} MB`);
      console.log(`🔗 Path: ${result.path}`);
    } else {
      console.error(`❌ Backup failed: ${result.error}`);
    }
  });

program
  .command('list')
  .description('List available backups')
  .action(() => {
    const backups = backupService.listBackups();
    console.log('📋 Available backups:');
    console.log('─'.repeat(70));
    backups.forEach((backup, i) => {
      const size = (backup.size / 1024 / 1024).toFixed(2);
      console.log(`${(i + 1).toString().padStart(2)}. ${backup.name.padEnd(40)} ${size} MB`);
    });
    console.log('─'.repeat(70));
    console.log(`Total: ${backups.length} backups`);
  });

program
  .command('restore <backupName>')
  .description('Restore database from backup')
  .action(async (backupName) => {
    console.log(`Restoring database from: ${backupName}`);
    const result = await backupService.restoreBackup(backupName);
    if (result.success) {
      console.log('✅ Database restored successfully');
    } else {
      console.error(`❌ Restore failed: ${result.error}`);
    }
  });

program
  .command('status')
  .description('Show backup status')
  .action(async () => {
    const stats = await backupService.getBackupStats();
    console.log('📊 Backup Status:');
    console.log('─'.repeat(40));
    console.log(`Total Backups: ${stats.totalBackups}`);
    console.log(`Total Size: ${(stats.totalSize / 1024 / 1024).toFixed(2)} MB`);
    console.log(`Retention Days: ${stats.retentionDays}`);
    if (stats.lastBackup) {
      console.log(`Last Backup: ${stats.lastBackup.createdAt}`);
      console.log(`Last Backup Size: ${(stats.lastBackup.size / 1024 / 1024).toFixed(2)} MB`);
    }
    console.log(`Status: ${stats.status.status || 'unknown'}`);
  });

program
  .command('cleanup')
  .description('Clean up old backups')
  .action(async () => {
    console.log('Cleaning up old backups...');
    await backupService.cleanupOldBackups();
    console.log('✅ Cleanup completed');
  });

program.parse();