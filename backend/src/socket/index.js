// parking-management/backend/src/socket/index.js
import { logger } from '../utils/logger.js';

export const setupWebSocket = (io, prisma) => {
  // Authentication middleware
  io.use((socket, next) => {
    const token = socket.handshake.auth.token;
    
    if (!token) {
      return next(new Error('Authentication required'));
    }

    try {
      const decoded = jwt.verify(token, process.env.JWT_SECRET);
      socket.userId = decoded.userId;
      next();
    } catch (error) {
      return next(new Error('Invalid token'));
    }
  });

  io.on('connection', (socket) => {
    const userId = socket.userId;
    logger.info(`WebSocket connected: ${userId}`);

    // Join user room
    socket.join(`user:${userId}`);

    // Handle booking events
    socket.on('booking:create', async (data) => {
      try {
        // Create booking
        const booking = await prisma.booking.create({
          data: {
            userId,
            parkingId: data.parkingId,
            startTime: new Date(data.startTime),
            endTime: new Date(data.endTime),
            duration: data.duration,
            totalPrice: data.totalPrice,
          },
          include: {
            parkingSpot: true,
          },
        });

        // Notify user
        io.to(`user:${userId}`).emit('booking:created', booking);

        // Notify parking spot updates to other users
        io.emit('parking:update', {
          parkingId: data.parkingId,
          status: 'reserved',
          timestamp: new Date().toISOString(),
        });

        logger.info(`Booking created: ${booking.id}`);
      } catch (error) {
        logger.error('Booking creation error:', error);
        socket.emit('error', {
          event: 'booking:create',
          message: error.message,
        });
      }
    });

    // Handle booking cancellation
    socket.on('booking:cancel', async ({ bookingId }) => {
      try {
        const booking = await prisma.booking.update({
          where: { id: bookingId },
          data: { status: 'CANCELLED' },
          include: {
            parkingSpot: true,
          },
        });

        // Notify user
        io.to(`user:${userId}`).emit('booking:cancelled', booking);

        // Notify parking spot updates
        io.emit('parking:update', {
          parkingId: booking.parkingId,
          status: 'available',
          timestamp: new Date().toISOString(),
        });

        logger.info(`Booking cancelled: ${bookingId}`);
      } catch (error) {
        logger.error('Booking cancellation error:', error);
        socket.emit('error', {
          event: 'booking:cancel',
          message: error.message,
        });
      }
    });

    // Handle check-in
    socket.on('booking:checkin', async ({ bookingId }) => {
      try {
        const booking = await prisma.booking.update({
          where: { id: bookingId },
          data: {
            status: 'CONFIRMED',
            checkInTime: new Date(),
          },
          include: {
            parkingSpot: true,
          },
        });

        io.to(`user:${userId}`).emit('booking:checkedin', booking);
        logger.info(`Check-in: ${bookingId}`);
      } catch (error) {
        logger.error('Check-in error:', error);
        socket.emit('error', {
          event: 'booking:checkin',
          message: error.message,
        });
      }
    });

    // Handle check-out
    socket.on('booking:checkout', async ({ bookingId }) => {
      try {
        const booking = await prisma.booking.update({
          where: { id: bookingId },
          data: {
            status: 'COMPLETED',
            checkOutTime: new Date(),
          },
          include: {
            parkingSpot: true,
          },
        });

        io.to(`user:${userId}`).emit('booking:checkedout', booking);
        logger.info(`Check-out: ${bookingId}`);
      } catch (error) {
        logger.error('Check-out error:', error);
        socket.emit('error', {
          event: 'booking:checkout',
          message: error.message,
        });
      }
    });

    // Handle real-time availability subscription
    socket.on('parking:subscribe', async ({ parkingId }) => {
      socket.join(`parking:${parkingId}`);
      
      // Send current availability
      const availability = await prisma.availability.findFirst({
        where: { parkingId },
        orderBy: { date: 'asc' },
      });

      socket.emit('parking:availability', {
        parkingId,
        availability,
        timestamp: new Date().toISOString(),
      });

      logger.info(`Subscribed to parking: ${parkingId}`);
    });

    // Handle unsubscription
    socket.on('parking:unsubscribe', ({ parkingId }) => {
      socket.leave(`parking:${parkingId}`);
      logger.info(`Unsubscribed from parking: ${parkingId}`);
    });

    // Handle disconnection
    socket.on('disconnect', () => {
      logger.info(`WebSocket disconnected: ${userId}`);
    });
  });

  // Broadcast availability updates
  const broadcastAvailabilityUpdate = async (parkingId) => {
    const availability = await prisma.availability.findFirst({
      where: { parkingId },
      orderBy: { date: 'asc' },
    });

    io.to(`parking:${parkingId}`).emit('parking:availability:update', {
      parkingId,
      availability,
      timestamp: new Date().toISOString(),
    });
  };

  return {
    broadcastAvailabilityUpdate,
  };
};

export default setupWebSocket;