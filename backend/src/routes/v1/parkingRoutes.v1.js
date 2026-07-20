// parking-management/backend/src/routes/v1/parkingRoutes.v1.js
import express from 'express';
import { parkingControllerV1 } from '../../controllers/v1/parkingController.v1.js';
import { authenticate } from '../../middleware/auth.js';

const router = express.Router();

router.get('/search', authenticate, parkingControllerV1.search);
router.get('/:id', authenticate, parkingControllerV1.getSpot);

export default router;

// parking-management/backend/src/routes/v2/parkingRoutes.v2.js
import { parkingControllerV2 } from '../../controllers/v2/parkingController.v2.js';

const router = express.Router();

router.get('/search', authenticate, parkingControllerV2.search);
router.get('/:id', authenticate, parkingControllerV2.getSpot);
router.get('/:id/availability', authenticate, parkingControllerV2.getAvailability);
router.post('/:id/book', authenticate, parkingControllerV2.book);

export default router;