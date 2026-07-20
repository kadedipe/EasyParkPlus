// parking-management/backend/tests/unit/test_assets/middleware/upload.middleware.test.js
const request = require('supertest');
const express = require('express');
const uploadMiddleware = require('../../../../../src/middleware/upload.middleware');
const AssetGenerator = require('../helpers/asset-generator');
const UploadHelper = require('../helpers/upload-helper');

describe('Upload Middleware', () => {
  let app;
  let assetGenerator;
  let uploadHelper;
  
  beforeEach(() => {
    app = express();
    assetGenerator = new AssetGenerator();
    uploadHelper = new UploadHelper();
  });
  
  describe('single file upload', () => {
    it('should handle single file upload', async () => {
      app.post('/upload', uploadMiddleware.single('file'), (req, res) => {
        res.json({ file: req.file });
      });
      
      const testImage = await assetGenerator.generateTestImage();
      const form = await uploadHelper.createFormData({
        filepath: testImage.filepath,
        filename: testImage.filename,
        mimetype: testImage.mimetype,
        fieldname: 'file'
      });
      
      const response = await request(app)
        .post('/upload')
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(200);
      expect(response.body.file).toHaveProperty('originalname', testImage.filename);
      expect(response.body.file).toHaveProperty('mimetype', testImage.mimetype);
      expect(response.body.file).toHaveProperty('size');
    });
    
    it('should reject request with no file', async () => {
      app.post('/upload', uploadMiddleware.single('file'), (req, res) => {
        res.json({ file: req.file });
      });
      
      const form = new (require('form-data'))();
      form.append('other', 'value');
      
      const response = await request(app)
        .post('/upload')
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'No file uploaded');
    });
  });
  
  describe('multiple file upload', () => {
    it('should handle multiple file uploads', async () => {
      app.post('/upload', uploadMiddleware.array('files', 5), (req, res) => {
        res.json({ files: req.files });
      });
      
      const images = await Promise.all([
        assetGenerator.generateTestImage(),
        assetGenerator.generateTestImage(),
        assetGenerator.generateTestImage()
      ]);
      
      const form = await uploadHelper.createFormData(images.map(img => ({
        filepath: img.filepath,
        filename: img.filename,
        mimetype: img.mimetype,
        fieldname: 'files'
      })));
      
      const response = await request(app)
        .post('/upload')
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(200);
      expect(response.body.files).toHaveLength(3);
    });
    
    it('should enforce file count limit', async () => {
      app.post('/upload', uploadMiddleware.array('files', 2), (req, res) => {
        res.json({ files: req.files });
      });
      
      const images = await Promise.all([
        assetGenerator.generateTestImage(),
        assetGenerator.generateTestImage(),
        assetGenerator.generateTestImage()
      ]);
      
      const form = await uploadHelper.createFormData(images.map(img => ({
        filepath: img.filepath,
        filename: img.filename,
        mimetype: img.mimetype,
        fieldname: 'files'
      })));
      
      const response = await request(app)
        .post('/upload')
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Too many files');
    });
  });
  
  describe('file type validation', () => {
    it('should accept allowed image types', async () => {
      app.post('/upload', uploadMiddleware.imageUpload(), (req, res) => {
        res.json({ file: req.file });
      });
      
      const testImage = await assetGenerator.generateTestImage({ format: 'png' });
      const form = await uploadHelper.createFormData({
        filepath: testImage.filepath,
        filename: testImage.filename,
        mimetype: testImage.mimetype,
        fieldname: 'image'
      });
      
      const response = await request(app)
        .post('/upload')
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(200);
    });
    
    it('should reject non-image files', async () => {
      app.post('/upload', uploadMiddleware.imageUpload(), (req, res) => {
        res.json({ file: req.file });
      });
      
      const testDocument = await assetGenerator.generateTestPDF();
      const form = await uploadHelper.createFormData({
        filepath: testDocument.filepath,
        filename: testDocument.filename,
        mimetype: testDocument.mimetype,
        fieldname: 'image'
      });
      
      const response = await request(app)
        .post('/upload')
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message', 'Invalid file type');
    });
  });
  
  describe('file size validation', () => {
    it('should reject oversized files', async () => {
      app.post('/upload', uploadMiddleware.single('file', { maxSize: 1024 * 1024 }), (req, res) => {
        res.json({ file: req.file });
      });
      
      const largeFile = await assetGenerator.generateLargeFile(2); // 2MB
      const form = await uploadHelper.createFormData({
        filepath: largeFile.filepath,
        filename: largeFile.filename,
        mimetype: 'application/octet-stream',
        fieldname: 'file'
      });
      
      const response = await request(app)
        .post('/upload')
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(413);
      expect(response.body).toHaveProperty('message', 'File too large');
    });
  });
  
  describe('filename sanitization', () => {
    it('should sanitize filenames', async () => {
      app.post('/upload', uploadMiddleware.single('file'), (req, res) => {
        res.json({ filename: req.file.filename });
      });
      
      const testImage = await assetGenerator.generateTestImage();
      const maliciousFilename = '../../../etc/passwd.jpg';
      
      const form = await uploadHelper.createFormData({
        filepath: testImage.filepath,
        filename: maliciousFilename,
        mimetype: testImage.mimetype,
        fieldname: 'file'
      });
      
      const response = await request(app)
        .post('/upload')
        .set('Content-Type', `multipart/form-data; boundary=${form._boundary}`)
        .send(form.getBuffer());
      
      expect(response.status).toBe(200);
      expect(response.body.filename).not.toContain('..');
      expect(response.body.filename).not.toContain('/');
    });
  });
});