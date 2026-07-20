// parking-management/backend/src/webhooks/webhookMonitor.js
import { logger } from '../utils/logger.js';
import { webhookQueueService } from './webhookQueue.js';
import { webhookRetryService } from './webhookRetry.js';

class WebhookMonitor {
  constructor() {
    this.alerts = [];
    this.thresholds = {
      successRateMin: 95, // 95%
      failedCountMax: 10, // Max failed in last hour
      queueSizeMax: 100, // Max queue size
      retryAttemptsMax: 3, // Max retry attempts
    };
  }

  /**
   * Check webhook health
   */
  async checkHealth() {
    try {
      const stats = await webhookRetryService.getWebhookStats();
      const issues = [];

      // Check success rate
      if (stats.successRate < this.thresholds.successRateMin) {
        issues.push({
          severity: 'warning',
          message: `Success rate (${stats.successRate.toFixed(2)}%) below threshold (${this.thresholds.successRateMin}%)`,
          metric: 'successRate',
          value: stats.successRate,
          threshold: this.thresholds.successRateMin,
        });
      }

      // Check failed count
      if (stats.failed > this.thresholds.failedCountMax) {
        issues.push({
          severity: 'critical',
          message: `${stats.failed} failed webhooks in last hour`,
          metric: 'failedCount',
          value: stats.failed,
          threshold: this.thresholds.failedCountMax,
        });
      }

      // Check queue size
      if (stats.queue.total > this.thresholds.queueSizeMax) {
        issues.push({
          severity: 'warning',
          message: `Queue size (${stats.queue.total}) above threshold (${this.thresholds.queueSizeMax})`,
          metric: 'queueSize',
          value: stats.queue.total,
          threshold: this.thresholds.queueSizeMax,
        });
      }

      // Get retry distribution
      const retryMetrics = await webhookRetryService.getRetryMetrics();
      const highRetries = retryMetrics.retryDistribution.filter(r => r.attempts > this.thresholds.retryAttemptsMax);
      
      if (highRetries.length > 0) {
        issues.push({
          severity: 'warning',
          message: `${highRetries.reduce((acc, r) => acc + r.count, 0)} webhooks with high retry attempts`,
          metric: 'highRetries',
          value: highRetries,
          threshold: this.thresholds.retryAttemptsMax,
        });
      }

      // Log issues
      issues.forEach(issue => {
        const logFn = issue.severity === 'critical' ? logger.error : logger.warn;
        logFn(`Webhook health issue: ${issue.message}`);
      });

      return {
        healthy: issues.length === 0,
        issues,
        stats,
        timestamp: new Date().toISOString(),
      };

    } catch (error) {
      logger.error('Health check failed:', error);
      return {
        healthy: false,
        issues: [{
          severity: 'critical',
          message: 'Health check failed',
          error: error.message,
        }],
        timestamp: new Date().toISOString(),
      };
    }
  }

  /**
   * Get webhook dashboard data
   */
  async getDashboardData() {
    try {
      const [
        stats,
        retryMetrics,
        queueStats,
        recentWebhooks,
        topFailed,
      ] = await Promise.all([
        webhookRetryService.getWebhookStats(),
        webhookRetryService.getRetryMetrics(),
        webhookQueueService.getQueueStats(),
        WebhookEventModel.getRecent(50),
        WebhookEventModel.getTopFailed(10),
      ]);

      return {
        stats,
        retryMetrics,
        queue: queueStats,
        recent: recentWebhooks,
        topFailed,
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      logger.error('Failed to get dashboard data:', error);
      throw error;
    }
  }

  /**
   * Send alert for critical issues
   */
  async sendAlert(alert) {
    // Log alert
    logger.warn('Webhook alert:', alert);

    // Store alert
    this.alerts.push({
      ...alert,
      timestamp: new Date().toISOString(),
      resolved: false,
    });

    // Could integrate with Slack, Email, PagerDuty, etc.
    if (alert.severity === 'critical') {
      // Send critical alert
      await this.sendCriticalAlert(alert);
    }

    return alert;
  }

  /**
   * Send critical alert (Slack, Email, etc.)
   */
  async sendCriticalAlert(alert) {
    // Implement alert sending logic here
    // This could be Slack webhook, Email, SMS, etc.
    logger.info(`Critical alert: ${alert.message}`);
  }

  /**
   * Resolve an alert
   */
  resolveAlert(alertId) {
    const alert = this.alerts.find(a => a.id === alertId);
    if (alert) {
      alert.resolved = true;
      alert.resolvedAt = new Date().toISOString();
      logger.info(`Alert ${alertId} resolved`);
    }
  }

  /**
   * Get alert history
   */
  getAlertHistory(options = {}) {
    const { resolved, severity, limit = 100 } = options;
    
    let alerts = this.alerts;
    
    if (resolved !== undefined) {
      alerts = alerts.filter(a => a.resolved === resolved);
    }
    
    if (severity) {
      alerts = alerts.filter(a => a.severity === severity);
    }
    
    return alerts.slice(-limit);
  }
}

export const webhookMonitor = new WebhookMonitor();

// Run health check every 5 minutes
setInterval(async () => {
  const health = await webhookMonitor.checkHealth();
  if (!health.healthy) {
    logger.warn('Webhook health issues detected:', health.issues);
  }
}, 300000);

export default webhookMonitor;