/**
 * JWT Authentication Tests
 * Comprehensive testing of JWT authentication endpoints
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { SharedArray } from 'k6/data';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';

import { TEST_CONFIG, HEADERS } from '../../config/test-config.js';
import { AuthHelper, generateTestData, validators, dbHelpers } from '../../utils/helpers.js';

const testUsers = new SharedArray('test-users', function() {
  const users = [];
  for (let i = 0; i < 50; i++) {
    users.push(generateTestData.user());
  }
  return users;
});

export let options = {
  scenarios: {
    jwt_login: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 10 },
        { duration: '3m', target: 20 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testJWTLogin',
    },
    jwt_protected_routes: {
      executor: 'ramping-vus', 
      stages: [
        { duration: '2m', target: 15 },
        { duration: '3m', target: 15 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testProtectedRoutes',
    },
    jwt_token_refresh: {
      executor: 'constant-vus',
      vus: 5,
      duration: '2m',
      exec: 'testTokenRefresh',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<1000'], // 95% of requests must complete below 1s
    http_req_failed: ['rate<0.05'],    // Error rate must be below 5%
    'http_req_duration{endpoint:login}': ['p(95)<500'],
    'http_req_duration{endpoint:me}': ['p(95)<300'],
  },
};

export function setup() {
  console.log('🧪 Setting up JWT Authentication Tests');
  
  // Setup test database
  dbHelpers.setupTestDb(TEST_CONFIG.baseUrl);
  
  return { baseUrl: TEST_CONFIG.baseUrl };
}

export function testJWTLogin(data) {
  group('JWT Login Tests', () => {
    const { baseUrl } = data;
    
    group('Valid Login', () => {
      const response = http.post(`${baseUrl}/api/v1/auth/login`, JSON.stringify({
        email: TEST_CONFIG.auth.jwt.testUser.email,
        password: TEST_CONFIG.auth.jwt.testUser.password,
      }), {
        headers: HEADERS,
        tags: { endpoint: 'login' },
      });

      check(response, {
        'login status is 200': (r) => r.status === 200,
        'has access_token': (r) => r.json().hasOwnProperty('access_token'),
        'has token_type': (r) => r.json().hasOwnProperty('token_type'),
        'has expires_in': (r) => r.json().hasOwnProperty('expires_in'),
        'token_type is Bearer': (r) => r.json().token_type === 'Bearer',
        'response time < 500ms': (r) => r.timings.duration < 500,
      });
    });

    group('Invalid Credentials', () => {
      const response = http.post(`${baseUrl}/api/v1/auth/login`, JSON.stringify({
        email: TEST_CONFIG.auth.jwt.testUser.email,
        password: 'wrongpassword',
      }), {
        headers: HEADERS,
        tags: { endpoint: 'login' },
      });

      validators.errorResponse(response, 401);
    });

    group('Missing Fields', () => {
      const response = http.post(`${baseUrl}/api/v1/auth/login`, JSON.stringify({
        email: TEST_CONFIG.auth.jwt.testUser.email,
        // missing password
      }), {
        headers: HEADERS,
        tags: { endpoint: 'login' },
      });

      validators.errorResponse(response, 422);
    });

    group('Rate Limiting', () => {
      // Test rate limiting with multiple rapid requests
      const responses = [];
      for (let i = 0; i < 15; i++) { // Exceed rate limit
        const response = http.post(`${baseUrl}/api/v1/auth/login`, JSON.stringify({
          email: 'test@ratelimit.com',
          password: 'password123',
        }), {
          headers: HEADERS,
          tags: { endpoint: 'login' },
        });
        responses.push(response);
      }

      // At least one request should be rate limited
      const rateLimitedCount = responses.filter(r => r.status === 429).length;
      check({ rateLimitedCount }, {
        'rate limiting triggered': (data) => data.rateLimitedCount > 0,
      });
    });
  });
}

export function testProtectedRoutes(data) {
  group('Protected Routes Tests', () => {
    const { baseUrl } = data;
    const authHelper = new AuthHelper(baseUrl);

    // Login to get token
    const token = authHelper.loginJWT(
      TEST_CONFIG.auth.jwt.testUser.email,
      TEST_CONFIG.auth.jwt.testUser.password
    );

    group('Access with Valid Token', () => {
      const response = http.get(`${baseUrl}/api/v1/auth/me`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${token}`,
        },
        tags: { endpoint: 'me' },
      });

      check(response, {
        'me status is 200': (r) => r.status === 200,
        'has user data': (r) => r.json().hasOwnProperty('data'),
        'has user email': (r) => r.json().data.hasOwnProperty('email'),
        'response time < 300ms': (r) => r.timings.duration < 300,
      });
    });

    group('Access without Token', () => {
      const response = http.get(`${baseUrl}/api/v1/auth/me`, {
        headers: HEADERS,
        tags: { endpoint: 'me' },
      });

      validators.errorResponse(response, 401);
    });

    group('Access with Invalid Token', () => {
      const response = http.get(`${baseUrl}/api/v1/auth/me`, {
        headers: {
          ...HEADERS,
          'Authorization': 'Bearer invalid.token.here',
        },
        tags: { endpoint: 'me' },
      });

      validators.errorResponse(response, 401);
    });

    group('User Profile Update', () => {
      const updateData = {
        name: 'Updated Test User',
        phone: '+1234567890',
      };

      const response = http.put(`${baseUrl}/api/v1/users/me`, JSON.stringify(updateData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${token}`,
        },
        tags: { endpoint: 'update_profile' },
      });

      validators.apiResponse(response, 200);
    });
  });
}

export function testTokenRefresh(data) {
  group('Token Refresh Tests', () => {
    const { baseUrl } = data;

    group('Refresh Valid Token', () => {
      // First login to get initial token
      const loginResponse = http.post(`${baseUrl}/api/v1/auth/login`, JSON.stringify({
        email: TEST_CONFIG.auth.jwt.testUser.email,
        password: TEST_CONFIG.auth.jwt.testUser.password,
      }), { headers: HEADERS });

      if (loginResponse.status === 200) {
        const token = loginResponse.json().access_token;

        // Attempt to refresh token
        const refreshResponse = http.post(`${baseUrl}/api/v1/auth/refresh`, {}, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${token}`,
          },
          tags: { endpoint: 'refresh' },
        });

        check(refreshResponse, {
          'refresh status is 200': (r) => r.status === 200,
          'has new access_token': (r) => r.json().hasOwnProperty('access_token'),
          'new token is different': (r) => r.json().access_token !== token,
        });
      }
    });

    group('Refresh Invalid Token', () => {
      const response = http.post(`${baseUrl}/api/v1/auth/refresh`, {}, {
        headers: {
          ...HEADERS,
          'Authorization': 'Bearer invalid.token',
        },
        tags: { endpoint: 'refresh' },
      });

      validators.errorResponse(response, 401);
    });
  });
}

export function teardown(data) {
  console.log('🧹 Cleaning up JWT Authentication Tests');
  dbHelpers.cleanTestDb(data.baseUrl);
}

export function handleSummary(data) {
  return {
    'k6-tests/results/jwt-auth-test.html': htmlReport(data),
    'k6-tests/results/jwt-auth-test.json': JSON.stringify(data),
  };
}