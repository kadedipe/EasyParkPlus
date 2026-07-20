// parking-management/backend/src/middleware/versioning.js

// API versions
export const API_VERSIONS = {
  V1: 'v1',
  V2: 'v2',
  V3: 'v3',
  LATEST: 'v1', // Current latest version
};

// Version middleware
export const versionMiddleware = (req, res, next) => {
  // Get version from header, query param, or URL
  let version = req.headers['api-version'] || 
                req.query.version || 
                req.params.version ||
                API_VERSIONS.LATEST;

  // Validate version
  if (!Object.values(API_VERSIONS).includes(version)) {
    version = API_VERSIONS.LATEST;
  }

  // Set version on request
  req.apiVersion = version;
  
  // Add version to response headers
  res.setHeader('API-Version', version);
  res.setHeader('API-Latest-Version', API_VERSIONS.LATEST);
  res.setHeader('API-Deprecated-Versions', 'v0');

  // Check if version is deprecated
  if (isVersionDeprecated(version)) {
    res.setHeader('API-Deprecated', 'true');
    res.setHeader('API-Deprecation-Date', '2024-06-01');
    res.setHeader('API-Sunset-Date', '2024-12-01');
  }

  next();
};

// Check if version is deprecated
const isVersionDeprecated = (version) => {
  const deprecatedVersions = [];
  return deprecatedVersions.includes(version);
};

// Version routing
export const versionRouter = (routes) => {
  return (req, res, next) => {
    const version = req.apiVersion;
    const route = routes[version];
    
    if (!route) {
      return res.status(404).json({
        error: 'VERSION_NOT_FOUND',
        message: `API version ${version} not found`,
        availableVersions: Object.keys(routes),
      });
    }
    
    // Pass control to version-specific route
    return route(req, res, next);
  };
};

// Versioned route factory
export const createVersionedRoutes = (handlers) => {
  return {
    [API_VERSIONS.V1]: handlers.v1,
    [API_VERSIONS.V2]: handlers.v2,
    [API_VERSIONS.V3]: handlers.v3,
  };
};

// Version-aware controller
export const versionController = (controllerMap) => {
  return async (req, res, next) => {
    const version = req.apiVersion;
    const controller = controllerMap[version];
    
    if (!controller) {
      return res.status(404).json({
        error: 'VERSION_NOT_FOUND',
        message: `Version ${version} not supported for this endpoint`,
      });
    }
    
    try {
      await controller(req, res, next);
    } catch (error) {
      next(error);
    }
  };
};

export default {
  API_VERSIONS,
  versionMiddleware,
  versionRouter,
  createVersionedRoutes,
  versionController,
};