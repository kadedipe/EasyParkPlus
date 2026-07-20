// parking-management/backend/src/config/database.js
import { PrismaClient } from '@prisma/client';
import { logger } from '../utils/logger.js';

class DatabaseManager {
  constructor() {
    this.primaryClient = null;
    this.replicaClients = [];
    this.currentReplicaIndex = 0;
    this.isReplicaEnabled = process.env.ENABLE_READ_REPLICAS === 'true';
    
    this.initializeClients();
  }

  /**
   * Initialize database clients
   */
  initializeClients() {
    // Primary database client
    this.primaryClient = new PrismaClient({
      datasources: {
        db: {
          url: process.env.DATABASE_URL,
        },
      },
      log: process.env.NODE_ENV === 'development' ? ['query', 'info', 'warn', 'error'] : ['error'],
    });

    // Read replica clients
    if (this.isReplicaEnabled) {
      const replicaUrls = this.getReplicaUrls();
      this.replicaClients = replicaUrls.map((url, index) => {
        return new PrismaClient({
          datasources: {
            db: { url },
          },
          log: ['error'],
        });
      });
      
      logger.info(`Initialized ${this.replicaClients.length} read replicas`);
    }

    // Handle connection errors
    this.primaryClient.$on('error', (e) => {
      logger.error('Primary database error:', e);
    });

    this.replicaClients.forEach((client, index) => {
      client.$on('error', (e) => {
        logger.error(`Replica ${index} error:`, e);
      });
    });
  }

  /**
   * Get replica URLs from environment
   */
  getReplicaUrls() {
    const replicaUrls = [];
    let index = 1;
    
    while (process.env[`DATABASE_REPLICA_URL_${index}`]) {
      replicaUrls.push(process.env[`DATABASE_REPLICA_URL_${index}`]);
      index++;
    }
    
    // Fallback to primary if no replicas configured
    if (replicaUrls.length === 0) {
      replicaUrls.push(process.env.DATABASE_URL);
    }
    
    return replicaUrls;
  }

  /**
   * Get client for read operations (round-robin)
   */
  getReadClient() {
    if (!this.isReplicaEnabled || this.replicaClients.length === 0) {
      return this.primaryClient;
    }

    // Round-robin load balancing
    const client = this.replicaClients[this.currentReplicaIndex];
    this.currentReplicaIndex = (this.currentReplicaIndex + 1) % this.replicaClients.length;
    
    return client;
  }

  /**
   * Get client for write operations
   */
  getWriteClient() {
    return this.primaryClient;
  }

  /**
   * Execute query with read/write separation
   */
  async executeQuery(options) {
    const { query, params, type = 'read', model, operation } = options;
    
    try {
      let client;
      
      if (type === 'write') {
        client = this.getWriteClient();
      } else {
        client = this.getReadClient();
      }
      
      // Execute the query
      const result = await this.executeWithClient(client, query, params);
      
      // Log query performance
      if (process.env.NODE_ENV === 'development') {
        logger.debug(`Query executed on ${type} database:`, {
          model,
          operation,
          type,
        });
      }
      
      return result;
      
    } catch (error) {
      logger.error(`Database query failed (${type}):`, error);
      throw error;
    }
  }

  /**
   * Execute query with specific client
   */
  async executeWithClient(client, query, params) {
    // Handle Prisma queries
    if (typeof query === 'function') {
      return await query(client);
    }
    
    // Handle raw SQL queries
    return await client.$queryRaw(query, ...params);
  }

  /**
   * Get database health status
   */
  async getHealth() {
    const health = {
      primary: { status: 'healthy', latency: 0 },
      replicas: [],
    };

    try {
      // Check primary
      const start = Date.now();
      await this.primaryClient.$queryRaw`SELECT 1`;
      health.primary.latency = Date.now() - start;
    } catch (error) {
      health.primary.status = 'unhealthy';
      health.primary.error = error.message;
    }

    // Check replicas
    for (let i = 0; i < this.replicaClients.length; i++) {
      const replica = { status: 'healthy', latency: 0 };
      try {
        const start = Date.now();
        await this.replicaClients[i].$queryRaw`SELECT 1`;
        replica.latency = Date.now() - start;
      } catch (error) {
        replica.status = 'unhealthy';
        replica.error = error.message;
      }
      health.replicas.push(replica);
    }

    return health;
  }

  /**
   * Get database statistics
   */
  async getStats() {
    try {
      const stats = await this.primaryClient.$queryRaw`
        SELECT 
          (SELECT count(*) FROM users) as users,
          (SELECT count(*) FROM parking_spots) as parking_spots,
          (SELECT count(*) FROM bookings) as bookings,
          (SELECT count(*) FROM payments) as payments,
          (SELECT count(*) FROM notifications) as notifications
      `;
      
      return stats[0];
    } catch (error) {
      logger.error('Failed to get database stats:', error);
      return null;
    }
  }

  /**
   * Disconnect all clients
   */
  async disconnect() {
    await this.primaryClient.$disconnect();
    await Promise.all(this.replicaClients.map(client => client.$disconnect()));
    logger.info('All database clients disconnected');
  }
}

// Create singleton instance
export const dbManager = new DatabaseManager();

// Graceful shutdown
process.on('SIGTERM', async () => {
  await dbManager.disconnect();
});

export default dbManager;