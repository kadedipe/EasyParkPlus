// parking-management/backend/tests/unit/test_assets/models/asset.model.test.js
const { Asset } = require('../../../../../src/models');
const AssetGenerator = require('../helpers/asset-generator');

describe('Asset Model', () => {
  let assetGenerator;
  
  beforeEach(() => {
    assetGenerator = new AssetGenerator();
  });
  
  describe('validation', () => {
    it('should create valid asset', async () => {
      const testImage = await assetGenerator.generateTestImage();
      
      const assetData = {
        filename: testImage.filename,
        originalName: testImage.filename,
        path: `/uploads/${testImage.filename}`,
        url: `http://localhost:3000/uploads/${testImage.filename}`,
        size: testImage.size,
        mimetype: testImage.mimetype,
        type: 'avatar',
        userId: new mongoose.Types.ObjectId(),
        metadata: {
          width: testImage.width,
          height: testImage.height,
          format: testImage.format
        }
      };
      
      const asset = new Asset(assetData);
      const savedAsset = await asset.save();
      
      expect(savedAsset._id).toBeDefined();
      expect(savedAsset.filename).toBe(assetData.filename);
      expect(savedAsset.size).toBe(assetData.size);
      expect(savedAsset.metadata).toMatchObject(assetData.metadata);
    });
    
    it('should require filename', async () => {
      const asset = new Asset({
        path: '/uploads/file.jpg',
        size: 1024,
        mimetype: 'image/jpeg'
      });
      
      let error;
      try {
        await asset.save();
      } catch (err) {
        error = err;
      }
      
      expect(error).toBeDefined();
      expect(error.errors.filename).toBeDefined();
    });
    
    it('should validate file size', async () => {
      const asset = new Asset({
        filename: 'test.jpg',
        path: '/uploads/test.jpg',
        size: -1,
        mimetype: 'image/jpeg'
      });
      
      let error;
      try {
        await asset.save();
      } catch (err) {
        error = err;
      }
      
      expect(error).toBeDefined();
      expect(error.errors.size).toBeDefined();
    });
    
    it('should validate URL format', async () => {
      const asset = new Asset({
        filename: 'test.jpg',
        path: '/uploads/test.jpg',
        url: 'invalid-url',
        size: 1024,
        mimetype: 'image/jpeg'
      });
      
      let error;
      try {
        await asset.save();
      } catch (err) {
        error = err;
      }
      
      expect(error).toBeDefined();
      expect(error.errors.url).toBeDefined();
    });
  });
  
  describe('virtuals', () => {
    it('should generate file extension', async () => {
      const asset = new Asset({
        filename: 'test-image.jpg',
        path: '/uploads/test-image.jpg',
        size: 1024,
        mimetype: 'image/jpeg'
      });
      
      expect(asset.extension).toBe('jpg');
    });
    
    it('should generate thumbnail URL', async () => {
      const asset = new Asset({
        filename: 'test-image.jpg',
        path: '/uploads/test-image.jpg',
        size: 1024,
        mimetype: 'image/jpeg'
      });
      
      expect(asset.thumbnailUrl).toContain('/thumbnails/');
    });
  });
  
  describe('methods', () => {
    let asset;
    
    beforeEach(async () => {
      const testImage = await assetGenerator.generateTestImage();
      asset = new Asset({
        filename: testImage.filename,
        originalName: testImage.filename,
        path: `/uploads/${testImage.filename}`,
        size: testImage.size,
        mimetype: testImage.mimetype,
        type: 'avatar'
      });
      await asset.save();
    });
    
    it('should mark as deleted', async () => {
      await asset.markAsDeleted();
      
      expect(asset.isDeleted).toBe(true);
      expect(asset.deletedAt).toBeDefined();
    });
    
    it('should get public URL', () => {
      const url = asset.getPublicUrl();
      expect(url).toContain('/uploads/');
    });
    
    it('should check if image', () => {
      expect(asset.isImage()).toBe(true);
    });
    
    it('should check if document', () => {
      const documentAsset = new Asset({
        filename: 'test.pdf',
        path: '/uploads/test.pdf',
        size: 1024,
        mimetype: 'application/pdf'
      });
      
      expect(documentAsset.isDocument()).toBe(true);
    });
  });
  
  describe('statics', () => {
    beforeEach(async () => {
      const testImage1 = await assetGenerator.generateTestImage();
      const testImage2 = await assetGenerator.generateTestImage();
      const userId = new mongoose.Types.ObjectId();
      
      await Asset.create({
        filename: testImage1.filename,
        path: `/uploads/${testImage1.filename}`,
        size: testImage1.size,
        mimetype: testImage1.mimetype,
        userId,
        type: 'avatar'
      });
      
      await Asset.create({
        filename: testImage2.filename,
        path: `/uploads/${testImage2.filename}`,
        size: testImage2.size,
        mimetype: testImage2.mimetype,
        userId,
        type: 'document'
      });
    });
    
    it('should find by user', async () => {
      const assets = await Asset.findByUser(userId);
      expect(assets).toHaveLength(2);
    });
    
    it('should find by type', async () => {
      const avatars = await Asset.findByType('avatar');
      expect(avatars).toHaveLength(1);
      expect(avatars[0].type).toBe('avatar');
    });
    
    it('should cleanup orphaned', async () => {
      // Create orphaned asset (no userId)
      const orphanedImage = await assetGenerator.generateTestImage();
      await Asset.create({
        filename: orphanedImage.filename,
        path: `/uploads/${orphanedImage.filename}`,
        size: orphanedImage.size,
        mimetype: orphanedImage.mimetype,
        createdAt: new Date(Date.now() - 86400000 * 8) // 8 days old
      });
      
      const deleted = await Asset.cleanupOrphaned(7); // 7 days
      expect(deleted).toBe(1);
    });
  });
});