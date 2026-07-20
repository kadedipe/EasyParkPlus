// parking-management/backend/tests/unit/test_assets/services/cleanup.service.test.js
const CleanupService = require('../../../../../src/services/cleanup.service');
const AssetGenerator = require('../helpers/asset-generator');
const UploadHelper = require('../helpers/upload-helper');
const { Asset } = require('../../../../../src/models');
const fs = require('fs-extra');
const path = require('path');

describe('CleanupService', () => {
  let cleanupService;
  let assetGenerator;
  let uploadHelper;
  let testUser;
  
  beforeEach(async () => {
    cleanupService = new CleanupService();
    assetGenerator = new AssetGenerator();
    uploadHelper = new UploadHelper();
    
    // Create test user
    const userData = {
      email: 'cleanup_test@example.com',
      password: 'Password123!',
      firstName: 'Cleanup',
      lastName: 'Test'
    };
    
    const response = await global.testRequest
      .post('/api/auth/register')
      .send(userData);
    
    testUser = response.body.data.user;
  });
  
  afterEach(async () => {
    await assetGenerator.cleanup();
    await uploadHelper.cleanUserUploads(testUser._id);
  });
  
  describe('cleanupOrphanedFiles', () => {
    it('should remove orphaned files', async () => {
      // Create orphaned file (no database record)
      const orphanedFile = await assetGenerator.generateTestImage();
      const orphanedPath = path.join(global.testUploadDir, 'orphaned', orphanedFile.filename);
      await fs.ensureDir(path.dirname(orphanedPath));
      await fs.copy(orphanedFile.filepath, orphanedPath);
      
      const deleted = await cleanupService.cleanupOrphanedFiles(global.testUploadDir);
      
      expect(deleted).toBe(1);
      expect(await fs.pathExists(orphanedPath)).toBe(false);
    });
    
    it('should not remove files with database records', async () => {
      // Create asset with database record
      const assetFile = await assetGenerator.generateTestImage();
      const assetPath = path.join(global.testUploadDir, 'assets', assetFile.filename);
      await fs.ensureDir(path.dirname(assetPath));
      await fs.copy(assetFile.filepath, assetPath);
      
      await Asset.create({
        filename: assetFile.filename,
        path: assetPath,
        size: assetFile.size,
        mimetype: assetFile.mimetype,
        userId: testUser._id
      });
      
      const deleted = await cleanupService.cleanupOrphanedFiles(global.testUploadDir);
      
      expect(deleted).toBe(0);
      expect(await fs.pathExists(assetPath)).toBe(true);
    });
  });
  
  describe('cleanupExpiredTempFiles', () => {
    it('should remove expired temporary files', async () => {
      // Create old temp file
      const oldTempFile = await assetGenerator.generateTestImage();
      const tempPath = path.join(global.testTempDir, `temp_${Date.now()}.jpg`);
      await fs.copy(oldTempFile.filepath, tempPath);
      
      // Modify file timestamp to 25 hours ago
      const oldDate = new Date(Date.now() - 25 * 60 * 60 * 1000);
      await fs.utimes(tempPath, oldDate, oldDate);
      
      const deleted = await cleanupService.cleanupExpiredTempFiles(global.testTempDir, 24);
      
      expect(deleted).toBe(1);
      expect(await fs.pathExists(tempPath)).toBe(false);
    });
    
    it('should keep recent temporary files', async () => {
      const recentTempFile = await assetGenerator.generateTestImage();
      const tempPath = path.join(global.testTempDir, `temp_${Date.now()}.jpg`);
      await fs.copy(recentTempFile.filepath, tempPath);
      
      const deleted = await cleanupService.cleanupExpiredTempFiles(global.testTempDir, 24);
      
      expect(deleted).toBe(0);
      expect(await fs.pathExists(tempPath)).toBe(true);
    });
  });
  
  describe('cleanupUnusedAssets', () => {
    it('should remove assets not used for specified period', async () => {
      // Create old unused asset
      const oldAsset = await assetGenerator.generateTestImage();
      const form = await uploadHelper.createFormData({
        filepath: oldAsset.filepath,
        filename: oldAsset.filename,
        mimetype: oldAsset.mimetype,
        fieldname: 'asset'
      });
      
      const response = await global.testRequest
        .post('/api/assets/upload')
        .set('Authorization', `Bearer ${testUser.token}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      const asset = response.body.data.asset;
      
      // Manually update last accessed time
      await Asset.findByIdAndUpdate(asset._id, {
        lastAccessedAt: new Date(Date.now() - 31 * 24 * 60 * 60 * 1000)
      });
      
      const deleted = await cleanupService.cleanupUnusedAssets(30);
      
      expect(deleted).toBe(1);
      const deletedAsset = await Asset.findById(asset._id);
      expect(deletedAsset).toBeNull();
    });
  });
  
  describe('compressOldImages', () => {
    it('should compress images older than threshold', async () => {
      // Create large image
      const largeImage = await assetGenerator.generateTestImage({
        width: 2000,
        height: 2000
      });
      
      const form = await uploadHelper.createFormData({
        filepath: largeImage.filepath,
        filename: largeImage.filename,
        mimetype: largeImage.mimetype,
        fieldname: 'asset'
      });
      
      const response = await global.testRequest
        .post('/api/assets/upload')
        .set('Authorization', `Bearer ${testUser.token}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      const asset = response.body.data.asset;
      const originalSize = asset.size;
      
      // Manually update creation time
      await Asset.findByIdAndUpdate(asset._id, {
        createdAt: new Date(Date.now() - 31 * 24 * 60 * 60 * 1000)
      });
      
      const compressed = await cleanupService.compressOldImages(30, 80);
      
      expect(compressed).toBe(1);
      
      const updatedAsset = await Asset.findById(asset._id);
      expect(updatedAsset.size).toBeLessThan(originalSize);
      expect(updatedAsset.compressed).toBe(true);
    });
  });
  
  describe('generateCleanupReport', () => {
    it('should generate cleanup report', async () => {
      const report = await cleanupService.generateCleanupReport();
      
      expect(report).toHaveProperty('timestamp');
      expect(report).toHaveProperty('summary');
      expect(report.summary).toHaveProperty('totalAssets');
      expect(report.summary).toHaveProperty('totalSize');
      expect(report.summary).toHaveProperty('orphanedFiles');
      expect(report.summary).toHaveProperty('tempFiles');
      expect(report).toHaveProperty('recommendations');
    });
    
    it('should include detailed breakdown', async () => {
      const report = await cleanupService.generateCleanupReport(true);
      
      expect(report).toHaveProperty('details');
      expect(report.details).toHaveProperty('assetsByType');
      expect(report.details).toHaveProperty('assetsByUser');
      expect(report.details).toHaveProperty('storageByMonth');
    });
  });
});