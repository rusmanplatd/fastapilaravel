/**
 * K6 Test Utilities and Helpers
 * Common functions used across all test suites
 */

import http from 'k6/http';
import { check, fail } from 'k6';
import { Trend } from 'k6/metrics';
import ws from 'k6/ws';
import { randomIntBetween, randomString } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

/**
 * Generate random test data
 */
export const generateTestData = {
  user: () => ({
    name: `User ${randomString(8)}`,
    email: `user${randomIntBetween(1, 10000)}@example.com`,
    password: 'password123',
    phone: `+1${randomIntBetween(1000000000, 9999999999)}`,
  }),

  post: () => ({
    title: `Test Post ${randomString(10)}`,
    content: `This is test content ${randomString(50)}`,
    category: ['tech', 'news', 'lifestyle'][randomIntBetween(0, 2)],
    status: 'published',
  }),

  organization: () => ({
    name: `Test Org ${randomString(8)}`,
    description: `Test organization description ${randomString(20)}`,
    industry: ['tech', 'finance', 'healthcare'][randomIntBetween(0, 2)],
  }),

  oauth2Client: () => ({
    name: `OAuth2 Client ${randomString(8)}`,
    redirect_uris: [`https://example${randomIntBetween(1, 100)}.com/callback`],
    scopes: ['read', 'write'],
    grant_types: ['authorization_code', 'refresh_token'],
  }),
};

/**
 * Authentication helpers
 */
export class AuthHelper {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this.tokens = new Map();
  }

  /**
   * Login with JWT and store token
   */
  loginJWT(email, password) {
    const response = http.post(`${this.baseUrl}/api/v1/auth/login`, 
      JSON.stringify({ email, password }), 
      { headers: { 'Content-Type': 'application/json' } }
    );

    if (check(response, { 'JWT login successful': (r) => r.status === 200 })) {
      const token = response.json('access_token');
      this.tokens.set('jwt', token);
      return token;
    }
    fail('JWT login failed');
  }

  /**
   * Get OAuth2 access token using client credentials
   */
  getOAuth2Token(clientId, clientSecret, scopes = 'read write') {
    const response = http.post(`${this.baseUrl}/oauth/token`, {
      grant_type: 'client_credentials',
      client_id: clientId,
      client_secret: clientSecret,
      scope: scopes,
    }, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });

    if (check(response, { 'OAuth2 token obtained': (r) => r.status === 200 })) {
      const token = response.json('access_token');
      this.tokens.set('oauth2', token);
      return token;
    }
    fail('OAuth2 token request failed');
  }

  /**
   * Get authorization headers for JWT
   */
  getJWTHeaders() {
    const token = this.tokens.get('jwt');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  /**
   * Get authorization headers for OAuth2
   */
  getOAuth2Headers() {
    const token = this.tokens.get('oauth2');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }
}

/**
 * Database test helpers
 */
export const dbHelpers = {
  /**
   * Setup fresh test database
   */
  setupTestDb: (baseUrl) => {
    const response = http.post(`${baseUrl}/test/db/setup`, {}, {
      headers: { 'Content-Type': 'application/json' }
    });
    
    check(response, { 
      'Test DB setup successful': (r) => r.status === 200 
    }) || fail('Failed to setup test database');
    
    return response;
  },

  /**
   * Seed test data
   */
  seedTestData: (baseUrl) => {
    const response = http.post(`${baseUrl}/test/db/seed`, {}, {
      headers: { 'Content-Type': 'application/json' }
    });
    
    check(response, { 
      'Test data seeded successfully': (r) => r.status === 200 
    }) || fail('Failed to seed test data');
    
    return response;
  },

  /**
   * Clean test database
   */
  cleanTestDb: (baseUrl) => {
    const response = http.delete(`${baseUrl}/test/db/clean`, {}, {
      headers: { 'Content-Type': 'application/json' }
    });
    
    check(response, { 
      'Test DB cleaned successfully': (r) => r.status === 200 
    }) || fail('Failed to clean test database');
    
    return response;
  },
};

/**
 * Response validation helpers
 */
export const validators = {
  /**
   * Validate standard API response structure
   */
  apiResponse: (response, expectedStatus = 200) => {
    return check(response, {
      [`Status is ${expectedStatus}`]: (r) => r.status === expectedStatus,
      'Response has data field': (r) => r.json().hasOwnProperty('data') || r.json().hasOwnProperty('message'),
      'Response time < 2s': (r) => r.timings.duration < 2000,
    });
  },

  /**
   * Validate paginated response
   */
  paginatedResponse: (response) => {
    return check(response, {
      'Status is 200': (r) => r.status === 200,
      'Has data array': (r) => Array.isArray(r.json().data),
      'Has pagination meta': (r) => r.json().hasOwnProperty('meta'),
      'Has links': (r) => r.json().hasOwnProperty('links'),
    });
  },

  /**
   * Validate OAuth2 token response
   */
  oauth2TokenResponse: (response) => {
    return check(response, {
      'Status is 200': (r) => r.status === 200,
      'Has access_token': (r) => r.json().hasOwnProperty('access_token'),
      'Has token_type': (r) => r.json().hasOwnProperty('token_type'),
      'Has expires_in': (r) => r.json().hasOwnProperty('expires_in'),
      'Token type is Bearer': (r) => r.json().token_type === 'Bearer',
    });
  },

  /**
   * Validate error response
   */
  errorResponse: (response, expectedStatus) => {
    return check(response, {
      [`Status is ${expectedStatus}`]: (r) => r.status === expectedStatus,
      'Has error field': (r) => r.json().hasOwnProperty('error') || r.json().hasOwnProperty('detail'),
      'Response time < 1s': (r) => r.timings.duration < 1000,
    });
  },
};

/**
 * Performance monitoring helpers
 */
export const performance = {
  /**
   * Track custom metrics
   */
  trackMetric: (name, value, tags = {}) => {
    const trend = new Trend(name);
    trend.add(value, tags);
  },

  /**
   * Performance thresholds for different endpoints
   */
  thresholds: {
    auth: {
      http_req_duration: ['p(95)<1000'], // Auth should be fast
      http_req_failed: ['rate<0.01'],    // Very low error rate
    },
    api: {
      http_req_duration: ['p(95)<2000'], // Standard API response time
      http_req_failed: ['rate<0.05'],    // 5% error tolerance
    },
    uploads: {
      http_req_duration: ['p(95)<5000'], // File uploads can be slower
      http_req_failed: ['rate<0.02'],    // Low error rate for uploads
    },
  },
};

/**
 * Test scenario builders
 */
export const scenarios = {
  /**
   * Build a user journey scenario
   */
  userJourney: (name, stages, exec) => ({
    [name]: {
      executor: 'ramping-vus',
      stages: stages,
      exec: exec,
    },
  }),

  /**
   * Build a constant rate scenario
   */
  constantRate: (name, rate, duration, exec) => ({
    [name]: {
      executor: 'constant-arrival-rate',
      rate: rate,
      timeUnit: '1s',
      duration: duration,
      preAllocatedVUs: 10,
      exec: exec,
    },
  }),
};

/**
 * File upload helpers
 */
export const fileHelpers = {
  /**
   * Generate test file data
   */
  generateTestFile: (filename, content, mimetype = 'text/plain') => {
    return {
      filename: filename,
      data: content,
      content_type: mimetype,
    };
  },

  /**
   * Generate test image data (base64)
   */
  generateTestImage: () => {
    // Simple 1x1 pixel PNG in base64
    const pngData = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
    return {
      filename: 'test.png',
      data: pngData,
      content_type: 'image/png',
    };
  },
};

/**
 * WebSocket helpers
 */
export const wsHelpers = {
  /**
   * Connect to WebSocket with authentication
   */
  connectWithAuth: (url, token) => {
    const headers = {
      'Authorization': `Bearer ${token}`,
    };
    return ws.connect(url, null, { headers });
  },

  /**
   * Send and wait for WebSocket message
   */
  sendAndWait: (socket, message, timeout = 5000) => {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error('WebSocket response timeout'));
      }, timeout);

      socket.onmessage = (event) => {
        clearTimeout(timer);
        resolve(JSON.parse(event.data));
      };

      socket.send(JSON.stringify(message));
    });
  },
};