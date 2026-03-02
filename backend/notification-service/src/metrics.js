const prometheus = require('prom-client');
const responseTime = require('response-time');

// Create a Registry which registers the metrics
const register = new prometheus.Registry();

// Add default metrics
prometheus.collectDefaultMetrics({ register });

// Custom metrics for Notification Service
const metrics = {
  // Notification metrics
  notificationsSentTotal: new prometheus.Counter({
    name: 'notification_service_notifications_sent_total',
    help: 'Total number of notifications sent',
    labelNames: ['channel', 'provider', 'notification_type', 'status', 'priority'],
    registers: [register]
  }),

  deliveryLatencySeconds: new prometheus.Histogram({
    name: 'notification_service_delivery_latency_seconds',
    help: 'Notification delivery latency in seconds',
    labelNames: ['channel', 'provider', 'notification_type'],
    buckets: [0.1, 0.5, 1, 2, 5, 10, 30, 60],
    registers: [register]
  }),

  // Channel-specific metrics
  smsSentTotal: new prometheus.Counter({
    name: 'notification_service_sms_sent_total',
    help: 'Total number of SMS notifications sent',
    labelNames: ['provider', 'status', 'country_code'],
    registers: [register]
  }),

  emailSentTotal: new prometheus.Counter({
    name: 'notification_service_email_sent_total',
    help: 'Total number of email notifications sent',
    labelNames: ['provider', 'status', 'template_id'],
    registers: [register]
  }),

  pushSentTotal: new prometheus.Counter({
    name: 'notification_service_push_sent_total',
    help: 'Total number of push notifications sent',
    labelNames: ['provider', 'status', 'platform'],
    registers: [register]
  }),

  // Provider metrics
  providerCallsTotal: new prometheus.Counter({
    name: 'notification_service_provider_calls_total',
    help: 'Total number of provider API calls',
    labelNames: ['provider', 'endpoint', 'status'],
    registers: [register]
  }),

  providerResponseTimeSeconds: new prometheus.Histogram({
    name: 'notification_service_provider_response_time_seconds',
    help: 'Provider API response time in seconds',
    labelNames: ['provider', 'endpoint'],
    buckets: [0.01, 0.05, 0.1, 0.5, 1, 2, 5],
    registers: [register]
  }),

  providerErrorsTotal: new prometheus.Counter({
    name: 'notification_service_provider_errors_total',
    help: 'Total number of provider errors',
    labelNames: ['provider', 'error_type'],
    registers: [register]
  }),

  // Queue metrics
  queueSize: new prometheus.Gauge({
    name: 'notification_service_queue_size',
    help: 'Current size of notification queue',
    registers: [register]
  }),

  activeWorkers: new prometheus.Gauge({
    name: 'notification_service_active_workers',
    help: 'Number of active notification processing workers',
    registers: [register]
  }),

  // Retry and DLQ metrics
  retriesTotal: new prometheus.Counter({
    name: 'notification_service_retries_total',
    help: 'Total number of notification retries',
    labelNames: ['channel', 'provider', 'retry_count'],
    registers: [register]
  }),

  dlqMessagesTotal: new prometheus.Counter({
    name: 'notification_service_dlq_messages_total',
    help: 'Total number of messages sent to dead letter queue',
    labelNames: ['channel', 'error_type'],
    registers: [register]
  }),

  // Error metrics
  errorsTotal: new prometheus.Counter({
    name: 'notification_service_errors_total',
    help: 'Total number of notification errors',
    labelNames: ['error_type', 'channel', 'provider'],
    registers: [register]
  }),

  // Template metrics
  templatesRenderedTotal: new prometheus.Counter({
    name: 'notification_service_templates_rendered_total',
    help: 'Total number of templates rendered',
    labelNames: ['template_id', 'channel'],
    registers: [register]
  }),

  templateErrorsTotal: new prometheus.Counter({
    name: 'notification_service_template_errors_total',
    help: 'Total number of template rendering errors',
    labelNames: ['template_id', 'error_type'],
    registers: [register]
  }),

  // Rate limiting metrics
  rateLimitHitsTotal: new prometheus.Counter({
    name: 'notification_service_rate_limit_hits_total',
    help: 'Total number of rate limit hits',
    labelNames: ['provider', 'channel'],
    registers: [register]
  }),

  // Cost metrics (for billing)
  smsCostTotal: new prometheus.Counter({
    name: 'notification_service_sms_cost_total',
    help: 'Total SMS cost in USD',
    labelNames: ['provider', 'country_code'],
    registers: [register]
  }),

  // Delivery confirmation metrics
  deliveryConfirmationsTotal: new prometheus.Counter({
    name: 'notification_service_delivery_confirmations_total',
    help: 'Total number of delivery confirmations received',
    labelNames: ['channel', 'provider', 'status'],
    registers: [register]
  }),

  // User engagement metrics
  notificationsOpenedTotal: new prometheus.Counter({
    name: 'notification_service_notifications_opened_total',
    help: 'Total number of notifications opened',
    labelNames: ['channel', 'notification_type'],
    registers: [register]
  }),

  notificationsClickedTotal: new prometheus.Counter({
    name: 'notification_service_notifications_clicked_total',
    help: 'Total number of notification links clicked',
    labelNames: ['channel', 'notification_type'],
    registers: [register]
  })
};

// Helper function to determine channel
function getChannel(notification) {
  if (notification.to.phone) return 'sms';
  if (notification.to.email) return 'email';
  if (notification.to.device_token) return 'push';
  if (notification.to.webhook_url) return 'webhook';
  return 'unknown';
}

// Helper function to determine provider based on channel and config
function getProvider(channel, config) {
  switch (channel) {
    case 'sms':
      return config.smsProvider || 'twilio';
    case 'email':
      return config.emailProvider || 'sendgrid';
    case 'push':
      return config.pushProvider || 'firebase';
    case 'webhook':
      return 'custom';
    default:
      return 'unknown';
  }
}

// Metrics middleware for Express
function metricsMiddleware() {
  return responseTime((req, res, time) => {
    const endpoint = req.originalUrl || req.url;
    const method = req.method;
    const status = res.statusCode;

    // For notification endpoints, record provider calls
    if (endpoint.includes('/api/v1/notifications')) {
      const provider = req.headers['x-notification-provider'] || 'unknown';
      metrics.providerCallsTotal.inc({ provider, endpoint, status });
      metrics.providerResponseTimeSeconds.observe({ provider, endpoint }, time / 1000);
    }
  });
}

// Notification sender wrapper with metrics
function createNotificationSenderWrapper(providerName, sender) {
  return {
    send: async (notification, config) => {
      const start = Date.now();
      const channel = getChannel(notification);
      const provider = getProvider(channel, config);

      try {
        // Send notification
        const result = await sender.send(notification, config);
        const duration = Date.now() - start;

        // Record successful notification
        metrics.notificationsSentTotal.inc({
          channel,
          provider: providerName,
          notification_type: notification.type || 'general',
          status: result.status || 'sent',
          priority: notification.priority || 'normal'
        });

        metrics.deliveryLatencySeconds.observe(
          { channel, provider: providerName, notification_type: notification.type || 'general' },
          duration / 1000
        );

        // Record channel-specific metrics
        switch (channel) {
          case 'sms':
            metrics.smsSentTotal.inc({
              provider: providerName,
              status: result.status || 'sent',
              country_code: notification.to.country_code || 'unknown'
            });
            
            // Record cost if available
            if (result.cost) {
              metrics.smsCostTotal.inc(
                { provider: providerName, country_code: notification.to.country_code || 'unknown' },
                result.cost
              );
            }
            break;
          
          case 'email':
            metrics.emailSentTotal.inc({
              provider: providerName,
              status: result.status || 'sent',
              template_id: notification.template_id || 'default'
            });
            break;
          
          case 'push':
            metrics.pushSentTotal.inc({
              provider: providerName,
              status: result.status || 'sent',
              platform: notification.platform || 'unknown'
            });
            break;
        }

        // Record template rendering if applicable
        if (notification.template_id) {
          metrics.templatesRenderedTotal.inc({
            template_id: notification.template_id,
            channel
          });
        }

        return result;
      } catch (error) {
        const duration = Date.now() - start;
        const errorType = error.code || error.type || 'unknown';

        // Record failed notification
        metrics.notificationsSentTotal.inc({
          channel,
          provider: providerName,
          notification_type: notification.type || 'general',
          status: 'failed',
          priority: notification.priority || 'normal'
        });

        metrics.deliveryLatencySeconds.observe(
          { channel, provider: providerName, notification_type: notification.type || 'general' },
          duration / 1000
        );

        metrics.errorsTotal.inc({
          error_type: errorType,
          channel,
          provider: providerName
        });

        metrics.providerErrorsTotal.inc({
          provider: providerName,
          error_type: errorType
        });

        throw error;
      }
    }
  };
}

// Queue processor wrapper
function createQueueProcessorWrapper(queue) {
  return {
    add: async (notification, options = {}) => {
      const job = await queue.add('send-notification', notification, options);
      
      // Update queue size metric
      metrics.queueSize.set(await queue.getJobCounts());
      
      return job;
    },
    
    process: async (concurrency = 1) => {
      queue.process('send-notification', concurrency, async (job) => {
        const start = Date.now();
        
        try {
          // Update active workers
          metrics.activeWorkers.inc();
          
          const result = await processNotificationJob(job.data);
          const duration = Date.now() - start;
          
          // Record successful processing
          return result;
        } catch (error) {
          const duration = Date.now() - start;
          
          // Record retry if applicable
          if (job.attemptsMade < (job.opts.attempts || 3)) {
            metrics.retriesTotal.inc({
              channel: getChannel(job.data),
              provider: getProvider(getChannel(job.data), {}),
              retry_count: job.attemptsMade + 1
            });
            throw error; // Will trigger retry
          } else {
            // Move to DLQ
            metrics.dlqMessagesTotal.inc({
              channel: getChannel(job.data),
              error_type: error.code || 'max_retries_exceeded'
            });
            
            // Archive failed job
            await job.moveToFailed({ message: error.message }, true);
          }
        } finally {
          metrics.activeWorkers.dec();
          metrics.queueSize.set(await queue.getJobCounts());
        }
      });
    }
  };
}

// Template engine wrapper
function createTemplateEngineWrapper(engine) {
  return {
    render: async (templateId, data, channel) => {
      const start = Date.now();
      
      try {
        const rendered = await engine.render(templateId, data, channel);
        const duration = Date.now() - start;
        
        metrics.templatesRenderedTotal.inc({
          template_id: templateId,
          channel
        });
        
        return rendered;
      } catch (error) {
        metrics.templateErrorsTotal.inc({
          template_id: templateId,
          error_type: error.name || 'rendering_error'
        });
        
        throw error;
      }
    }
  };
}

// Webhook handler wrapper for delivery confirmations
function createWebhookHandlerWrapper(handler) {
  return {
    handle: async (provider, event, payload) => {
      try {
        const result = await handler.handle(provider, event, payload);
        
        // Record delivery confirmation
        if (event.includes('delivered') || event.includes('sent')) {
          metrics.deliveryConfirmationsTotal.inc({
            channel: getChannelFromEvent(event),
            provider,
            status: 'delivered'
          });
        }
        
        // Record user engagement
        if (event.includes('opened') || event.includes('clicked')) {
          metrics.notificationsOpenedTotal.inc({
            channel: getChannelFromEvent(event),
            notification_type: payload.notification_type || 'unknown'
          });
        }
        
        if (event.includes('clicked')) {
          metrics.notificationsClickedTotal.inc({
            channel: getChannelFromEvent(event),
            notification_type: payload.notification_type || 'unknown'
          });
        }
        
        return result;
      } catch (error) {
        console.error('Webhook handling error:', error);
        throw error;
      }
    }
  };
}

// Helper function to get channel from webhook event
function getChannelFromEvent(event) {
  if (event.includes('sms') || event.includes('message')) return 'sms';
  if (event.includes('email')) return 'email';
  if (event.includes('push')) return 'push';
  return 'unknown';
}

// Function to get metrics as string
async function getMetrics() {
  return await register.metrics();
}

// Function to reset metrics (for testing)
function resetMetrics() {
  register.resetMetrics();
}

// Function to update queue metrics periodically
async function updateQueueMetrics(queue) {
  if (queue) {
    const counts = await queue.getJobCounts();
    metrics.queueSize.set(counts.waiting + counts.active + counts.delayed);
  }
}

module.exports = {
  metrics,
  metricsMiddleware,
  createNotificationSenderWrapper,
  createQueueProcessorWrapper,
  createTemplateEngineWrapper,
  createWebhookHandlerWrapper,
  updateQueueMetrics,
  getMetrics,
  resetMetrics,
  register
};
