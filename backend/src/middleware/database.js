// parking-management/backend/src/middleware/database.js
import { dbManager } from '../config/database.js';

/**
 * Middleware to route queries to appropriate database
 */
export const databaseRouter = (options = {}) => {
  const { type = 'read', model, operation } = options;
  
  return async (req, res, next) => {
    // Attach database client to request
    req.db = {
      read: dbManager.getReadClient(),
      write: dbManager.getWriteClient(),
    };
    
    // Attach query helper
    req.db.query = async (query, params = []) => {
      const client = type === 'write' ? req.db.write : req.db.read;
      return await dbManager.executeWithClient(client, query, params);
    };
    
    // Log database routing
    if (process.env.NODE_ENV === 'development') {
      req.db.type = type;
      req.db.model = model;
      req.db.operation = operation;
    }
    
    next();
  };
};

/**
 * Read operation middleware
 */
export const readOperation = (model, operation) => {
  return databaseRouter({ type: 'read', model, operation });
};

/**
 * Write operation middleware
 */
export const writeOperation = (model, operation) => {
  return databaseRouter({ type: 'write', model, operation });
};

/**
 * Query performance monitoring
 */
export const queryPerformance = (model, operation) => {
  return async (req, res, next) => {
    const start = process.hrtime();
    
    // Track query execution
    res.on('finish', () => {
      const [seconds, nanoseconds] = process.hrtime(start);
      const duration = seconds * 1000 + nanoseconds / 1000000;
      
      if (duration > 100) { // Log queries slower than 100ms
        logger.warn(`Slow query detected: ${model}.${operation} took ${duration.toFixed(2)}ms`, {
          model,
          operation,
          duration,
          path: req.path,
          method: req.method,
          userId: req.user?.id,
        });
      }
    });
    
    next();
  };
};

export default {
  databaseRouter,
  readOperation,
  writeOperation,
  queryPerformance,
};