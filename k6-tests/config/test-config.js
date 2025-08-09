/**
 * K6 Test Configuration
 * Global configuration for k6 load testing
 */

export const BASE_URL = __ENV.BASE_URL || __ENV.K6_BASE_URL || 'http://localhost:8001';
export const TEST_DB_URL = __ENV.TEST_DB_URL || __ENV.K6_TEST_DB_URL || 'postgresql://postgres:k6_test_password@localhost:5433/test_k6_db';

export const TEST_CONFIG = {
  // Test environment settings
  baseUrl: BASE_URL,
  testDbUrl: TEST_DB_URL,
  
  // Default test options
  defaultOptions: {
    stages: [
      { duration: '30s', target: 5 },   // Ramp up
      { duration: '1m', target: 10 },   // Stay at 10 users
      { duration: '30s', target: 0 },   // Ramp down
    ],
    thresholds: {
      http_req_duration: ['p(95)<2000'], // 95% of requests must complete below 2s
      http_req_failed: ['rate<0.05'],    // Error rate must be below 5%
    },
  },

  // Load test scenarios
  scenarios: {
    light: {
      stages: [
        { duration: '1m', target: 5 },
        { duration: '2m', target: 5 },
        { duration: '1m', target: 0 },
      ],
    },
    normal: {
      stages: [
        { duration: '2m', target: 20 },
        { duration: '5m', target: 20 },
        { duration: '2m', target: 0 },
      ],
    },
    stress: {
      stages: [
        { duration: '2m', target: 100 },
        { duration: '5m', target: 100 },
        { duration: '2m', target: 200 },
        { duration: '5m', target: 200 },
        { duration: '10m', target: 0 },
      ],
    },
    spike: {
      stages: [
        { duration: '10s', target: 100 },
        { duration: '1m', target: 100 },
        { duration: '10s', target: 1400 },
        { duration: '3m', target: 1400 },
        { duration: '10s', target: 100 },
        { duration: '3m', target: 100 },
        { duration: '10s', target: 0 },
      ],
    },
  },

  // Authentication config
  auth: {
    jwt: {
      testUser: {
        email: __ENV.K6_TEST_USER_EMAIL || 'test@example.com',
        password: __ENV.K6_TEST_USER_PASSWORD || 'password123',
      },
      adminUser: {
        email: __ENV.K6_ADMIN_USER_EMAIL || 'admin@example.com', 
        password: __ENV.K6_ADMIN_USER_PASSWORD || 'admin123',
      },
    },
    oauth2: {
      client: {
        id: __ENV.K6_OAUTH2_CLIENT_ID || 'test-client-id',
        secret: __ENV.K6_OAUTH2_CLIENT_SECRET || 'test-client-secret',
      },
      confidential: {
        id: __ENV.K6_OAUTH2_CONFIDENTIAL_ID || 'confidential-client',
        secret: __ENV.K6_OAUTH2_CONFIDENTIAL_SECRET || 'confidential-secret',
      },
      scopes: ['read', 'write', 'admin'],
    },
  },

  // Test data configurations
  testData: {
    users: {
      count: parseInt(__ENV.K6_TEST_USERS_COUNT) || 100,
      roles: ['user', 'admin', 'moderator'],
    },
    posts: {
      count: parseInt(__ENV.K6_TEST_POSTS_COUNT) || 500,
      categories: ['tech', 'news', 'lifestyle', 'sports'],
    },
    notifications: {
      count: parseInt(__ENV.K6_TEST_NOTIFICATIONS_COUNT) || 200,
      types: ['email', 'sms', 'push', 'database'],
      channels: ['email', 'database', 'slack', 'discord'],
    },
    organizations: {
      count: parseInt(__ENV.K6_TEST_ORGANIZATIONS_COUNT) || 20,
    },
  },

  // Rate limiting thresholds
  rateLimits: {
    auth: {
      requests: 10,
      window: 60, // seconds
    },
    api: {
      requests: 100,
      window: 60,
    },
    oauth2: {
      requests: 50,
      window: 60,
    },
  },
};

export const HEADERS = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'User-Agent': 'k6-test-suite/1.0',
};

export const FORM_HEADERS = {
  'Content-Type': 'application/x-www-form-urlencoded',
  'Accept': 'application/json',
};