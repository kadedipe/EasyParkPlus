// parking-management/backend/tests/unit/test_assets/services/asset.service.test.js
const AssetService = require('../../../../../src/services/asset.service');
const AssetGenerator = require('../helpers/asset-generator');
const UploadHelper = require('../helpers/upload-helper');
const { Asset, User, ParkingSpot } = require('../../../../../src/models');
const fs = require('fs-extra');
const path = require('path');

describe('AssetService', () => {
  let assetService;
  let assetGenerator;
  let uploadHelper;
  let testUser;
  let testSpot;
  let authToken;
  
  beforeEach(async () => {
    assetService = new AssetService();
    assetGenerator = new AssetGenerator();
    uploadHelper = new UploadHelper();
    
    // Create test user
    const userData = {
      email: 'asset_test@example.com',
      password: 'Password123!',
      firstName: 'Asset',
      lastName: 'Tester'
    };
    
    const response = await global.testRequest
      .post('/api/auth/register')
      .send(userData);
    
    testUser = response.body.data.user;
    authToken = response.body.data.token;
    
    // Create test parking spot
    const spotData = {
      name: 'Asset Test Spot',
      location: {
        latitude: 40.7128,
        longitude: -74.0060,
        address: '123 Test St'
      },
      pricePerHour: 10
    };
    
    const spotResponse = await global.testRequest
      .post('/api/parking-spots')
      .set('Authorization', `Bearer ${authToken}`)
      .send(spotData);
    
    testSpot = spotResponse.body.data;
  });
  
  afterEach(async () => {
    await assetGenerator.cleanup();
    await uploadHelper.cleanUserUploads(testUser._id);
  });
  
  describe('uploadAvatar', () => {
    it('should upload user avatar successfully', async () => {
      const avatar = await assetGenerator.generateTestAvatar(testUser._id);
      const form = await uploadHelper.createFormData({
        filepath: avatar.filepath,
        filename: avatar.filename,
        mimetype: avatar.mimetype,
        fieldname: 'avatar'
      });
      
      const response = await global.testRequest
        .post('/api/users/avatar')
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body.data).toHaveProperty('avatarUrl');
      expect(response.body.data).toHaveProperty('thumbnailUrl');
      
      // Verify avatar URL is valid
      const avatarResponse = await global.testRequest
        .get(response.body.data.avatarUrl);
      expect(avatarResponse.status).toBe(200);
      
      // Check user model updated
      const user = await User.findById(testUser._id);
      expect(user.avatar).toBeTruthy();
      expect(user.avatar).toHaveProperty('url');
      expect(user.avatar).toHaveProperty('thumbnail');
    });
    
    it('should resize avatar to correct dimensions', async () => {
      const largeAvatar = await assetGenerator.generateTestAvatar(testUser._id, {
        size: 2000
      });
      
      const form = await uploadHelper.createFormData({
        filepath: largeAvatar.filepath,
        filename: largeAvatar.filename,
        mimetype: largeAvatar.mimetype,
        fieldname: 'avatar'
      });
      
      const response = await global.testRequest
        .post('/api/users/avatar')
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(200);
      
      // Download and check dimensions
      const sharp = require('sharp');
      const avatarResponse = await global.testRequest
        .get(response.body.data.avatarUrl);
      
      const metadata = await sharp(avatarResponse.body).metadata();
      expect(metadata.width).toBeLessThanOrEqual(500);
      expect(metadata.height).toBeLessThanOrEqual(500);
    });
    
    it('should reject invalid image formats', async () => {
      const invalidImage = await assetGenerator.generateTestImage({
        format: 'bmp'
      });
      
      const form = await uploadHelper.createFormData({
        filepath: invalidImage.filepath,
        filename: invalidImage.filename,
        mimetype: invalidImage.mimetype,
        fieldname: 'avatar'
      });
      
      const response = await global.testRequest
        .post('/api/users/avatar')
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Invalid file type');
    });
    
    it('should reject files exceeding size limit', async () => {
      const largeFile = await assetGenerator.generateLargeFile(6); // 6MB
      
      const form = await uploadHelper.createFormData({
        filepath: largeFile.filepath,
        filename: largeFile.filename,
        mimetype: 'image/jpeg',
        fieldname: 'avatar'
      });
      
      const response = await global.testRequest
        .post('/api/users/avatar')
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(413);
      expect(response.body).toHaveProperty('message', 'File too large');
    });
  });
  
  describe('uploadVehicleImage', () => {
    let testVehicle;
    
    beforeEach(async () => {
      // Create test vehicle
      const vehicleResponse = await global.testRequest
        .post('/api/users/vehicles')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          plateNumber: 'VEH123',
          make: 'Tesla',
          model: 'Model 3',
          year: 2023,
          color: 'Red'
        });
      
      testVehicle = vehicleResponse.body.data;
    });
    
    it('should upload vehicle image successfully', async () => {
      const vehicleImage = await assetGenerator.generateTestImage({
        width: 1024,
        height: 768,
        text: 'Test Vehicle'
      });
      
      const form = await uploadHelper.createFormData({
        filepath: vehicleImage.filepath,
        filename: vehicleImage.filename,
        mimetype: vehicleImage.mimetype,
        fieldname: 'image'
      });
      
      const response = await global.testRequest
        .post(`/api/users/vehicles/${testVehicle._id}/image`)
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('imageUrl');
      
      // Verify image saved
      const vehicle = await global.testRequest
        .get(`/api/users/vehicles/${testVehicle._id}`)
        .set('Authorization', `Bearer ${authToken}`);
      
      expect(vehicle.body.data).toHaveProperty('image');
    });
    
    it('should generate multiple image sizes', async () => {
      const vehicleImage = await assetGenerator.generateTestImage();
      
      const form = await uploadHelper.createFormData({
        filepath: vehicleImage.filepath,
        filename: vehicleImage.filename,
        mimetype: vehicleImage.mimetype,
        fieldname: 'image'
      });
      
      const response = await global.testRequest
        .post(`/api/users/vehicles/${testVehicle._id}/image`)
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('sizes');
      expect(response.body.data.sizes).toHaveProperty('thumbnail');
      expect(response.body.data.sizes).toHaveProperty('medium');
      expect(response.body.data.sizes).toHaveProperty('large');
    });
  });
  
  describe('uploadParkingSpotImage', () => {
    it('should upload parking spot image as admin', async () => {
      // Create admin user
      const adminData = {
        email: 'admin_asset@example.com',
        password: 'Admin123!',
        firstName: 'Admin',
        lastName: 'Asset',
        role: 'admin'
      };
      
      const adminResponse = await global.testRequest
        .post('/api/auth/register')
        .send(adminData);
      
      const adminToken = adminResponse.body.data.token;
      
      const spotImage = await assetGenerator.generateParkingSpotImage(testSpot._id);
      
      const form = await uploadHelper.createFormData({
        filepath: spotImage.filepath,
        filename: spotImage.filename,
        mimetype: spotImage.mimetype,
        fieldname: 'image'
      });
      
      const response = await global.testRequest
        .post(`/api/parking-spots/${testSpot._id}/image`)
        .set('Authorization', `Bearer ${adminToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('imageUrl');
      
      // Verify spot updated
      const spot = await ParkingSpot.findById(testSpot._id);
      expect(spot.images).toBeDefined();
      expect(spot.images.length).toBeGreaterThan(0);
    });
    
    it('should prevent non-admin from uploading spot images', async () => {
      const spotImage = await assetGenerator.generateParkingSpotImage(testSpot._id);
      
      const form = await uploadHelper.createFormData({
        filepath: spotImage.filepath,
        filename: spotImage.filename,
        mimetype: spotImage.mimetype,
        fieldname: 'image'
      });
      
      const response = await global.testRequest
        .post(`/api/parking-spots/${testSpot._id}/image`)
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(403);
    });
  });
  
  describe('uploadDocument', () => {
    it('should upload document successfully', async () => {
      const document = await assetGenerator.generateTestPDF({
        title: 'Parking Permit',
        content: 'This is a valid parking permit document.',
        pages: 2
      });
      
      const form = await uploadHelper.createFormData({
        filepath: document.filepath,
        filename: document.filename,
        mimetype: document.mimetype,
        fieldname: 'document'
      });
      
      const response = await global.testRequest
        .post('/api/users/documents')
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(201);
      expect(response.body.data).toHaveProperty('documentUrl');
      expect(response.body.data).toHaveProperty('metadata');
      expect(response.body.data.metadata).toHaveProperty('pages', 2);
    });
    
    it('should handle multiple document uploads', async () => {
      const documents = await Promise.all([
        assetGenerator.generateTestPDF({ title: 'Doc 1' }),
        assetGenerator.generateTestPDF({ title: 'Doc 2' }),
        assetGenerator.generateTestDocument({ type: 'docx' })
      ]);
      
      const form = await uploadHelper.createFormData(documents.map(doc => ({
        filepath: doc.filepath,
        filename: doc.filename,
        mimetype: doc.mimetype,
        fieldname: 'documents'
      })));
      
      const response = await global.testRequest
        .post('/api/users/documents/batch')
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(200);
      expect(response.body.data).toHaveProperty('documents');
      expect(response.body.data.documents).toHaveLength(3);
      expect(response.body.data).toHaveProperty('failed');
      expect(response.body.data.failed).toHaveLength(0);
    });
    
    it('should reject invalid document types', async () => {
      const invalidDoc = await assetGenerator.generateTestDocument({ type: 'exe' });
      
      const form = await uploadHelper.createFormData({
        filepath: invalidDoc.filepath,
        filename: invalidDoc.filename,
        mimetype: 'application/x-msdownload',
        fieldname: 'document'
      });
      
      const response = await global.testRequest
        .post('/api/users/documents')
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Invalid document type');
    });
  });
  
  describe('getAsset', () => {
    let uploadedAvatar;
    
    beforeEach(async () => {
      const avatar = await assetGenerator.generateTestAvatar(testUser._id);
      const form = await uploadHelper.createFormData({
        filepath: avatar.filepath,
        filename: avatar.filename,
        mimetype: avatar.mimetype,
        fieldname: 'avatar'
      });
      
      const response = await global.testRequest
        .post('/api/users/avatar')
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      uploadedAvatar = response.body.data;
    });
    
    it('should serve asset file', async () => {
      const response = await global.testRequest
        .get(uploadedAvatar.avatarUrl);
      
      expect(response.status).toBe(200);
      expect(response.headers['content-type']).toMatch(/image/);
    });
    
    it('should serve thumbnail version', async () => {
      const response = await global.testRequest
        .get(uploadedAvatar.thumbnailUrl);
      
      expect(response.status).toBe(200);
      
      // Verify dimensions
      const sharp = require('sharp');
      const metadata = await sharp(response.body).metadata();
      expect(metadata.width).toBeLessThanOrEqual(150);
      expect(metadata.height).toBeLessThanOrEqual(150);
    });
    
    it('should return 404 for non-existent asset', async () => {
      const response = await global.testRequest
        .get('/uploads/nonexistent/file.jpg');
      
      expect(response.status).toBe(404);
    });
    
    it('should cache assets', async () => {
      const response = await global.testRequest
        .get(uploadedAvatar.avatarUrl);
      
      expect(response.headers['cache-control']).toBeDefined();
      expect(response.headers['etag']).toBeDefined();
      
      // Test conditional GET
      const cachedResponse = await global.testRequest
        .get(uploadedAvatar.avatarUrl)
        .set('If-None-Match', response.headers.etag);
      
      expect(cachedResponse.status).toBe(304);
    });
  });
  
  describe('deleteAsset', () => {
    let uploadedDocument;
    
    beforeEach(async () => {
      const document = await assetGenerator.generateTestPDF();
      const form = await uploadHelper.createFormData({
        filepath: document.filepath,
        filename: document.filename,
        mimetype: document.mimetype,
        fieldname: 'document'
      });
      
      const response = await global.testRequest
        .post('/api/users/documents')
        .set('Authorization', `Bearer ${authToken}`)
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      uploadedDocument = response.body.data;
    });
    
    it('should delete asset', async () => {
      const response = await global.testRequest
        .delete(`/api/users/documents/${uploadedDocument._id}`)
        .set('Authorization', `Bearer ${authToken}`);
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      
      // Verify file deleted
      const asset = await Asset.findById(uploadedDocument._id);
      expect(asset).toBeNull();
      
      const fileExists = await fs.pathExists(uploadedDocument.filepath);
      expect(fileExists).toBe(false);
    });
    
    it('should prevent deleting other user assets', async () => {
      const otherUser = await global.testRequest
        .post('/api/auth/register')
        .send({
          email: 'other@example.com',
          password: 'Password123!',
          firstName: 'Other',
          lastName: 'User'
        });
      
      const otherToken = otherUser.body.data.token;
      
      const response = await global.testRequest
        .delete(`/api/users/documents/${uploadedDocument._id}`)
        .set('Authorization', `Bearer ${otherToken}`);
      
      expect(response.status).toBe(403);
    });
  });
});