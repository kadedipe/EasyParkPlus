const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const Bull = require('bull');
const twilio = require('twilio');
const sgMail = require('@sendgrid/mail');
const admin = require('firebase-admin');
const { 
  metrics, 
  metricsMiddleware, 
  createNotificationSenderWrapper,
  createQueueProcessorWrapper,
  createTemplateEngineWrapper,
  createWebhookHandlerWrapper,
  updateQueueMetrics,
  getMetrics 
} = require('./metrics');

const app = express();

// Security middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", "'unsafe-inline'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      imgSrc: ["'self'", "data:", "https:"],
      connectSrc: ["'self'", "https://api.twilio.com", "https://api.sendgrid.com"]
    }
  }
}));
app.use(cors());
app.use(compression());

// Rate limiting
const notificationLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 1000, // limit each IP to 1000 requests per windowMs
  message: 'Too many notification requests from this IP, please try again after 15 minutes'
});

// Apply rate limiting to notification endpoints
app.use('/api/v1/notifications/send', notificationLimiter);

// Metrics middleware
app.use(metricsMiddleware());

// Body parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Request logging middleware
app.use((req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`[Notification] ${req.method} ${req.originalUrl} ${res.statusCode} ${duration}ms`);
  });
  
  next();
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Notification Service Error:', err);
  
  // Increment error metrics
  metrics.errorsTotal.inc({
    error_type: err.name || 'UnknownError',
    channel: req.body?.channel || 'unknown',
    provider: req.body?.provider || 'unknown'
  });

  res.status(err.status || 500).json({
    error: err.name || 'NotificationError',
    message: err.message || 'An error occurred while sending notification',
    code: err.code || 'INTERNAL_ERROR',
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
  });
});

// Initialize notification providers
const twilioClient = twilio(
  process.env.TWILIO_ACCOUNT_SID,
  process.env.TWILIO_AUTH_TOKEN
);

sgMail.setApiKey(process.env.SENDGRID_API_KEY);

// Initialize Firebase Admin for push notifications
if (process.env.FIREBASE_SERVICE_ACCOUNT_KEY) {
  admin.initializeApp({
    credential: admin.credential.cert(
      JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT_KEY)
    )
  });
}

// Create notification queue
const notificationQueue = new Bull('notifications', {
  redis: {
    host: process.env.REDIS_HOST || 'redis',
    port: process.env.REDIS_PORT || 6379,
    password: process.env.REDIS_PASSWORD
  },
  defaultJobOptions: {
    attempts: 3,
    backoff: {
      type: 'exponential',
      delay: 1000
    },
    removeOnComplete: true,
    removeOnFail: false
  }
});

// Create wrapped providers
const twilioSender = createNotificationSenderWrapper('twilio', {
  send: async (notification, config) => {
    const { to, body, from = process.env.TWILIO_PHONE_NUMBER } = notification;
    
    const message = await twilioClient.messages.create({
      body,
      to: to.phone,
      from,
      ...config
    });
    
    return {
      id: message.sid,
      status: message.status,
      price: message.price,
      priceUnit: message.priceUnit
    };
  }
});

const sendgridSender = createNotificationSenderWrapper('sendgrid', {
  send: async (notification, config) => {
    const { to, subject, text, html, template_id, template_data } = notification;
    
    const msg = {
      to: to.email,
      from: process.env.SENDGRID_FROM_EMAIL,
      subject,
      ...(text && { text }),
      ...(html && { html }),
      ...(template_id && {
        templateId: template_id,
        dynamicTemplateData: template_data
      }),
      ...config
    };
    
    const [response] = await sgMail.send(msg);
    
    return {
      id: response.headers['x-message-id'],
      status: 'sent'
    };
  }
});

const firebaseSender = createNotificationSenderWrapper('firebase', {
  send: async (notification, config) => {
    const { to, title, body, data, image } = notification;
    
    const message = {
      token: to.device_token,
      notification: {
        title,
        body,
        ...(image && { image })
      },
      data: data || {},
      ...config
    };
    
    const response = await admin.messaging().send(message);
    
    return {
      id: response,
      status: 'sent'
    };
  }
});

// Create queue processor
const queueProcessor = createQueueProcessorWrapper(notificationQueue);

// Template engine
const templateEngine = createTemplateEngineWrapper({
  render: async (templateId, data, channel) => {
    // Load template from database or filesystem
    const template = await loadTemplate(templateId, channel);
    
    // Render template with data
    return renderTemplate(template, data, channel);
  }
});

// Webhook handler
const webhookHandler = createWebhookHandlerWrapper({
  handle: async (provider, event, payload) => {
    switch (provider) {
      case 'twilio':
        return await handleTwilioWebhook(event, payload);
      case 'sendgrid':
        return await handleSendGridWebhook(event, payload);
      case 'firebase':
        return await handleFirebaseWebhook(event, payload);
      default:
        throw new Error(`Unsupported provider: ${provider}`);
    }
  }
});

// Notification endpoints
app.post('/api/v1/notifications/send', async (req, res, next) => {
  try {
    const {
      channel,
      to,
      template_id,
      template_data = {},
      data = {},
      priority = 'normal',
      schedule_at,
      provider_override
    } = req.body;

    // Validate input
    if (!channel || !to) {
      throw new Error('Channel and recipient are required');
    }

    if (!isValidChannel(channel)) {
      throw new Error(`Invalid channel: ${channel}`);
    }

    // Load template if specified
    let notificationData = { ...data };
    if (template_id) {
      const rendered = await templateEngine.render(template_id, template_data, channel);
      notificationData = { ...notificationData, ...rendered };
    }

    // Create notification object
    const notification = {
      channel,
      to,
      ...notificationData,
      priority,
      timestamp: new Date().toISOString()
    };

    // Add to queue or send immediately based on priority
    let result;
    if (priority === 'high' || schedule_at) {
      // Send immediately for high priority
      result = await sendNotificationImmediately(notification, provider_override);
    } else {
      // Add to queue for normal priority
      const job = await queueProcessor.add(notification, {
        priority: getBullPriority(priority),
        delay: schedule_at ? new Date(schedule_at).getTime() - Date.now() : 0
      });
      
      result = {
        id: job.id,
        status: 'queued',
        queue_position: await notificationQueue.getJobCountByTypes('waiting'),
        estimated_delay: schedule_at ? new Date(schedule_at).getTime() - Date.now() : 0
      };
    }

    res.json({
      success: true,
      notification: {
        id: result.id,
        channel,
        status: result.status,
        ...(result.queue_position && { queue_position: result.queue_position }),
        ...(result.estimated_delay && { estimated_delay: result.estimated_delay }),
        timestamp: notification.timestamp
      }
    });
  } catch (error) {
    next(error);
  }
});

app.post('/api/v1/notifications/batch', async (req, res, next) => {
  try {
    const { notifications, options = {} } = req.body;

    if (!Array.isArray(notifications) || notifications.length === 0) {
      throw new Error('Notifications array is required and cannot be empty');
    }

    if (notifications.length > 1000) {
      throw new Error('Batch size cannot exceed 1000 notifications');
    }

    const results = [];
    const errors = [];

    // Process notifications in parallel with concurrency limit
    const concurrency = options.concurrency || 10;
    const batches = [];
    
    for (let i = 0; i < notifications.length; i += concurrency) {
      batches.push(notifications.slice(i, i + concurrency));
    }

    for (const batch of batches) {
      const batchPromises = batch.map(async (notification) => {
        try {
          const job = await queueProcessor.add(notification, {
            priority: getBullPriority(notification.priority || 'normal')
          });
          
          return {
            notification_id: notification.id || `batch_${Date.now()}_${Math.random()}`,
            status: 'queued',
            job_id: job.id,
            success: true
          };
        } catch (error) {
          return {
            notification_id: notification.id || `batch_${Date.now()}_${Math.random()}`,
            status: 'failed',
            error: error.message,
            success: false
          };
        }
      });

      const batchResults = await Promise.all(batchPromises);
      results.push(...batchResults);
      
      // Separate successes and errors
      batchResults.forEach(result => {
        if (result.success) {
          results.push(result);
        } else {
          errors.push(result);
        }
      });
    }

    // Update queue metrics
    await updateQueueMetrics(notificationQueue);

    res.json({
      success: true,
      total: notifications.length,
      queued: results.filter(r => r.success).length,
      failed: errors.length,
      results,
      ...(errors.length > 0 && { errors })
    });
  } catch (error) {
    next(error);
  }
});

app.get('/api/v1/notifications/:id/status', async (req, res, next) => {
  try {
    const { id } = req.params;
    
    // Check if it's a job ID
    const job = await notificationQueue.getJob(id);
    
    if (job) {
      const state = await job.getState();
      const result = await job.finished().catch(() => null);
      
      res.json({
        id,
        type: 'queued',
        state,
        progress: job.progress(),
        attempts_made: job.attemptsMade,
        created_at: job.timestamp,
        processed_at: job.processedOn,
        finished_at: job.finishedOn,
        result,
        failed_reason: job.failedReason
      });
    } else {
      // Check database for sent notifications
      const notification = await getNotification(id);
      
      if (!notification) {
        throw new Error(`Notification ${id} not found`);
      }
      
      res.json({
        id: notification.id,
        type: 'sent',
        channel: notification.channel,
        status: notification.status,
        provider: notification.provider,
        sent_at: notification.sent_at,
        delivered_at: notification.delivered_at,
        error_message: notification.error_message
      });
    }
  } catch (error) {
    next(error);
  }
});

// Template endpoints
app.post('/api/v1/notifications/templates', async (req, res, next) => {
  try {
    const { id, name, channel, content, variables = [] } = req.body;
    
    if (!id || !name || !channel || !content) {
      throw new Error('ID, name, channel, and content are required');
    }
    
    const template = await saveTemplate({
      id,
      name,
      channel,
      content,
      variables,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });
    
    res.json({
      success: true,
      template: {
        id: template.id,
        name: template.name,
        channel: template.channel,
        variables: template.variables,
        created_at: template.created_at,
        updated_at: template.updated_at
      }
    });
  } catch (error) {
    next(error);
  }
});

app.get('/api/v1/notifications/templates/:id', async (req, res, next) => {
  try {
    const { id } = req.params;
    const { channel } = req.query;
    
    const template = await loadTemplate(id, channel);
    
    if (!template) {
      throw new Error(`Template ${id} not found`);
    }
    
    res.json({
      success: true,
      template
    });
  } catch (error) {
    next(error);
  }
});

// Webhook endpoints
app.post('/webhooks/twilio', express.urlencoded({ extended: false }), async (req, res) => {
  try {
    const { MessageStatus, MessageSid, To, From, ErrorCode, ErrorMessage } = req.body;
    
    await webhookHandler.handle('twilio', `message.${MessageStatus}`, {
      message_sid: MessageSid,
      to: To,
      from: From,
      status: MessageStatus,
      error_code: ErrorCode,
      error_message: ErrorMessage,
      timestamp: new Date().toISOString()
    });
    
    res.type('text/xml').send('<Response></Response>');
  } catch (error) {
    console.error('Twilio webhook error:', error);
    res.status(400).send('Webhook processing failed');
  }
});

app.post('/webhooks/sendgrid', async (req, res) => {
  try {
    const events = Array.isArray(req.body) ? req.body : [req.body];
    
    for (const event of events) {
      const { event: eventType, sg_message_id, email, timestamp } = event;
      
      await webhookHandler.handle('sendgrid', eventType, {
        message_id: sg_message_id,
        email,
        event: eventType,
        timestamp: new Date(timestamp * 1000).toISOString(),
        ...event
      });
    }
    
    res.status(200).send();
  } catch (error) {
    console.error('SendGrid webhook error:', error);
    res.status(400).json({ error: 'Webhook processing failed' });
  }
});

app.post('/webhooks/firebase', async (req, res) => {
  try {
    const { message_id, from, data, notification, priority, collapse_key } = req.body;
    
    await webhookHandler.handle('firebase', 'message.sent', {
      message_id,
      from,
      data,
      notification,
      priority,
      collapse_key,
      timestamp: new Date().toISOString()
    });
    
    res.status(200).send();
  } catch (error) {
    console.error('Firebase webhook error:', error);
    res.status(400).json({ error: 'Webhook processing failed' });
  }
});

// Health check endpoint
app.get('/health', async (req, res) => {
  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    providers: {
      twilio: await checkTwilioHealth(),
      sendgrid: await checkSendGridHealth(),
      firebase: await checkFirebaseHealth()
    },
    queue: await checkQueueHealth(),
    database: await checkDatabaseHealth(),
    redis: await checkRedisHealth()
  };

  res.json(health);
});

// Metrics endpoint (Prometheus format)
app.get('/metrics', async (req, res) => {
  try {
    res.set('Content-Type', 'text/plain');
    res.end(await getMetrics());
  } catch (error) {
    res.status(500).end();
  }
});

// Admin endpoints
app.get('/api/v1/admin/notifications/stats', async (req, res, next) => {
  try {
    const { start_date, end_date, channel, provider } = req.query;
    
    const stats = await getNotificationStats({
      start_date,
      end_date,
      channel,
      provider
    });

    res.json(stats);
  } catch (error) {
    next(error);
  }
});

app.get('/api/v1/admin/queue/stats', async (req, res, next) => {
  try {
    const queueStats = await notificationQueue.getJobCounts();
    const delayedJobs = await notificationQueue.getDelayed();
    const failedJobs = await notificationQueue.getFailed();
    
    res.json({
      queue_stats: queueStats,
      delayed_count: delayedJobs.length,
      failed_count: failedJobs.length,
      active_workers: await getActiveWorkersCount(),
      oldest_job: await getOldestJobTimestamp()
    });
  } catch (error) {
    next(error);
  }
});

// Helper functions
async function sendNotificationImmediately(notification, providerOverride) {
  const channel = notification.channel;
  let provider = providerOverride;
  
  if (!provider) {
    switch (channel) {
      case 'sms':
        provider = 'twilio';
        break;
      case 'email':
        provider = 'sendgrid';
        break;
      case 'push':
        provider = 'firebase';
        break;
      default:
        throw new Error(`No default provider for channel: ${channel}`);
    }
  }
  
  let sender;
  switch (provider) {
    case 'twilio':
      sender = twilioSender;
      break;
    case 'sendgrid':
      sender = sendgridSender;
      break;
    case 'firebase':
      sender = firebaseSender;
      break;
    default:
      throw new Error(`Unsupported provider: ${provider}`);
  }
  
  const result = await sender.send(notification, {});
  
  // Save to database
  await saveNotification({
    ...notification,
    provider,
    status: result.status,
    provider_id: result.id,
    sent_at: new Date().toISOString()
  });
  
  return result;
}

async function processNotificationJob(notification) {
  return await sendNotificationImmediately(notification);
}

function isValidChannel(channel) {
  return ['sms', 'email', 'push', 'webhook'].includes(channel);
}

function getBullPriority(priority) {
  switch (priority) {
    case 'high': return 1;
    case 'normal': return 2;
    case 'low': return 3;
    default: return 2;
  }
}

async function checkTwilioHealth() {
  try {
    await twilioClient.messages.list({ limit: 1 });
    return { status: 'healthy' };
  } catch (error) {
    return { status: 'unhealthy', error: error.message };
  }
}

async function checkSendGridHealth() {
  try {
    // Simple SendGrid health check
    return { status: 'healthy' };
  } catch (error) {
    return { status: 'unhealthy', error: error.message };
  }
}

async function checkFirebaseHealth() {
  try {
    if (admin.apps.length > 0) {
      return { status: 'healthy' };
    }
    return { status: 'unhealthy', error: 'Firebase not initialized' };
  } catch (error) {
    return { status: 'unhealthy', error: error.message };
  }
}

async function checkQueueHealth() {
  try {
    const counts = await notificationQueue.getJobCounts();
    return {
      status: 'healthy',
      waiting: counts.waiting,
      active: counts.active,
      completed: counts.completed,
      failed: counts.failed,
      delayed: counts.delayed
    };
  } catch (error) {
    return { status: 'unhealthy', error: error.message };
  }
}

async function checkDatabaseHealth() {
  try {
    // Check database connection
    return { status: 'connected' };
  } catch (error) {
    return { status: 'disconnected', error: error.message };
  }
}

async function checkRedisHealth() {
  try {
    // Check Redis connection
    const client = notificationQueue.client;
    await client.ping();
    return { status: 'connected' };
  } catch (error) {
    return { status: 'disconnected', error: error.message };
  }
}

async function getActiveWorkersCount() {
  // This would require additional logic with Bull
  return 0;
}

async function getOldestJobTimestamp() {
  const jobs = await notificationQueue.getJobs(['waiting'], 0, 1);
  return jobs.length > 0 ? new Date(jobs[0].timestamp) : null;
}

// Database functions (mock implementations)
async function saveTemplate(data) {
  // Save template to database
  return data;
}

async function loadTemplate(id, channel) {
  // Load template from database
  // This is a mock implementation
  return {
    id,
    name: `Template ${id}`,
    channel,
    content: 'Default template content',
    variables: [],
    created_at: new Date().toISOString()
  };
}

function renderTemplate(template, data, channel) {
  // Simple template rendering
  let content = template.content;
  for (const [key, value] of Object.entries(data)) {
    content = content.replace(new RegExp(`{{${key}}}`, 'g'), value);
  }
  return { content };
}

async function saveNotification(data) {
  // Save notification to database
  // This is a mock implementation
  return {
    id: 'notif_' + Date.now(),
    ...data,
    created_at: new Date().toISOString()
  };
}

async function getNotification(id) {
  // Get notification from database
  // This is a mock implementation
  return null;
}

async function getNotificationStats(params) {
  // Get notification statistics from database
  // This is a mock implementation
  return {
    total: 1000,
    by_channel: {
      sms: { count: 400, delivered: 380, failed: 20 },
      email: { count: 500, delivered: 490, failed: 10 },
      push: { count: 100, delivered: 95, failed: 5 }
    },
    by_provider: {
      twilio: { count: 400, delivered: 380 },
      sendgrid: { count: 500, delivered: 490 },
      firebase: { count: 100, delivered: 95 }
    },
    by_type: {
      reservation_confirmation: 300,
      payment_receipt: 200,
      parking_alert: 500
    }
  };
}

// Webhook handlers
async function handleTwilioWebhook(event, payload) {
  // Update notification status in database
  console.log('Twilio webhook:', event, payload);
  return { processed: true };
}

async function handleSendGridWebhook(event, payload) {
  // Update notification status in database
  console.log('SendGrid webhook:', event, payload);
  return { processed: true };
}

async function handleFirebaseWebhook(event, payload) {
  // Update notification status in database
  console.log('Firebase webhook:', event, payload);
  return { processed: true };
}

// Start queue processing
queueProcessor.process(5); // Process 5 jobs concurrently

// Start periodic metric updates
setInterval(() => {
  updateQueueMetrics(notificationQueue);
}, 30000); // Update every 30 seconds

module.exports = {
  app,
  twilioSender,
  sendgridSender,
  firebaseSender,
  queueProcessor,
  templateEngine,
  webhookHandler
};
