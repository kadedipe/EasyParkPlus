// parking-management/backend/src/routes/parkingRoutes.js
import express from 'express';
import { API_VERSIONS, versionMiddleware } from '../middleware/versioning.js';
import v1Routes from './v1/parkingRoutes.v1.js';
import v2Routes from './v2/parkingRoutes.v2.js';

const router = express.Router();

// Apply version middleware
router.use(versionMiddleware);

// Version-specific routes
router.use('/v1', v1Routes);
router.use('/v2', v2Routes);

// Default to latest version
router.use('/', v2Routes);

// Version info endpoint
router.get('/versions', (req, res) => {
  res.json({
    versions: Object.values(API_VERSIONS),
    latest: API_VERSIONS.LATEST,
    deprecated: [],
    supported: Object.values(API_VERSIONS),
  });
});

export default router;