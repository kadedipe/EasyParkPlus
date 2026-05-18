// parking-management/backend/tests/unit/test_assets/helpers/upload-helper.js
const path = require('path');
const fs = require('fs-extra');
const FormData = require('form-data');

class UploadHelper {
  constructor() {
    this.uploadDir = global.testUploadDir;
  }
  
  // Create form data for file upload
  async createFormData(files, fields = {}) {
    const form = new FormData();
    
    // Add files
    if (Array.isArray(files)) {
      for (const file of files) {
        form.append(file.fieldname || 'files', fs.createReadStream(file.filepath), {
          filename: file.filename,
          contentType: file.mimetype
        });
      }
    } else {
      form.append(files.fieldname || 'file', fs.createReadStream(files.filepath), {
        filename: files.filename,
        contentType: files.mimetype
      });
    }
    
    // Add fields
    for (const [key, value] of Object.entries(fields)) {
      form.append(key, value);
    }
    
    return form;
  }
  
  // Validate uploaded file
  async validateUploadedFile(uploadedPath, originalFile) {
    const exists = await fs.pathExists(uploadedPath);
    if (!exists) return false;
    
    const stats = await fs.stat(uploadedPath);
    if (stats.size !== originalFile.size) return false;
    
    // For images, verify dimensions
    if (originalFile.mimetype && originalFile.mimetype.startsWith('image/')) {
      const sharp = require('sharp');
      const metadata = await sharp(uploadedPath).metadata();
      return metadata.width === originalFile.width && metadata.height === originalFile.height;
    }
    
    return true;
  }
  
  // Get file hash
  async getFileHash(filepath) {
    const crypto = require('crypto');
    const buffer = await fs.readFile(filepath);
    return crypto.createHash('md5').update(buffer).digest('hex');
  }
  
  // Create test upload directory structure
  async createUploadStructure(userId) {
    const userDir = path.join(this.uploadDir, userId.toString());
    const subDirs = ['avatars', 'vehicles', 'spots', 'documents', 'temp'];
    
    for (const dir of subDirs) {
      await fs.ensureDir(path.join(userDir, dir));
    }
    
    return userDir;
  }
  
  // Clean user uploads
  async cleanUserUploads(userId) {
    const userDir = path.join(this.uploadDir, userId.toString());
    if (await fs.pathExists(userDir)) {
      await fs.remove(userDir);
    }
  }
  
  // Simulate upload progress
  async simulateUpload(filepath, onProgress) {
    const stats = await fs.stat(filepath);
    const totalSize = stats.size;
    const chunkSize = 1024 * 1024; // 1MB chunks
    let uploadedSize = 0;
    
    const readStream = fs.createReadStream(filepath, { highWaterMark: chunkSize });
    
    for await (const chunk of readStream) {
      uploadedSize += chunk.length;
      const progress = (uploadedSize / totalSize) * 100;
      if (onProgress) onProgress(progress);
      await new Promise(resolve => setTimeout(resolve, 10)); // Simulate upload time
    }
    
    return { totalSize, uploadedSize };
  }
}

module.exports = UploadHelper;