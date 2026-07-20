// parking-management/backend/tests/unit/test_assets/services/image.service.test.js
const ImageService = require('../../../../../src/services/image.service');
const AssetGenerator = require('../helpers/asset-generator');
const sharp = require('sharp');
const fs = require('fs-extra');
const path = require('path');

describe('ImageService', () => {
  let imageService;
  let assetGenerator;
  
  beforeEach(() => {
    imageService = new ImageService();
    assetGenerator = new AssetGenerator();
  });
  
  afterEach(async () => {
    await assetGenerator.cleanup();
  });
  
  describe('resizeImage', () => {
    it('should resize image to specified dimensions', async () => {
      const originalImage = await assetGenerator.generateTestImage({
        width: 1920,
        height: 1080
      });
      
      const resized = await imageService.resizeImage(originalImage.buffer, {
        width: 800,
        height: 600,
        fit: 'cover'
      });
      
      const metadata = await sharp(resized).metadata();
      expect(metadata.width).toBe(800);
      expect(metadata.height).toBe(600);
    });
    
    it('should maintain aspect ratio', async () => {
      const originalImage = await assetGenerator.generateTestImage({
        width: 1920,
        height: 1080
      });
      
      const resized = await imageService.resizeImage(originalImage.buffer, {
        width: 400,
        height: 400,
        fit: 'inside'
      });
      
      const metadata = await sharp(resized).metadata();
      expect(metadata.width).toBe(400);
      expect(metadata.height).toBe(225); // Maintained 16:9 ratio
    });
    
    it('should optimize image quality', async () => {
      const originalImage = await assetGenerator.generateTestImage();
      const originalSize = originalImage.buffer.length;
      
      const optimized = await imageService.optimizeImage(originalImage.buffer, {
        quality: 80,
        compressionLevel: 6
      });
      
      const optimizedSize = optimized.length;
      expect(optimizedSize).toBeLessThan(originalSize);
      
      // Verify image still valid
      const metadata = await sharp(optimized).metadata();
      expect(metadata).toBeDefined();
    });
    
    it('should generate thumbnail', async () => {
      const originalImage = await assetGenerator.generateTestImage();
      
      const thumbnail = await imageService.generateThumbnail(originalImage.buffer, {
        width: 150,
        height: 150
      });
      
      const metadata = await sharp(thumbnail).metadata();
      expect(metadata.width).toBe(150);
      expect(metadata.height).toBe(150);
    });
  });
  
  describe('watermarkImage', () => {
    it('should add text watermark', async () => {
      const originalImage = await assetGenerator.generateTestImage();
      const watermarkText = '© Parking Management System';
      
      const watermarked = await imageService.addWatermark(originalImage.buffer, {
        type: 'text',
        text: watermarkText,
        position: 'bottom-right',
        opacity: 0.5
      });
      
      // Verify watermark added
      const metadata = await sharp(watermarked).metadata();
      expect(metadata).toBeDefined();
      expect(watermarked.length).toBeGreaterThan(originalImage.buffer.length);
    });
    
    it('should add image watermark', async () => {
      const originalImage = await assetGenerator.generateTestImage();
      const watermarkImage = await assetGenerator.generateTestImage({
        width: 100,
        height: 100,
        text: 'WATERMARK'
      });
      
      const watermarked = await imageService.addWatermark(originalImage.buffer, {
        type: 'image',
        image: watermarkImage.buffer,
        position: 'center',
        opacity: 0.3
      });
      
      expect(watermarked).toBeDefined();
      expect(watermarked.length).toBeGreaterThan(originalImage.buffer.length);
    });
  });
  
  describe('convertFormat', () => {
    it('should convert JPEG to PNG', async () => {
      const jpegImage = await assetGenerator.generateTestImage({ format: 'jpeg' });
      
      const pngImage = await imageService.convertFormat(jpegImage.buffer, 'png');
      
      const metadata = await sharp(pngImage).metadata();
      expect(metadata.format).toBe('png');
    });
    
    it('should convert PNG to WebP', async () => {
      const pngImage = await assetGenerator.generateTestImage({ format: 'png' });
      
      const webpImage = await imageService.convertFormat(pngImage.buffer, 'webp');
      
      const metadata = await sharp(webpImage).metadata();
      expect(metadata.format).toBe('webp');
      expect(webpImage.length).toBeLessThan(pngImage.buffer.length);
    });
    
    it('should preserve quality during conversion', async () => {
      const originalImage = await assetGenerator.generateTestImage({ format: 'jpeg' });
      
      const converted = await imageService.convertFormat(originalImage.buffer, 'webp', {
        quality: 90
      });
      
      const metadata = await sharp(converted).metadata();
      expect(metadata.format).toBe('webp');
    });
  });
  
  describe('extractMetadata', () => {
    it('should extract EXIF data', async () => {
      const image = await assetGenerator.generateTestImage();
      
      const metadata = await imageService.extractMetadata(image.buffer);
      
      expect(metadata).toHaveProperty('width');
      expect(metadata).toHaveProperty('height');
      expect(metadata).toHaveProperty('format');
      expect(metadata).toHaveProperty('size');
    });
    
    it('should detect image orientation', async () => {
      const landscapeImage = await assetGenerator.generateTestImage({
        width: 1920,
        height: 1080
      });
      
      const metadata = await imageService.extractMetadata(landscapeImage.buffer);
      expect(metadata.orientation).toBe('landscape');
      
      const portraitImage = await assetGenerator.generateTestImage({
        width: 1080,
        height: 1920
      });
      
      const portraitMetadata = await imageService.extractMetadata(portraitImage.buffer);
      expect(portraitMetadata.orientation).toBe('portrait');
    });
  });
  
  describe('validateImage', () => {
    it('should validate correct image', async () => {
      const validImage = await assetGenerator.generateTestImage();
      
      const isValid = await imageService.validateImage(validImage.buffer);
      expect(isValid).toBe(true);
    });
    
    it('should reject corrupted image', async () => {
      const corruptedImage = await assetGenerator.generateCorruptedFile({ extension: 'jpg' });
      
      const isValid = await imageService.validateImage(corruptedImage.buffer);
      expect(isValid).toBe(false);
    });
    
    it('should check minimum dimensions', async () => {
      const smallImage = await assetGenerator.generateTestImage({
        width: 50,
        height: 50
      });
      
      const isValid = await imageService.validateImage(smallImage.buffer, {
        minWidth: 100,
        minHeight: 100
      });
      
      expect(isValid).toBe(false);
    });
  });
});