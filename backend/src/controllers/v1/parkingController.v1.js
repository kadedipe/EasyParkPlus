// parking-management/backend/src/controllers/v1/parkingController.v1.js
/**
 * V1 Parking Controller
 * Original implementation with basic features
 */
export const parkingControllerV1 = {
  async search(req, res) {
    const { location, date, time } = req.query;
    
    // V1: Basic search with minimal filters
    const spots = await prisma.parkingSpot.findMany({
      where: {
        OR: [
          { address: { contains: location } },
          { city: { contains: location } },
        ],
        status: 'AVAILABLE',
      },
      take: 10,
    });

    res.json({
      version: 'v1',
      data: spots,
      count: spots.length,
    });
  },

  async getSpot(req, res) {
    const { id } = req.params;
    
    const spot = await prisma.parkingSpot.findUnique({
      where: { id },
    });

    if (!spot) {
      return res.status(404).json({ error: 'Spot not found' });
    }

    // V1: Basic spot information
    res.json({
      version: 'v1',
      data: spot,
    });
  },
};

// parking-management/backend/src/controllers/v2/parkingController.v2.js
/**
 * V2 Parking Controller
 * Enhanced version with more features
 */
export const parkingControllerV2 = {
  async search(req, res) {
    const { location, date, time, duration, priceRange, features } = req.query;
    
    // V2: Enhanced search with more filters
    const spots = await prisma.parkingSpot.findMany({
      where: {
        OR: [
          { address: { contains: location } },
          { city: { contains: location } },
          { name: { contains: location } },
        ],
        status: 'AVAILABLE',
        hourlyRate: {
          gte: priceRange?.min || 0,
          lte: priceRange?.max || 100,
        },
        features: features ? { hasSome: features.split(',') } : undefined,
      },
      include: {
        reviews: {
          take: 5,
          orderBy: { createdAt: 'desc' },
        },
        availability: {
          where: { date: new Date(date) },
          take: 1,
        },
      },
      take: 20,
    });

    // V2: Enhanced response with more data
    res.json({
      version: 'v2',
      data: spots,
      count: spots.length,
      filters: {
        applied: { location, date, time, duration, priceRange, features },
        available: ['priceRange', 'features', 'duration'],
      },
    });
  },

  async getSpot(req, res) {
    const { id } = req.params;
    
    const spot = await prisma.parkingSpot.findUnique({
      where: { id },
      include: {
        reviews: {
          take: 20,
          orderBy: { createdAt: 'desc' },
        },
        availability: {
          take: 7,
          orderBy: { date: 'asc' },
        },
      },
    });

    if (!spot) {
      return res.status(404).json({ error: 'Spot not found' });
    }

    // V2: Enhanced spot information with reviews and availability
    res.json({
      version: 'v2',
      data: {
        ...spot,
        stats: {
          averageRating: spot.reviews.reduce((acc, r) => acc + r.rating, 0) / spot.reviews.length || 0,
          totalReviews: spot.reviews.length,
          availableDays: spot.availability.filter(a => a.availableSlots > 0).length,
        },
      },
    });
  },
};