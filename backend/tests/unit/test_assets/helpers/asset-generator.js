// parking-management/backend/tests/unit/test_assets/helpers/asset-generator.js
const fs = require('fs-extra');
const path = require('path');
const sharp = require('sharp');
const { PDFDocument } = require('pdf-lib');
const { createCanvas } = require('canvas');

class AssetGenerator {
  constructor() {
    this.uploadDir = global.testUploadDir;
    this.tempDir = global.testTempDir;
  }
  
  // Generate test image
  async generateTestImage(options = {}) {
    const {
      width = 800,
      height = 600,
      format = 'jpeg',
      color = '#ff0000',
      text = 'Test Image'
    } = options;
    
    const filename = `test_image_${Date.now()}.${format}`;
    const filepath = path.join(this.tempDir, filename);
    
    // Create canvas
    const canvas = createCanvas(width, height);
    const ctx = canvas.getContext('2d');
    
    // Fill background
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, width, height);
    
    // Add text
    ctx.fillStyle = '#ffffff';
    ctx.font = '30px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(text, width / 2, height / 2);
    
    // Save image
    const buffer = canvas.toBuffer(`image/${format}`);
    await fs.writeFile(filepath, buffer);
    
    return {
      filename,
      filepath,
      buffer,
      size: buffer.length,
      width,
      height,
      format,
      mimetype: `image/${format}`
    };
  }
  
  // Generate test PDF
  async generateTestPDF(options = {}) {
    const {
      title = 'Test Document',
      content = 'This is a test PDF document for upload testing.',
      pages = 1
    } = options;
    
    const pdfDoc = await PDFDocument.create();
    
    for (let i = 0; i < pages; i++) {
      const page = pdfDoc.addPage([600, 400]);
      const { width, height } = page.getSize();
      
      page.drawText(`${title} - Page ${i + 1}`, {
        x: 50,
        y: height - 50,
        size: 20
      });
      
      page.drawText(content, {
        x: 50,
        y: height - 100,
        size: 12
      });
      
      page.drawText(`Generated: ${new Date().toISOString()}`, {
        x: 50,
        y: 50,
        size: 10
      });
    }
    
    const pdfBytes = await pdfDoc.save();
    const filename = `test_document_${Date.now()}.pdf`;
    const filepath = path.join(this.tempDir, filename);
    
    await fs.writeFile(filepath, pdfBytes);
    
    return {
      filename,
      filepath,
      buffer: pdfBytes,
      size: pdfBytes.length,
      pages,
      mimetype: 'application/pdf'
    };
  }
  
  // Generate test document (Word, etc.)
  async generateTestDocument(options = {}) {
    const {
      type = 'docx',
      content = 'Test document content'
    } = options;
    
    // Simple text file for testing
    const filename = `test_document_${Date.now()}.${type}`;
    const filepath = path.join(this.tempDir, filename);
    
    await fs.writeFile(filepath, content);
    const buffer = await fs.readFile(filepath);
    
    return {
      filename,
      filepath,
      buffer,
      size: buffer.length,
      mimetype: type === 'docx' ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' : 'application/msword'
    };
  }
  
  // Generate test avatar
  async generateTestAvatar(userId, options = {}) {
    const {
      size = 200,
      backgroundColor = '#4CAF50',
      textColor = '#ffffff'
    } = options;
    
    const canvas = createCanvas(size, size);
    const ctx = canvas.getContext('2d');
    
    // Draw circle background
    ctx.fillStyle = backgroundColor;
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2);
    ctx.fill();
    
    // Draw initials
    ctx.fillStyle = textColor;
    ctx.font = `bold ${size / 2}px Arial`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const initials = userId.toString().substring(0, 2).toUpperCase();
    ctx.fillText(initials, size / 2, size / 2);
    
    const filename = `avatar_${userId}_${Date.now()}.png`;
    const filepath = path.join(this.tempDir, filename);
    const buffer = canvas.toBuffer('image/png');
    
    await fs.writeFile(filepath, buffer);
    
    return {
      filename,
      filepath,
      buffer,
      size: buffer.length,
      width: size,
      height: size,
      format: 'png',
      mimetype: 'image/png'
    };
  }
  
  // Generate test parking spot image
  async generateParkingSpotImage(spotId, options = {}) {
    const {
      width = 1200,
      height = 800,
      spotNumber = spotId.toString().substring(0, 4)
    } = options;
    
    const canvas = createCanvas(width, height);
    const ctx = canvas.getContext('2d');
    
    // Draw parking spot background
    ctx.fillStyle = '#e0e0e0';
    ctx.fillRect(0, 0, width, height);
    
    // Draw parking lines
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 10;
    
    // Draw spot boundary
    ctx.strokeRect(100, 100, width - 200, height - 200);
    
    // Draw spot number
    ctx.fillStyle = '#333333';
    ctx.font = `bold ${Math.min(width, height) / 10}px Arial`;
    ctx.textAlign = 'center';
    ctx.fillText(`SPOT ${spotNumber}`, width / 2, height / 2);
    
    // Add "P" symbol
    ctx.fillStyle = '#1976D2';
    ctx.font = `bold ${Math.min(width, height) / 5}px Arial`;
    ctx.fillText('P', width / 2, height / 3);
    
    const filename = `spot_${spotId}_${Date.now()}.jpg`;
    const filepath = path.join(this.tempDir, filename);
    const buffer = canvas.toBuffer('image/jpeg', { quality: 0.8 });
    
    await fs.writeFile(filepath, buffer);
    
    return {
      filename,
      filepath,
      buffer,
      size: buffer.length,
      width,
      height,
      format: 'jpeg',
      mimetype: 'image/jpeg'
    };
  }
  
  // Generate corrupted file
  async generateCorruptedFile(options = {}) {
    const {
      extension = 'jpg',
      size = 1024
    } = options;
    
    const filename = `corrupted_${Date.now()}.${extension}`;
    const filepath = path.join(this.tempDir, filename);
    
    // Write random data
    const buffer = Buffer.alloc(size);
    for (let i = 0; i < size; i++) {
      buffer[i] = Math.floor(Math.random() * 256);
    }
    
    await fs.writeFile(filepath, buffer);
    
    return {
      filename,
      filepath,
      buffer,
      size,
      mimetype: `image/${extension}`
    };
  }
  
  // Generate large file
  async generateLargeFile(sizeMB = 10) {
    const filename = `large_file_${Date.now()}.bin`;
    const filepath = path.join(this.tempDir, filename);
    const size = sizeMB * 1024 * 1024;
    
    // Create file with zeros (sparse file)
    const fd = await fs.open(filepath, 'w');
    await fs.ftruncate(fd, size);
    await fs.close(fd);
    
    const stats = await fs.stat(filepath);
    
    return {
      filename,
      filepath,
      size: stats.size,
      sizeMB: sizeMB
    };
  }
  
  // Clean up generated files
  async cleanup() {
    const files = await fs.readdir(this.tempDir);
    for (const file of files) {
      await fs.remove(path.join(this.tempDir, file));
    }
  }
}

module.exports = AssetGenerator;