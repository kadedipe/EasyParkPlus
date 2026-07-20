// parking-management/backend/src/webhooks/idempotencyService.js
import { PrismaClient } from '@prisma/client';
import { createClient } from 'redis';
import { logger } from '../utils/logger.js';

const prisma = new PrismaClient();

class IdempotencyService {
  constructor() {
    this.redisClient = createClient({
      url: process.env.REDIS_URL || 'redis://localhost:6379',
    });
    this.redisClient.connect().catch(err => {
      logger.error('Redis connection error:', err);
    });
  }

  /**
   * Check if request is idempotent
   */
  async checkIdempotency(idempotentKey, provider) {
    try {
      // Check Redis first (fast)
      const cached = await this.redisClient.get(`idempotency:${provider}:${idempotentKey}`);
      
      if (cached) {
        const data = JSON.parse(cached);
        logger.info(`Idempotency cache hit: ${idempotentKey}`);
        return data;
      }

      // Check database
      const record = await prisma.idempotencyRecord.findUnique({
        where: {
          idempotentKey_provider: {
            idempotentKey,
            provider,
          },
        },
      });

      if (record) {
        // Cache the result for future checks
        await this.cacheIdempotentRecord(idempotentKey, provider, record);
        return record;
      }

      return null;

    } catch (error) {
      logger.error('Idempotency check error:', error);
      // Fallback to database only
      return await this.checkIdempotencyDatabase(idempotentKey, provider);
    }
  }

  /**
   * Check idempotency in database only
   */
  async checkIdempotencyDatabase(idempotentKey, provider) {
    try {
      return await prisma.idempotencyRecord.findUnique({
        where: {
          idempotentKey_provider: {
            idempotentKey,
            provider,
          },
        },
      });
    } catch (error) {
      logger.error('Database idempotency check error:', error);
      return null;
    }
  }

  /**
   * Mark request as idempotent
   */
  async markIdempotent(idempotentKey, provider, data) {
    try {
      // Store in database
      const record = await prisma.idempotencyRecord.create({
        data: {
          idempotentKey,
          provider,
          data: data || {},
          status: 'COMPLETED',
          processedAt: new Date(),
        },
      });

      // Cache for fast lookups
      await this.cacheIdempotentRecord(idempotentKey, provider, record);

      // Set expiration based on TTL
      const ttl = parseInt(process.env.IDEMPOTENCY_TTL) || 86400; // 24 hours default
      await this.redisClient.expire(
        `idempotency:${provider}:${idempotentKey}`,
        ttl
      );

      return record;

    } catch (error) {
      logger.error('Mark idempotent error:', error);
      throw error;
    }
  }

  /**
   * Cache idempotent record
   */
  async cacheIdempotentRecord(idempotentKey, provider, record) {
    try {
      const ttl = parseInt(process.env.IDEMPOTENCY_TTL) || 86400;
      await this.redisClient.set(
        `idempotency:${provider}:${idempotentKey}`,
        JSON.stringify(record),
        {
          EX: ttl,
        }
      );
    } catch (error) {
      logger.error('Cache idempotent record error:', error);
    }
  }

  /**
   * Check if idempotent key is expired
   */
  async isExpired(idempotentKey, provider) {
    try {
      const record = await prisma.idempotencyRecord.findUnique({
        where: {
          idempotentKey_provider: {
            idempotentKey,
            provider,
          },
        },
      });

      if (!record) return true;

      const ttl = parseInt(process.env.IDEMPOTENCY_TTL) || 86400;
      const age = (Date.now() - record.createdAt.getTime()) / 1000;
      
      return age > ttl;

    } catch (error) {
      logger.error('Idempotency expiration check error:', error);
      return true;
    }
  }

  /**
   * Clean up expired idempotency records
   */
  async cleanupExpired() {
    try {
      const ttl = parseInt(process.env.IDEMPOTENCY_TTL) || 86400;
      const cutoff = new Date(Date.now() - ttl * 1000);

      const deleted = await prisma.idempotencyRecord.deleteMany({
        where: {
          createdAt: {
            lt: cutoff,
          },
        },
      });

      logger.info(`Cleaned up ${deleted.count} expired idempotency records`);
      
      return deleted;

    } catch (error) {
      logger.error('Idempotency cleanup error:', error);
      throw error;
    }
  }

  /**
   * Get idempotency statistics
   */
  async getStats() {
    try {
      const [total, completed, failed] = await Promise.all([
        prisma.idempotencyRecord.count(),
        prisma.idempotencyRecord.count({ where: { status: 'COMPLETED' } }),
        prisma.idempotencyRecord.count({ where: { status: 'FAILED' } }),
      ]);

      return {
        total,
        completed,
        failed,
        successRate: total > 0 ? (completed / total) * 100 : 0,
      };

    } catch (error) {
      logger.error('Idempotency stats error:', error);
      return null;
    }
  }
}

// Database migration for idempotency
const createIdempotencyTable = `
  CREATE TABLE IF NOT EXISTS idempotency_records (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotent_key VARCHAR(255) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    data JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(idempotent_key, provider)
  );

  CREATE INDEX idx_idempotency_records_key ON idempotency_records(idempotent_key);
  CREATE INDEX idx_idempotency_records_provider ON idempotency_records(provider);
  CREATE INDEX idx_idempotency_records_status ON idempotency_records(status);
  CREATE INDEX idx_idempotency_records_created_at ON idempotency_records(created_at);
`;

export const idempotencyService = new IdempotencyService();
export default idempotencyService;