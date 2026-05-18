// parking-management/backend/tests/fixtures/helpers/database.helper.js
const mongoose = require('mongoose');
const { MongoMemoryServer } = require('mongodb-memory-server');

class DatabaseHelper {
  constructor() {
    this.mongod = null;
    this.connection = null;
  }
  
  async connect() {
    this.mongod = await MongoMemoryServer.create();
    const uri = this.mongod.getUri();
    this.connection = await mongoose.connect(uri);
    return this.connection;
  }
  
  async disconnect() {
    await mongoose.disconnect();
    if (this.mongod) {
      await this.mongod.stop();
    }
  }
  
  async clearDatabase() {
    const collections = mongoose.connection.collections;
    for (const key in collections) {
      await collections[key].deleteMany();
    }
  }
  
  async seedDatabase(fixtures) {
    for (const [modelName, data] of Object.entries(fixtures)) {
      const Model = mongoose.model(modelName);
      if (Array.isArray(data)) {
        await Model.insertMany(data);
      } else {
        await Model.create(data);
      }
    }
  }
  
  async getCollectionSize(collectionName) {
    const Model = mongoose.model(collectionName);
    return await Model.countDocuments();
  }
  
  async getRandomDocument(collectionName) {
    const Model = mongoose.model(collectionName);
    const count = await Model.countDocuments();
    const random = Math.floor(Math.random() * count);
    return await Model.findOne().skip(random);
  }
}

module.exports = DatabaseHelper;