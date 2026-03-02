const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const { metrics, metricsMiddleware, getMetrics, updateParkingMetrics } = require('./metrics');

const app = express();

// Security middleware
app.use(helmet());
app.use(cors());
app.use(compression());

// Rate limiting
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  handler: (req, res) => {
    // Increment rate limit metric
    metrics.rateLimitHitsTotal.inc({
      endpoint: req.path,
      client_id: req.ip
    });
    
    res.status(429).json({
      error: 'Too many requests',
      message: 'Please try again later.'
    });
  }
});

// Apply rate limiting to all API routes
app.use('/api/', apiLimiter);

// Metrics middleware
app.use(metricsMiddleware());

// Request logging middleware
app.use((req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`${req.method} ${req.originalUrl} ${res.statusCode} ${duration}ms`);
  });
  
  next();
});

// Error tracking middleware
app.use((err, req, res, next) => {
  // Increment error metric
  metrics.errorsTotal.inc({
    type: err.name || 'UnknownError',
    endpoint: req.path
  });
  
  console.error('Error:', err);
  
  res.status(err.status || 500).json({
    error: err.name || 'InternalServerError',
    message: err.message || 'An unexpected error occurred',
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
  });
});

// Database query wrapper with metrics
function createDbQueryWrapper(dbClient) {
  return {
    query: async (text, params) => {
      const start = Date.now();
      const queryType = text.trim().split(' ')[0].toUpperCase(); // GET, INSERT, UPDATE, DELETE
      const tableMatch = text.match(/FROM\s+(\w+)|INTO\s+(\w+)|UPDATE\s+(\w+)/i);
      const table = tableMatch ? (tableMatch[1] || tableMatch[2] || tableMatch[3]) : 'unknown';
      
      try {
        const result = await dbClient.query(text, params);
        const duration = Date.now() - start;
        
        // Increment query counter
        metrics.databaseQueriesTotal.inc({ type: queryType, table });
        
        // Record query duration
        metrics.databaseQueryDurationSeconds.observe(
          { type: queryType, table },
          duration / 1000
        );
        
        return result;
      } catch (error) {
        const duration = Date.now() - start;
        
        // Still record failed query
        metrics.databaseQueriesTotal.inc({ type: queryType, table });
        metrics.databaseQueryDurationSeconds.observe(
          { type: queryType, table },
          duration / 1000
        );
        
        // Increment error metric
        metrics.errorsTotal.inc({ type: 'DatabaseError', endpoint: 'database' });
        
        throw error;
      }
    }
  };
}

// Cache wrapper with metrics
function createCacheWrapper(cacheClient) {
  return {
    get: async (key) => {
      const start = Date.now();
      
      try {
        const value = await cacheClient.get(key);
        const duration = Date.now() - start;
        
        if (value !== null) {
          metrics.cacheHitsTotal.inc({ key });
        } else {
          metrics.cacheMissesTotal.inc({ key });
        }
        
        // Record cache operation duration
        metrics.externalApiCallDurationSeconds.observe(
          { service: 'redis', endpoint: 'get' },
          duration / 1000
        );
        
        return value;
      } catch (error) {
        metrics.cacheMissesTotal.inc({ key });
        metrics.errorsTotal.inc({ type: 'CacheError', endpoint: 'cache' });
        throw error;
      }
    },
    
    set: async (key, value, ttl) => {
      const start = Date.now();
      
      try {
        await cacheClient.set(key, value, 'EX', ttl);
        const duration = Date.now() - start;
        
        metrics.externalApiCallDurationSeconds.observe(
          { service: 'redis', endpoint: 'set' },
          duration / 1000
        );
      } catch (error) {
        metrics.errorsTotal.inc({ type: 'CacheError', endpoint: 'cache' });
        throw error;
      }
    }
  };
}

// External API wrapper with metrics
function createExternalApiWrapper(serviceName, axiosInstance) {
  return {
    request: async (config) => {
      const start = Date.now();
      const endpoint = config.url || 'unknown';
      
      try {
        const response = await axiosInstance(config);
        const duration = Date.now() - start;
        
        // Increment API call counter
        metrics.externalApiCallsTotal.inc({
          service: serviceName,
          endpoint,
          status: response.status
        });
        
        // Record API call duration
        metrics.externalApiCallDurationSeconds.observe(
          { service: serviceName, endpoint },
          duration / 1000
        );
        
        return response;
      } catch (error) {
        const duration = Date.now() - start;
        const status = error.response ? error.response.status : 0;
        
        // Still record failed API call
        metrics.externalApiCallsTotal.inc({
          service: serviceName,
          endpoint,
          status
        });
        
        metrics.externalApiCallDurationSeconds.observe(
          { service: serviceName, endpoint },
          duration / 1000
        );
        
        metrics.errorsTotal.inc({
          type: 'ExternalApiError',
          endpoint: serviceName
        });
        
        throw error;
      }
    }
  };
}

// Authentication middleware with metrics
function createAuthMiddleware() {
  return async (req, res, next) => {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      metrics.authFailureTotal.inc({ method: 'jwt', reason: 'missing_token' });
      return res.status(401).json({ error: 'Unauthorized' });
    }
    
    const token = authHeader.substring(7);
    
    try {
      // Verify JWT token
      const decoded = jwt.verify(token, process.env.JWT_SECRET);
      req.user = decoded;
      
      // Increment success metric
      metrics.authSuccessTotal.inc({ method: 'jwt' });
      
      // Track active users
      metrics.activeUsers.inc({ user_type: decoded.role || 'user' });
      
      res.on('finish', () => {
        metrics.activeUsers.dec({ user_type: decoded.role || 'user' });
      });
      
      next();
    } catch (error) {
      metrics.authFailureTotal.inc({ method: 'jwt', reason: 'invalid_token' });
      return res.status(401).json({ error: 'Unauthorized' });
    }
  };
}

// Example route with metrics
app.post('/api/v1/parking/reservations', createAuthMiddleware(), async (req, res) => {
  const { lot_id, space_id, start_time, end_time } = req.body;
  const user_id = req.user.id;
  
  try {
    // Create reservation in database
    const db = createDbQueryWrapper(dbClient);
    const result = await db.query(
      'INSERT INTO reservations (user_id, lot_id, space_id, start_time, end_time, status) VALUES ($1, $2, $3, $4, $5, $6) RETURNING *',
      [user_id, lot_id, space_id, start_time, end_time, 'active']
    );
    
    // Increment reservation metric
    metrics.parkingReservationsCreated.inc({
      lot_id,
      user_type: req.user.role || 'user'
    });
    
    // Update parking space availability
    await updateParkingMetrics();
    
    res.status(201).json({
      message: 'Reservation created successfully',
      reservation: result.rows[0]
    });
  } catch (error) {
    next(error);
  }
});

// Example route for checking parking spaces
app.get('/api/v1/parking/lots/:id/spaces', async (req, res) => {
  const { id } = req.params;
  
  try {
    // Try cache first
    const cache = createCacheWrapper(redisClient);
    const cachedSpaces = await cache.get(`parking_lot_${id}_spaces`);
    
    if (cachedSpaces) {
      return res.json(JSON.parse(cachedSpaces));
    }
    
    // If not in cache, query database
    const db = createDbQueryWrapper(dbClient);
    const result = await db.query(
      'SELECT * FROM parking_spaces WHERE parking_lot_id = $1 AND is_available = true',
      [id]
    );
    
    // Store in cache for 5 minutes
    await cache.set(`parking_lot_${id}_spaces`, JSON.stringify(result.rows), 300);
    
    res.json(result.rows);
  } catch (error) {
    next(error);
  }
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    database: 'connected', // You should actually check DB connection
    redis: 'connected' // You should actually check Redis connection
  });
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

// Start periodic metric updates
setInterval(updateParkingMetrics, 60000); // Update every minute

module.exports = {
  app,
  createDbQueryWrapper,
  createCacheWrapper,
  createExternalApiWrapper,
  createAuthMiddleware
};
