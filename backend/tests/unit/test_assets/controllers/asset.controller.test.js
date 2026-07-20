// parking-management/backend/tests/unit/test_assets/controllers/asset.controller.test.js
const request = require('supertest');
const { app } = require('../../../../../src/app');
const AssetGenerator = require('../helpers/asset-generator');
const UploadHelper = require('../helpers/upload-helper');
const { Asset } = require('../../../../../src/models');

describe('Asset Controller', () => {
  let authToken;
  let testUser;
  let assetGenerator;
  let uploadHelper;
  
  beforeEach(async () => {
    assetGenerator = new AssetGenerator();
    uploadHelper = new UploadHelper();
    
    // Create test user
    const userData = {
      email: 'asset_controller@example.com',
      password: 'Password123!',
      firstName: 'Asset',
      lastName: 'Controller'
    };
    
    const response = await request(app)
      .post('/api/auth/register')
      .send(userData);
    
    testUser = response.body.data.user;
    authToken = response.body.data.token;
  });
  
  afterEach(async () => {
    await assetGenerator.cleanup();
    await uploadHelper.cleanUserUploads(testUser._id);
  });
  
  describe('POST /api/assets/upload', () => {
    it('should upload asset successfully', async () => {
      const testImage = await assetGenerator.generateTestImage();
      const form = await uploadHelper.createFormData({
        filepath: testImage.filepath,
        filename: testImage.filename,
        mimetype: testImage.mimetype,
        fieldname: 'asset'
      });
      
      const response = await request(app)
        .post('/api/assets/upload')
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(201);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body.data).toHaveProperty('asset');
      expect(response.body.data.asset).toHaveProperty('url');
      expect(response.body.data.asset).toHaveProperty('filename');
    });
    
    it('should associate asset with specific type', async () => {
      const testImage = await assetGenerator.generateTestImage();
      const form = await uploadHelper.createFormData({
        filepath: testImage.filepath,
        filename: testImage.filename,
        mimetype: testImage.mimetype,
        fieldname: 'asset'
      });
      
      const response = await request(app)
        .post('/api/assets/upload?type=vehicle')
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(201);
      expect(response.body.data.asset.type).toBe('vehicle');
    });
  });
  
  describe('GET /api/assets/:id', () => {
    let uploadedAsset;
    
    beforeEach(async () => {
      const testImage = await assetGenerator.generateTestImage();
      const form = await uploadHelper.createFormData({
        filepath: testImage.filepath,
        filename: testImage.filename,
        mimetype: testImage.mimetype,
        fieldname: 'asset'
      });
      
      const response = await request(app)
        .post('/api/assets/upload')
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      uploadedAsset = response.body.data.asset;
    });
    
    it('should get asset details', async () => {
      const response = await request(app)
        .get(`/api/assets/${uploadedAsset._id}`)
        .set('Authorization', `Bearer ${authToken}`);
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('filename', uploadedAsset.filename);
      expect(response.body.data).toHaveProperty('size');
      expect(response.body.data).toHaveProperty('mimetype');
      expect(response.body.data).toHaveProperty('url');
    });
    
    it('should return 404 for non-existent asset', async () => {
      const nonExistentId = '507f1f77bcf86cd799439011';
      const response = await request(app)
        .get(`/api/assets/${nonExistentId}`)
        .set('Authorization', `Bearer ${authToken}`);
      
      expect(response.status).toBe(404);
    });
  });
  
  describe('DELETE /api/assets/:id', () => {
    let uploadedAsset;
    
    beforeEach(async () => {
      const testImage = await assetGenerator.generateTestImage();
      const form = await uploadHelper.createFormData({
        filepath: testImage.filepath,
        filename: testImage.filename,
        mimetype: testImage.mimetype,
        fieldname: 'asset'
      });
      
      const response = await request(app)
        .post('/api/assets/upload')
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      uploadedAsset = response.body.data.asset;
    });
    
    it('should delete asset', async () => {
      const response = await request(app)
        .delete(`/api/assets/${uploadedAsset._id}`)
        .set('Authorization', `Bearer ${authToken}`);
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      
      // Verify asset removed from database
      const asset = await Asset.findById(uploadedAsset._id);
      expect(asset).toBeNull();
    });
    
    it('should prevent deleting other user assets', async () => {
      // Create another user
      const otherUser = await request(app)
        .post('/api/auth/register')
        .send({
          email: 'other@example.com',
          password: 'Password123!',
          firstName: 'Other',
          lastName: 'User'
        });
      
      const otherToken = otherUser.body.data.token;
      
      const response = await request(app)
        .delete(`/api/assets/${uploadedAsset._id}`)
        .set('Authorization', `Bearer ${otherToken}`);
      
      expect(response.status).toBe(403);
    });
  });
  
  describe('GET /api/assets/user/assets', () => {
    beforeEach(async () => {
      // Upload multiple assets
      const images = await Promise.all([
        assetGenerator.generateTestImage(),
        assetGenerator.generateTestImage(),
        assetGenerator.generateTestImage()
      ]);
      
      for (const image of images) {
        const form = await uploadHelper.createFormData({
          filepath: image.filepath,
          filename: image.filename,
          mimetype: image.mimetype,
          fieldname: 'asset'
        });
        
        await request(app)
          .post('/api/assets/upload')
          .set('Authorization', `Bearer ${authToken}`)
          .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
          .send(form.getBuffer());
      }
    });
    
    it('should list user assets', async () => {
      const response = await request(app)
        .get('/api/assets/user/assets')
        .set('Authorization', `Bearer ${authToken}`);
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('assets');
      expect(response.body.data.assets).toHaveLength(3);
      expect(response.body.data).toHaveProperty('pagination');
    });
    
    it('should filter by asset type', async () => {
      const response = await request(app)
        .get('/api/assets/user/assets?type=image')
        .set('Authorization', `Bearer ${authToken}`);
      
      expect(response.status).toBe(200);
      expect(response.body.data.assets.every(a => a.mimetype.startsWith('image/'))).toBe(true);
    });
    
    it('should paginate results', async () => {
      const response = await request(app)
        .get('/api/assets/user/assets?page=1&limit=2')
        .set('Authorization', `Bearer ${authToken}`);
      
      expect(response.status).toBe(200);
      expect(response.body.data.assets).toHaveLength(2);
      expect(response.body.data.pagination).toHaveProperty('page', 1);
      expect(response.body.data.pagination).toHaveProperty('limit', 2);
      expect(response.body.data.pagination).toHaveProperty('total', 3);
    });
  });
  
  describe('POST /api/assets/avatar', () => {
    it('should upload and crop avatar', async () => {
      const avatarImage = await assetGenerator.generateTestAvatar(testUser._id, {
        size: 1000
      });
      
      const form = await uploadHelper.createFormData({
        filepath: avatarImage.filepath,
        filename: avatarImage.filename,
        mimetype: avatarImage.mimetype,
        fieldname: 'avatar'
      });
      
      const response = await request(app)
        .post('/api/assets/avatar')
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .field('crop', JSON.stringify({
          x: 100,
          y: 100,
          width: 800,
          height: 800
        }))
        .attach('avatar', avatarImage.filepath);
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('avatarUrl');
      expect(response.body.data).toHaveProperty('thumbnailUrl');
      
      // Verify cropped dimensions
      const sharp = require('sharp');
      const avatarResponse = await request(app)
        .get(response.body.data.avatarUrl);
      
      const metadata = await sharp(avatarResponse.body).metadata();
      expect(metadata.width).toBe(800);
      expect(metadata.height).toBe(800);
    });
  });
  
  describe('POST /api/assets/batch', () => {
    it('should upload multiple assets', async () => {
      const images = await Promise.all([
        assetGenerator.generateTestImage(),
        assetGenerator.generateTestPDF(),
        assetGenerator.generateTestImage()
      ]);
      
      const form = await uploadHelper.createFormData(images.map(img => ({
        filepath: img.filepath,
        filename: img.filename,
        mimetype: img.mimetype,
        fieldname: 'assets'
      })));
      
      const response = await request(app)
        .post('/api/assets/batch')
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('successful');
      expect(response.body.data).toHaveProperty('failed');
      expect(response.body.data.successful).toHaveLength(3);
      expect(response.body.data.failed).toHaveLength(0);
    });
    
    it('should handle partial failures', async () => {
      const validImage = await assetGenerator.generateTestImage();
      const invalidFile = await assetGenerator.generateLargeFile(10); // Too large
      
      const form = await uploadHelper.createFormData([
        {
          filepath: validImage.filepath,
          filename: validImage.filename,
          mimetype: validImage.mimetype,
          fieldname: 'assets'
        },
        {
          filepath: invalidFile.filepath,
          filename: invalidFile.filename,
          mimetype: 'application/octet-stream',
          fieldname: 'assets'
        }
      ]);
      
      const response = await request(app)
        .post('/api/assets/batch')
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(207); // Multi-Status
      expect(response.body.data.successful).toHaveLength(1);
      expect(response.body.data.failed).toHaveLength(1);
      expect(response.body.data.failed[0]).toHaveProperty('error');
    });
  });
});