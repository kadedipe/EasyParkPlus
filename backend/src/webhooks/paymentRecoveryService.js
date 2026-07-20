// parking-management/backend/src/webhooks/paymentRecoveryService.js
import { PrismaClient } from '@prisma/client';
import { notificationService } from '../services/notificationService.js';
import { paymentService } from '../services/paymentService.js';
import { logger } from '../utils/logger.js';

const prisma = new PrismaClient();

class PaymentRecoveryService {
  constructor() {
    this.maxRetries = 3;
    this.retryDelays = [60, 300, 900]; // seconds
    this.isRecoveryRunning = false;
  }

  /**
   * Recover a failed payment
   */
  async recoverFailedPayment(payment) {
    try {
      logger.info(`Starting recovery for payment: ${payment.id}`);
      
      const recoveryStrategy = await this.determineRecoveryStrategy(payment);
      
      switch (recoveryStrategy) {
        case 'retry':
          return await this.retryPayment(payment);
        case 'alternative_method':
          return await this.tryAlternativePayment(payment);
        case 'manual_review':
          return await this.initiateManualReview(payment);
        case 'notify_user':
          return await this.notifyUserFailure(payment);
        default:
          logger.warn(`No recovery strategy for payment ${payment.id}`);
          return {
            recovered: false,
            strategy: 'none',
            message: 'No recovery strategy available',
          };
      }

    } catch (error) {
      logger.error(`Payment recovery failed for ${payment.id}:`, error);
      throw error;
    }
  }

  /**
   * Determine recovery strategy based on failure type
   */
  async determineRecoveryStrategy(payment) {
    const failureType = await this.analyzeFailure(payment);
    
    const strategies = {
      insufficient_funds: 'retry',
      card_declined: 'retry',
      expired_card: 'alternative_method',
      invalid_cvv: 'alternative_method',
      fraud_suspected: 'manual_review',
      gateway_error: 'retry',
      timeout: 'retry',
      unknown: 'notify_user',
    };

    return strategies[failureType] || 'notify_user';
  }

  /**
   * Analyze payment failure
   */
  async analyzeFailure(payment) {
    try {
      // Get failure details from Stripe
      const failureDetails = await paymentService.getPaymentFailureDetails(
        payment.stripeIntentId
      );

      const failureCode = failureDetails?.last_payment_error?.code;
      
      const failureTypes = {
        'insufficient_funds': 'insufficient_funds',
        'card_declined': 'card_declined',
        'expired_card': 'expired_card',
        'incorrect_cvc': 'invalid_cvv',
        'incorrect_zip': 'invalid_zip',
        'fraudulent': 'fraud_suspected',
        'amount_too_large': 'amount_too_large',
        'balance_insufficient': 'insufficient_funds',
        'processing_error': 'gateway_error',
        'timeout': 'timeout',
      };

      return failureTypes[failureCode] || 'unknown';

    } catch (error) {
      logger.error('Failure analysis error:', error);
      return 'unknown';
    }
  }

  /**
   * Retry payment with exponential backoff
   */
  async retryPayment(payment, attempt = 0) {
    try {
      logger.info(`Retrying payment ${payment.id}, attempt ${attempt + 1}`);
      
      // Check if max retries exceeded
      if (attempt >= this.maxRetries) {
        logger.warn(`Max retries exceeded for payment ${payment.id}`);
        return {
          recovered: false,
          reason: 'max_retries_exceeded',
          attempts: attempt,
        };
      }

      // Calculate delay with exponential backoff
      const delay = this.retryDelays[attempt] || this.retryDelays[this.retryDelays.length - 1];
      
      // Wait before retry
      await this.sleep(delay * 1000);

      // Attempt payment again
      const result = await paymentService.retryPayment(payment);

      if (result.success) {
        logger.info(`Payment ${payment.id} recovered on attempt ${attempt + 1}`);
        
        // Update payment status
        await prisma.payment.update({
          where: { id: payment.id },
          data: {
            status: 'COMPLETED',
            updatedAt: new Date(),
          },
        });

        // Update booking status
        await prisma.booking.update({
          where: { id: payment.bookingId },
          data: {
            status: 'CONFIRMED',
            updatedAt: new Date(),
          },
        });

        // Send success notification
        await notificationService.sendPaymentRecoverySuccess(payment);

        return {
          recovered: true,
          attempts: attempt + 1,
          result: result,
        };
      }

      // Retry with backoff
      return await this.retryPayment(payment, attempt + 1);

    } catch (error) {
      logger.error(`Payment retry failed for ${payment.id}:`, error);
      
      // Schedule retry
      return await this.retryPayment(payment, attempt + 1);
    }
  }

  /**
   * Try alternative payment method
   */
  async tryAlternativePayment(payment) {
    try {
      logger.info(`Trying alternative payment for ${payment.id}`);
      
      // Get user's saved payment methods
      const userPaymentMethods = await prisma.paymentMethod.findMany({
        where: {
          userId: payment.booking.userId,
          isDefault: false,
        },
      });

      if (userPaymentMethods.length === 0) {
        return await this.notifyUserFailure(payment);
      }

      // Try each alternative method
      for (const method of userPaymentMethods) {
        try {
          const result = await paymentService.processSavedPayment(
            payment.stripeIntentId,
            method.paymentMethodId
          );

          if (result.success) {
            // Update payment with new method
            await prisma.payment.update({
              where: { id: payment.id },
              data: {
                paymentMethod: method.type,
                updatedAt: new Date(),
              },
            });

            logger.info(`Payment ${payment.id} recovered with alternative method`);
            
            return {
              recovered: true,
              method: method.type,
              result: result,
            };
          }
        } catch (error) {
          logger.error(`Alternative payment method failed: ${method.id}`, error);
          continue;
        }
      }

      // No alternative method worked
      return await this.notifyUserFailure(payment);

    } catch (error) {
      logger.error(`Alternative payment error for ${payment.id}:`, error);
      return await this.notifyUserFailure(payment);
    }
  }

  /**
   * Initiate manual review
   */
  async initiateManualReview(payment) {
    try {
      logger.info(`Initiating manual review for payment ${payment.id}`);
      
      // Update payment status
      await prisma.payment.update({
        where: { id: payment.id },
        data: {
          status: 'PROCESSING',
          updatedAt: new Date(),
        },
      });

      // Notify admin
      await this.notifyAdmin(payment);

      // Notify user
      await notificationService.sendManualReviewNotification(payment);

      // Create review ticket
      const reviewTicket = await prisma.reviewTicket.create({
        data: {
          paymentId: payment.id,
          status: 'PENDING',
          priority: 'HIGH',
          createdAt: new Date(),
        },
      });

      return {
        recovered: false,
        strategy: 'manual_review',
        ticketId: reviewTicket.id,
        message: 'Payment requires manual review',
      };

    } catch (error) {
      logger.error(`Manual review initiation error: ${error}`);
      return await this.notifyUserFailure(payment);
    }
  }

  /**
   * Notify user of payment failure
   */
  async notifyUserFailure(payment) {
    try {
      logger.info(`Notifying user of payment failure: ${payment.id}`);
      
      // Update payment status
      await prisma.payment.update({
        where: { id: payment.id },
        data: {
          status: 'FAILED',
          updatedAt: new Date(),
        },
      });

      // Send failure notification
      await notificationService.sendPaymentFailureNotification(payment);

      // Offer support options
      await this.offerSupportOptions(payment);

      return {
        recovered: false,
        strategy: 'notify_user',
        message: 'User notified of payment failure',
      };

    } catch (error) {
      logger.error(`User notification error: ${error}`);
      throw error;
    }
  }

  /**
   * Offer support options to user
   */
  async offerSupportOptions(payment) {
    try {
      const options = [
        {
          type: 'retry',
          label: 'Try Again',
          action: 'retry_payment',
        },
        {
          type: 'alternative',
          label: 'Use Different Card',
          action: 'change_payment_method',
        },
        {
          type: 'support',
          label: 'Contact Support',
          action: 'contact_support',
        },
      ];

      await notificationService.sendPaymentRecoveryOptions(
        payment,
        options
      );

    } catch (error) {
      logger.error('Support options error:', error);
    }
  }

  /**
   * Notify admin of payment issue
   */
  async notifyAdmin(payment) {
    try {
      // Create admin notification
      await prisma.adminNotification.create({
        data: {
          type: 'PAYMENT_ISSUE',
          priority: 'HIGH',
          title: 'Payment Requires Review',
          message: `Payment ${payment.id} requires manual review`,
          data: {
            paymentId: payment.id,
            bookingId: payment.bookingId,
            amount: payment.amount,
            failureReason: payment.failureReason,
          },
          createdAt: new Date(),
        },
      });

      logger.info(`Admin notified of payment issue: ${payment.id}`);
    } catch (error) {
      logger.error('Admin notification error:', error);
    }
  }

  /**
   * Sleep utility
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Process all failed payments
   */
  async processFailedPayments() {
    if (this.isRecoveryRunning) {
      logger.info('Recovery already in progress');
      return;
    }

    this.isRecoveryRunning = true;
    
    try {
      logger.info('Starting payment recovery batch process');
      
      // Get failed payments
      const failedPayments = await prisma.payment.findMany({
        where: {
          status: 'FAILED',
          createdAt: {
            gte: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // Last 7 days
          },
        },
        include: {
          booking: {
            include: {
              user: true,
            },
          },
        },
      });

      logger.info(`Found ${failedPayments.length} failed payments to process`);

      let recovered = 0;
      let failed = 0;

      for (const payment of failedPayments) {
        try {
          const result = await this.recoverFailedPayment(payment);
          
          if (result.recovered) {
            recovered++;
          } else {
            failed++;
          }
        } catch (error) {
          logger.error(`Failed to process payment ${payment.id}:`, error);
          failed++;
        }
      }

      logger.info(`Payment recovery completed: ${recovered} recovered, ${failed} failed`);

      return {
        total: failedPayments.length,
        recovered,
        failed,
      };

    } catch (error) {
      logger.error('Payment recovery batch process error:', error);
      throw error;
    } finally {
      this.isRecoveryRunning = false;
    }
  }
}

export const paymentRecoveryService = new PaymentRecoveryService();

// Schedule automated recovery
if (process.env.NODE_ENV === 'production') {
  cron.schedule('*/30 * * * *', async () => {
    try {
      await paymentRecoveryService.processFailedPayments();
    } catch (error) {
      logger.error('Scheduled payment recovery failed:', error);
    }
  });
}

export default paymentRecoveryService;