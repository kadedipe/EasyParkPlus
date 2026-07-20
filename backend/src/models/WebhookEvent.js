// parking-management/backend/src/models/WebhookEvent.js
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

export class WebhookEventModel {
  /**
   * Create a webhook event record
   */
  static async create(data) {
    return prisma.webhookEvent.create({
      data: {
        source: data.source,
        eventId: data.eventId,
        eventType: data.eventType,
        payload: data.payload,
        status: 'PENDING',
        retryCount: 0,
      },
    });
  }

  /**
   * Get pending webhook events
   */
  static async getPendingEvents(limit = 100) {
    return prisma.webhookEvent.findMany({
      where: {
        status: {
          in: ['PENDING', 'RETRYING'],
        },
        OR: [
          { nextRetryAt: null },
          { nextRetryAt: { lte: new Date() } },
        ],
      },
      orderBy: {
        createdAt: 'asc',
      },
      take: limit,
    });
  }

  /**
   * Update webhook event status
   */
  static async updateStatus(id, status, error = null) {
    return prisma.webhookEvent.update({
      where: { id },
      data: {
        status,
        processedAt: status === 'COMPLETED' ? new Date() : undefined,
        error,
        updatedAt: new Date(),
      },
    });
  }

  /**
   * Mark for retry
   */
  static async markForRetry(id, nextRetryAt) {
    return prisma.webhookEvent.update({
      where: { id },
      data: {
        status: 'RETRYING',
        retryCount: { increment: 1 },
        nextRetryAt,
        updatedAt: new Date(),
      },
    });
  }

  /**
   * Get webhook event by Stripe event ID
   */
  static async findByEventId(eventId) {
    return prisma.webhookEvent.findUnique({
      where: { eventId },
    });
  }

  /**
   * Get webhook statistics
   */
  static async getStats() {
    const [total, completed, failed, pending] = await Promise.all([
      prisma.webhookEvent.count(),
      prisma.webhookEvent.count({ where: { status: 'COMPLETED' } }),
      prisma.webhookEvent.count({ where: { status: 'FAILED' } }),
      prisma.webhookEvent.count({
        where: {
          status: {
            in: ['PENDING', 'RETRYING', 'PROCESSING'],
          },
        },
      }),
    ]);

    return {
      total,
      completed,
      failed,
      pending,
      successRate: total > 0 ? (completed / total) * 100 : 0,
    };
  }
}

export default WebhookEventModel;