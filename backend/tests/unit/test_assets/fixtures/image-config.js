// parking-management/backend/tests/unit/test_assets/fixtures/image-config.js
module.exports = {
  avatarConfig: {
    sizes: {
      thumbnail: { width: 150, height: 150 },
      small: { width: 300, height: 300 },
      medium: { width: 500, height: 500 },
      large: { width: 1000, height: 1000 }
    },
    allowedFormats: ['jpeg', 'png', 'webp'],
    maxSize: 5 * 1024 * 1024, // 5MB
    quality: 85
  },
  
  vehicleImageConfig: {
    sizes: {
      thumbnail: { width: 200, height: 150 },
      medium: { width: 800, height: 600 },
      large: { width: 1600, height: 1200 }
    },
    allowedFormats: ['jpeg', 'png'],
    maxSize: 10 * 1024 * 1024, // 10MB
    quality: 80
  },
  
  parkingSpotImageConfig: {
    sizes: {
      thumbnail: { width: 300, height: 200 },
      medium: { width: 1200, height: 800 },
      large: { width: 2400, height: 1600 }
    },
    allowedFormats: ['jpeg', 'webp'],
    maxSize: 15 * 1024 * 1024, // 15MB
    quality: 75
  },
  
  documentConfig: {
    allowedTypes: ['pdf', 'doc', 'docx'],
    maxSize: 20 * 1024 * 1024, // 20MB
    supportedLanguages: ['en', 'es', 'fr']
  }
};