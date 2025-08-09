/**
 * Notification System Tests
 * Tests multi-channel notifications (Database, Email, SMS, Discord, Slack, Push, Webhook)
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { SharedArray } from 'k6/data';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';

import { TEST_CONFIG, HEADERS } from '../../config/test-config.js';
import { AuthHelper, generateTestData, validators, dbHelpers } from '../../utils/helpers.js';

const notificationTypes = new SharedArray('notification-types', function() {
  return [
    { type: 'welcome', channels: ['database', 'email'] },
    { type: 'security_alert', channels: ['database', 'email', 'sms'] },
    { type: 'task_assignment', channels: ['database', 'slack', 'email'] },
    { type: 'system_maintenance', channels: ['database', 'email', 'discord'] },
    { type: 'marketing_campaign', channels: ['email', 'push'] },
    { type: 'order_shipped', channels: ['database', 'email', 'sms', 'webhook'] },
  ];
});

export let options = {
  scenarios: {
    send_notifications: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 10 },
        { duration: '2m', target: 15 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testSendNotifications',
    },
    notification_channels: {
      executor: 'constant-vus',
      vus: 12,
      duration: '3m',
      exec: 'testNotificationChannels',
    },
    notification_preferences: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 8 },
        { duration: '2m', target: 16 },
        { duration: '30s', target: 0 },
      ],
      exec: 'testNotificationPreferences',
    },
    bulk_notifications: {
      executor: 'constant-vus',
      vus: 6,
      duration: '2m',
      exec: 'testBulkNotifications',
    },
    notification_management: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 8 },
        { duration: '2m', target: 12 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testNotificationManagement',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<2500'], // Notifications can be slower
    http_req_failed: ['rate<0.05'],
    'http_req_duration{endpoint:notifications}': ['p(95)<2000'],
    'http_req_duration{endpoint:send-notification}': ['p(95)<3000'], // Sending can be slower
  },
};

export function setup() {
  console.log('📬 Setting up Notification System Tests');
  
  dbHelpers.setupTestDb(TEST_CONFIG.baseUrl);
  
  // Create authenticated user session
  const authHelper = new AuthHelper(TEST_CONFIG.baseUrl);
  const userToken = authHelper.loginJWT(
    TEST_CONFIG.auth.jwt.testUser.email,
    TEST_CONFIG.auth.jwt.testUser.password
  );
  const adminToken = authHelper.loginJWT(
    TEST_CONFIG.auth.jwt.adminUser.email,
    TEST_CONFIG.auth.jwt.adminUser.password
  );
  
  return { 
    baseUrl: TEST_CONFIG.baseUrl,
    userToken: userToken,
    adminToken: adminToken,
    notificationTypes: notificationTypes,
  };
}

export function testSendNotifications(data) {
  group('Send Notifications Tests', () => {
    const { baseUrl, adminToken, notificationTypes } = data;

    group('Send Single Notification', () => {
      const notificationData = {
        type: 'welcome',
        recipient_type: 'user',
        recipient_id: 1,
        channels: ['database', 'email'],
        data: {
          title: 'Welcome to Our Platform!',
          message: 'Thank you for joining us. Get started by exploring our features.',
          action_url: '/dashboard',
          priority: 'normal',
        },
        options: {
          send_immediately: true,
          track_opens: true,
          track_clicks: true,
        },
      };

      const response = http.post(`${baseUrl}/api/v1/notifications/send`, 
        JSON.stringify(notificationData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'send-notification', type: 'single' },
      });

      check(response, {
        'notification sent successfully': (r) => r.status === 200 || r.status === 201 || r.status === 202,
        'has notification ID': (r) => {
          if (r.status === 200 || r.status === 201 || r.status === 202) {
            const result = r.json();
            return result.hasOwnProperty('notification_id') || result.hasOwnProperty('id');
          }
          return true;
        },
        'channel results included': (r) => {
          if (r.status === 200 || r.status === 201 || r.status === 202) {
            const result = r.json();
            return result.hasOwnProperty('channels') || result.hasOwnProperty('results');
          }
          return true;
        },
      });
    });

    group('Send Notifications to Multiple Channels', () => {
      notificationTypes.forEach((notif, index) => {
        const notificationData = {
          type: notif.type,
          recipient_type: 'user',
          recipient_id: index + 1,
          channels: notif.channels,
          data: {
            title: `${notif.type} Notification ${index}`,
            message: `Test message for ${notif.type} notification`,
            action_url: `/notifications/${index}`,
          },
        };

        const response = http.post(`${baseUrl}/api/v1/notifications/send`, 
          JSON.stringify(notificationData), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'send-notification', type: notif.type, channels: notif.channels.length },
        });

        check(response, {
          [`${notif.type} notification processed`]: (r) => r.status === 200 || r.status === 201 || r.status === 202,
          [`${notif.type} channels handled`]: (r) => {
            if (r.status >= 200 && r.status < 300) {
              // Should handle all requested channels
              return true;
            }
            return r.status !== 500; // Should not crash
          },
        });
      });
    });

    group('Send with Template', () => {
      const templateData = {
        template: 'order_confirmation',
        recipient_type: 'user',
        recipient_id: 1,
        channels: ['database', 'email'],
        variables: {
          customer_name: 'John Doe',
          order_id: 'ORD-12345',
          order_total: '$99.99',
          items: ['Product A', 'Product B'],
        },
      };

      const response = http.post(`${baseUrl}/api/v1/notifications/send-template`, 
        JSON.stringify(templateData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'send-notification', type: 'template' },
      });

      check(response, {
        'template notification processed': (r) => r.status === 200 || r.status === 201 || r.status === 202 || r.status === 404,
        'template variables handled': (r) => {
          if (r.status >= 200 && r.status < 300) {
            return r.json().hasOwnProperty('notification_id') || r.json().hasOwnProperty('id');
          }
          return true;
        },
      });
    });

    group('Send with Scheduling', () => {
      const scheduledData = {
        type: 'marketing_campaign',
        recipient_type: 'users',
        recipient_ids: [1, 2, 3, 4, 5],
        channels: ['email'],
        data: {
          title: 'Special Offer Just for You!',
          message: 'Limited time offer - 50% off all products.',
          action_url: '/offers',
        },
        schedule: {
          send_at: new Date(Date.now() + 60000).toISOString(), // 1 minute from now
          timezone: 'UTC',
        },
      };

      const response = http.post(`${baseUrl}/api/v1/notifications/schedule`, 
        JSON.stringify(scheduledData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'send-notification', type: 'scheduled' },
      });

      check(response, {
        'scheduled notification created': (r) => r.status === 200 || r.status === 201 || r.status === 202,
        'schedule details included': (r) => {
          if (r.status >= 200 && r.status < 300) {
            const result = r.json();
            return result.hasOwnProperty('scheduled_id') || result.hasOwnProperty('send_at');
          }
          return true;
        },
      });
    });
  });
}

export function testNotificationChannels(data) {
  group('Notification Channels Tests', () => {
    const { baseUrl, adminToken } = data;

    group('Database Channel', () => {
      const databaseNotification = {
        type: 'system_alert',
        recipient_type: 'user',
        recipient_id: 1,
        channels: ['database'],
        data: {
          title: 'Database Test Notification',
          message: 'This notification is stored in the database.',
          metadata: {
            category: 'system',
            priority: 'high',
          },
        },
      };

      const response = http.post(`${baseUrl}/api/v1/notifications/send`, 
        JSON.stringify(databaseNotification), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'send-notification', channel: 'database' },
      });

      validators.apiResponse(response, 200, 201, 202);
    });

    group('Email Channel', () => {
      const emailNotification = {
        type: 'email_test',
        recipient_type: 'user',
        recipient_id: 1,
        channels: ['email'],
        data: {
          subject: 'Test Email Notification',
          body: 'This is a test email from k6 load testing.',
          from_name: 'Test System',
          reply_to: 'noreply@test.com',
        },
        options: {
          email_template: 'default',
          track_opens: true,
          track_clicks: true,
        },
      };

      const response = http.post(`${baseUrl}/api/v1/notifications/send`, 
        JSON.stringify(emailNotification), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'send-notification', channel: 'email' },
      });

      check(response, {
        'email notification processed': (r) => r.status === 200 || r.status === 201 || r.status === 202 || r.status === 400,
        'email channel result': (r) => {
          if (r.status >= 200 && r.status < 300) {
            const result = r.json();
            return result.hasOwnProperty('channels') || result.hasOwnProperty('results');
          }
          return true;
        },
      });
    });

    group('SMS Channel', () => {
      const smsNotification = {
        type: 'sms_test',
        recipient_type: 'user',
        recipient_id: 1,
        channels: ['sms'],
        data: {
          message: 'Test SMS from k6: Your verification code is 123456',
          phone_number: '+1234567890',
        },
        options: {
          sms_provider: 'twilio',
          country_code: 'US',
        },
      };

      const response = http.post(`${baseUrl}/api/v1/notifications/send`, 
        JSON.stringify(smsNotification), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'send-notification', channel: 'sms' },
      });

      check(response, {
        'SMS notification processed': (r) => r.status === 200 || r.status === 201 || r.status === 202 || r.status === 400,
        'SMS channel handling': (r) => r.status !== 500,
      });
    });

    group('Slack Channel', () => {
      const slackNotification = {
        type: 'slack_test',
        recipient_type: 'channel',
        recipient_id: 'general',
        channels: ['slack'],
        data: {
          message: 'K6 load test notification to Slack!',
          channel: '#general',
          username: 'K6 Bot',
          icon_emoji: ':robot_face:',
          attachments: [{
            color: 'good',
            title: 'Load Test Status',
            text: 'All systems operational',
          }],
        },
      };

      const response = http.post(`${baseUrl}/api/v1/notifications/send`, 
        JSON.stringify(slackNotification), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'send-notification', channel: 'slack' },
      });

      check(response, {
        'Slack notification processed': (r) => r.status === 200 || r.status === 201 || r.status === 202 || r.status === 400,
      });
    });

    group('Discord Channel', () => {
      const discordNotification = {
        type: 'discord_test',
        recipient_type: 'channel',
        recipient_id: '123456789',
        channels: ['discord'],
        data: {
          content: 'K6 load test notification to Discord!',
          embeds: [{
            title: 'Load Test Notification',
            description: 'Testing Discord integration',
            color: 3447003, // Blue
            timestamp: new Date().toISOString(),
          }],
        },
      };

      const response = http.post(`${baseUrl}/api/v1/notifications/send`, 
        JSON.stringify(discordNotification), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'send-notification', channel: 'discord' },
      });

      check(response, {
        'Discord notification processed': (r) => r.status === 200 || r.status === 201 || r.status === 202 || r.status === 400,
      });
    });

    group('Push Notification Channel', () => {
      const pushNotification = {
        type: 'push_test',
        recipient_type: 'user',
        recipient_id: 1,
        channels: ['push'],
        data: {
          title: 'K6 Test Push Notification',
          body: 'This is a test push notification from k6',
          icon: '/icon-192x192.png',
          badge: '/badge-72x72.png',
          actions: [{
            action: 'view',
            title: 'View Details',
            icon: '/view-icon.png',
          }],
        },
        options: {
          ttl: 3600, // 1 hour
          priority: 'high',
        },
      };

      const response = http.post(`${baseUrl}/api/v1/notifications/send`, 
        JSON.stringify(pushNotification), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'send-notification', channel: 'push' },
      });

      check(response, {
        'push notification processed': (r) => r.status === 200 || r.status === 201 || r.status === 202 || r.status === 400,
      });
    });

    group('Webhook Channel', () => {
      const webhookNotification = {
        type: 'webhook_test',
        recipient_type: 'webhook',
        recipient_id: 'order_webhook',
        channels: ['webhook'],
        data: {
          webhook_url: 'https://httpbin.org/post',
          payload: {
            event: 'k6_test',
            data: {
              message: 'K6 webhook test notification',
              timestamp: new Date().toISOString(),
            },
          },
          headers: {
            'X-Event-Type': 'k6-test',
            'X-Source': 'notification-system',
          },
        },
        options: {
          timeout: 10000,
          retry_attempts: 2,
        },
      };

      const response = http.post(`${baseUrl}/api/v1/notifications/send`, 
        JSON.stringify(webhookNotification), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'send-notification', channel: 'webhook' },
      });

      check(response, {
        'webhook notification processed': (r) => r.status === 200 || r.status === 201 || r.status === 202 || r.status === 400,
      });
    });
  });
}

export function testNotificationPreferences(data) {
  group('Notification Preferences Tests', () => {
    const { baseUrl, userToken } = data;

    group('Get User Preferences', () => {
      const response = http.get(`${baseUrl}/api/v1/notifications/preferences`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'notification-preferences', action: 'get' },
      });

      validators.apiResponse(response, 200);
      
      if (response.status === 200) {
        check(response, {
          'preferences structure valid': (r) => {
            const prefs = r.json().data;
            return prefs.hasOwnProperty('channels') || prefs.hasOwnProperty('types');
          },
        });
      }
    });

    group('Update User Preferences', () => {
      const preferences = {
        channels: {
          email: {
            enabled: true,
            types: ['welcome', 'security_alert', 'order_shipped'],
          },
          sms: {
            enabled: true,
            types: ['security_alert'],
          },
          push: {
            enabled: false,
            types: [],
          },
          database: {
            enabled: true,
            types: ['all'],
          },
        },
        general: {
          frequency: 'immediate',
          quiet_hours: {
            enabled: true,
            start: '22:00',
            end: '08:00',
            timezone: 'UTC',
          },
        },
      };

      const response = http.put(`${baseUrl}/api/v1/notifications/preferences`, 
        JSON.stringify(preferences), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'notification-preferences', action: 'update' },
      });

      validators.apiResponse(response, 200);
      
      if (response.status === 200) {
        check(response, {
          'preferences updated': (r) => {
            const result = r.json();
            return result.hasOwnProperty('message') || result.hasOwnProperty('data');
          },
        });
      }
    });

    group('Channel-Specific Preferences', () => {
      const channelPrefs = [
        { channel: 'email', settings: { digest: 'daily', format: 'html' } },
        { channel: 'sms', settings: { country_code: '+1', opt_in_confirmed: true } },
        { channel: 'push', settings: { sound: 'default', vibrate: true } },
      ];

      channelPrefs.forEach(({ channel, settings }) => {
        const response = http.put(`${baseUrl}/api/v1/notifications/preferences/${channel}`, 
          JSON.stringify(settings), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'notification-preferences', channel: channel },
        });

        check(response, {
          [`${channel} preferences updated`]: (r) => r.status === 200 || r.status === 404,
        });
      });
    });

    group('Unsubscribe Features', () => {
      // Test unsubscribe from specific notification types
      const unsubscribeData = {
        types: ['marketing_campaign', 'newsletter'],
        channels: ['email'],
      };

      const response = http.post(`${baseUrl}/api/v1/notifications/unsubscribe`, 
        JSON.stringify(unsubscribeData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'notifications', action: 'unsubscribe' },
      });

      check(response, {
        'unsubscribe processed': (r) => r.status === 200 || r.status === 201,
        'unsubscribe confirmation': (r) => {
          if (r.status === 200 || r.status === 201) {
            return r.json().hasOwnProperty('message') || r.json().hasOwnProperty('unsubscribed');
          }
          return true;
        },
      });
    });
  });
}

export function testBulkNotifications(data) {
  group('Bulk Notifications Tests', () => {
    const { baseUrl, adminToken } = data;

    group('Send Bulk Notifications', () => {
      const bulkData = {
        type: 'system_announcement',
        recipient_type: 'users',
        recipient_ids: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        channels: ['database', 'email'],
        data: {
          title: 'System Maintenance Announcement',
          message: 'Scheduled maintenance will occur tonight from 2 AM to 4 AM UTC.',
          priority: 'high',
        },
        options: {
          batch_size: 5,
          delay_between_batches: 1000, // 1 second
        },
      };

      const response = http.post(`${baseUrl}/api/v1/notifications/bulk-send`, 
        JSON.stringify(bulkData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'notifications', action: 'bulk-send' },
      });

      check(response, {
        'bulk notification initiated': (r) => r.status === 200 || r.status === 201 || r.status === 202,
        'bulk processing details': (r) => {
          if (r.status >= 200 && r.status < 300) {
            const result = r.json();
            return result.hasOwnProperty('batch_id') || 
                   result.hasOwnProperty('total_recipients') ||
                   result.hasOwnProperty('queued');
          }
          return true;
        },
      });
    });

    group('Segment-Based Notifications', () => {
      const segmentData = {
        type: 'targeted_campaign',
        segment: {
          criteria: {
            user_type: 'premium',
            last_login: '7_days_ago',
            location: 'US',
          },
          estimated_count: 50,
        },
        channels: ['email', 'push'],
        data: {
          title: 'Exclusive Premium Member Offer!',
          message: 'Special discount just for our premium members.',
          action_url: '/premium-offers',
        },
        options: {
          test_mode: true, // For k6 testing
          max_recipients: 20,
        },
      };

      const response = http.post(`${baseUrl}/api/v1/notifications/send-segment`, 
        JSON.stringify(segmentData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'notifications', action: 'segment-send' },
      });

      check(response, {
        'segment notification processed': (r) => r.status === 200 || r.status === 201 || r.status === 202 || r.status === 400,
        'segment results': (r) => {
          if (r.status >= 200 && r.status < 300) {
            const result = r.json();
            return result.hasOwnProperty('segment_size') || result.hasOwnProperty('queued');
          }
          return true;
        },
      });
    });

    group('Bulk Status Check', () => {
      // Check status of bulk operations
      const statusResponse = http.get(`${baseUrl}/api/v1/notifications/bulk-status`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'notifications', action: 'bulk-status' },
      });

      check(statusResponse, {
        'bulk status available': (r) => r.status === 200 || r.status === 404,
        'status information': (r) => {
          if (r.status === 200) {
            const status = r.json().data;
            return Array.isArray(status) || typeof status === 'object';
          }
          return true;
        },
      });
    });
  });
}

export function testNotificationManagement(data) {
  group('Notification Management Tests', () => {
    const { baseUrl, userToken } = data;

    group('List User Notifications', () => {
      const response = http.get(`${baseUrl}/api/v1/notifications?page=1&per_page=20`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'notifications', action: 'list' },
      });

      validators.paginatedResponse(response);
      
      if (response.status === 200) {
        check(response, {
          'notifications list structure': (r) => {
            const notifications = r.json().data;
            return Array.isArray(notifications);
          },
          'notification data format': (r) => {
            const notifications = r.json().data;
            if (notifications.length > 0) {
              const notif = notifications[0];
              return notif.hasOwnProperty('id') && 
                     notif.hasOwnProperty('type') &&
                     notif.hasOwnProperty('created_at');
            }
            return true;
          },
        });
      }
    });

    group('Mark Notifications as Read', () => {
      // Mark single notification as read
      const markReadResponse = http.put(`${baseUrl}/api/v1/notifications/1/read`, {}, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'notifications', action: 'mark-read' },
      });

      check(markReadResponse, {
        'mark read processed': (r) => r.status === 200 || r.status === 404,
      });

      // Mark multiple notifications as read
      const bulkReadData = {
        notification_ids: [1, 2, 3, 4, 5],
      };

      const bulkReadResponse = http.put(`${baseUrl}/api/v1/notifications/bulk-read`, 
        JSON.stringify(bulkReadData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'notifications', action: 'bulk-read' },
      });

      check(bulkReadResponse, {
        'bulk read processed': (r) => r.status === 200 || r.status === 404,
      });

      // Mark all as read
      const readAllResponse = http.put(`${baseUrl}/api/v1/notifications/read-all`, {}, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'notifications', action: 'read-all' },
      });

      check(readAllResponse, {
        'read all processed': (r) => r.status === 200,
      });
    });

    group('Delete Notifications', () => {
      // Delete single notification
      const deleteResponse = http.del(`${baseUrl}/api/v1/notifications/1`, null, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'notifications', action: 'delete' },
      });

      check(deleteResponse, {
        'delete processed': (r) => r.status === 200 || r.status === 404,
      });

      // Bulk delete
      const bulkDeleteData = {
        notification_ids: [2, 3, 4],
        older_than_days: 30,
      };

      const bulkDeleteResponse = http.delete(`${baseUrl}/api/v1/notifications/bulk-delete`, 
        JSON.stringify(bulkDeleteData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'notifications', action: 'bulk-delete' },
      });

      check(bulkDeleteResponse, {
        'bulk delete processed': (r) => r.status === 200 || r.status === 404,
      });
    });

    group('Notification Analytics', () => {
      const analyticsResponse = http.get(`${baseUrl}/api/v1/notifications/analytics`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'notifications', action: 'analytics' },
      });

      check(analyticsResponse, {
        'analytics available': (r) => r.status === 200 || r.status === 403,
        'analytics data structure': (r) => {
          if (r.status === 200) {
            const analytics = r.json().data;
            return typeof analytics === 'object';
          }
          return true;
        },
      });
    });

    group('Notification Templates', () => {
      // List available templates
      const templatesResponse = http.get(`${baseUrl}/api/v1/notifications/templates`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'notification-templates', action: 'list' },
      });

      check(templatesResponse, {
        'templates listed': (r) => r.status === 200 || r.status === 403 || r.status === 404,
        'templates format': (r) => {
          if (r.status === 200) {
            const templates = r.json().data;
            return Array.isArray(templates);
          }
          return true;
        },
      });
    });
  });
}

export function teardown(data) {
  console.log('🧹 Cleaning up Notification System Tests');
  dbHelpers.cleanTestDb(data.baseUrl);
}

export function handleSummary(data) {
  return {
    'k6-tests/results/notifications-test.html': htmlReport(data),
    'k6-tests/results/notifications-test.json': JSON.stringify(data),
  };
}