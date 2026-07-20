// parking-management/backend/tests/unit/test_services/notification/notification.service.test.js
const NotificationService = require('../../../../src/services/notification.service');
const EmailService = require('../../../../src/services/email.service');
const SMSService = require('../../../../src/services/sms.service');
const PushNotificationService = require('../../../../src/services/push-notification.service');
const TestDataFactory = require('../helpers/test-data-factory');
const { Notification, User } = require('../../../../src/models');

describe('NotificationService', () => {
  let notificationService;
  let emailService;
  let smsService;
  let pushService;
  
  beforeEach(() => {
    emailService = new EmailService();
    smsService = new SMSService();
    pushService = new PushNotificationService();
    notificationService = new NotificationService(emailService, smsService, pushService);
  });
  
  describe('sendNotification', () => {
    let user;
    
    beforeEach(async () => {
      user = await User.create(TestDataFactory.generateUser({
        preferences: {
          notifications: {
            email: true,
            sms: true,
            push: true
          }
        }
      }));
    });
    
    it('should send notification via preferred channels', async () => {
      const notificationData = {
        userId: user._id,
        type: 'reservation_reminder',
        title: 'Upcoming Reservation',
        body: 'Your reservation starts in 1 hour'
      };
      
      await notificationService.sendNotification(notificationData);
      
      expect(emailService.sendEmail).toHaveBeenCalled();
      expect(smsService.sendSMS).toHaveBeenCalled();
      expect(pushService.sendPush).toHaveBeenCalled();
      
      // Verify notification saved
      const notification = await Notification.findOne({ userId: user._id });
      expect(notification).toBeDefined();
      expect(notification.title).toBe(notificationData.title);
    });
    
    it('should respect user preferences', async () => {
      user.preferences.notifications.email = false;
      await user.save();
      
      const notificationData = {
        userId: user._id,
        type: 'promotion',
        title: 'Special Offer',
        body: 'Get 20% off your next booking!'
      };
      
      await notificationService.sendNotification(notificationData);
      
      expect(emailService.sendEmail).not.toHaveBeenCalled();
      expect(smsService.sendSMS).toHaveBeenCalled();
    });
    
    it('should respect priority levels', async () => {
      const highPriorityData = {
        userId: user._id,
        type: 'alert',
        title: 'Emergency Alert',
        body: 'Parking garage maintenance',
        priority: 'high'
      };
      
      await notificationService.sendNotification(highPriorityData);
      
      // High priority should use all channels regardless of preferences
      expect(emailService.sendEmail).toHaveBeenCalled();
      expect(smsService.sendSMS).toHaveBeenCalled();
      expect(pushService.sendPush).toHaveBeenCalled();
    });
    
    it('should handle notification batching', async () => {
      // Send multiple notifications
      for (let i = 0; i < 5; i++) {
        await notificationService.sendNotification({
          userId: user._id,
          type: 'system',
          title: `Message ${i}`,
          body: `Content ${i}`
        });
      }
      
      // Should batch similar notifications
      const notifications = await Notification.find({ userId: user._id });
      expect(notifications.length).toBeLessThan(5);
    });
  });
  
  describe('sendReservationReminders', () => {
    let users;
    let reservations;
    
    beforeEach(async () => {
      users = await Promise.all([
        User.create(TestDataFactory.generateUser()),
        User.create(TestDataFactory.generateUser()),
        User.create(TestDataFactory.generateUser())
      ]);
      
      reservations = await Promise.all(
        users.map(user => 
          Reservation.create(TestDataFactory.generateReservation(user._id, new mongoose.Types.ObjectId(), {
            startTime: new Date(Date.now() + 3600000) // 1 hour from now
          }))
        )
      );
    });
    
    it('should send reminders for upcoming reservations', async () => {
      const result = await notificationService.sendReservationReminders();
      
      expect(result).toHaveProperty('sent', 3);
      expect(result).toHaveProperty('failed', 0);
    });
    
    it('should respect reminder timing preferences', async () => {
      const userWithPreference = users[0];
      userWithPreference.preferences.reminderMinutes = 30;
      await userWithPreference.save();
      
      const result = await notificationService.sendReservationReminders();
      
      // Should only send to users with appropriate reminder timing
      expect(result.sent).toBe(3); // All have reservations in 1 hour
    });
    
    it('should not send duplicate reminders', async () => {
      await notificationService.sendReservationReminders();
      const result = await notificationService.sendReservationReminders();
      
      expect(result.sent).toBe(0);
      expect(result.skipped).toBe(3);
    });
  });
  
  describe('getUserNotifications', () => {
    let user;
    
    beforeEach(async () => {
      user = await User.create(TestDataFactory.generateUser());
      
      // Create notifications
      for (let i = 0; i < 10; i++) {
        await Notification.create({
          userId: user._id,
          type: 'system',
          title: `Notification ${i}`,
          body: `Content ${i}`,
          read: i < 5 // First 5 read, next 5 unread
        });
      }
    });
    
    it('should get user notifications with pagination', async () => {
      const result = await notificationService.getUserNotifications(user._id, {
        page: 1,
        limit: 5
      });
      
      expect(result).toHaveProperty('notifications');
      expect(result).toHaveProperty('pagination');
      expect(result.notifications).toHaveLength(5);
      expect(result.pagination.total).toBe(10);
    });
    
    it('should filter by read status', async () => {
      const unreadResult = await notificationService.getUserNotifications(user._id, {
        read: false
      });
      
      expect(unreadResult.notifications.every(n => !n.read)).toBe(true);
      expect(unreadResult.notifications).toHaveLength(5);
    });
    
    it('should filter by type', async () => {
      await Notification.create({
        userId: user._id,
        type: 'promotion',
        title: 'Special Offer',
        body: 'Discount!'
      });
      
      const result = await notificationService.getUserNotifications(user._id, {
        type: 'promotion'
      });
      
      expect(result.notifications.every(n => n.type === 'promotion')).toBe(true);
    });
  });
  
  describe('markAsRead', () => {
    let user;
    let notifications;
    
    beforeEach(async () => {
      user = await User.create(TestDataFactory.generateUser());
      
      notifications = await Promise.all(
        Array(5).fill().map(() => 
          Notification.create({
            userId: user._id,
            type: 'system',
            title: 'Test',
            body: 'Content',
            read: false
          })
        )
      );
    });
    
    it('should mark single notification as read', async () => {
      const notification = notifications[0];
      
      await notificationService.markAsRead(notification._id, user._id);
      
      const updated = await Notification.findById(notification._id);
      expect(updated.read).toBe(true);
      expect(updated.readAt).toBeDefined();
    });
    
    it('should mark multiple notifications as read', async () => {
      const notificationIds = notifications.slice(0, 3).map(n => n._id);
      
      await notificationService.markAsRead(notificationIds, user._id);
      
      const updated = await Notification.find({ _id: { $in: notificationIds } });
      expect(updated.every(n => n.read)).toBe(true);
    });
    
    it('should mark all as read', async () => {
      await notificationService.markAllAsRead(user._id);
      
      const unreadCount = await Notification.countDocuments({
        userId: user._id,
        read: false
      });
      
      expect(unreadCount).toBe(0);
    });
  });
  
  describe('sendBulkNotification', () => {
    let users;
    
    beforeEach(async () => {
      users = await Promise.all(
        Array(10).fill().map(() => User.create(TestDataFactory.generateUser()))
      );
    });
    
    it('should send bulk notifications', async () => {
      const bulkData = {
        userIds: users.map(u => u._id),
        type: 'announcement',
        title: 'System Update',
        body: 'New features available!'
      };
      
      const result = await notificationService.sendBulkNotification(bulkData);
      
      expect(result).toHaveProperty('total', 10);
      expect(result).toHaveProperty('successful', 10);
      expect(result).toHaveProperty('failed', 0);
      
      // Verify notifications created
      const notifications = await Notification.find({ type: 'announcement' });
      expect(notifications).toHaveLength(10);
    });
    
    it('should handle rate limiting', async () => {
      const bulkData = {
        userIds: users.map(u => u._id),
        type: 'promotion',
        title: 'Limited Offer',
        body: '50% off!'
      };
      
      // Should throttle to rate limit
      const result = await notificationService.sendBulkNotification(bulkData, {
        rateLimit: 5 // 5 per second
      });
      
      expect(result.successful).toBeLessThanOrEqual(5);
    });
  });
});