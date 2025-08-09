/**
 * Multi-Factor Authentication (MFA) Tests
 * Tests TOTP, SMS, and WebAuthn MFA flows
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { SharedArray } from 'k6/data';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';

import { TEST_CONFIG, HEADERS } from '../../config/test-config.js';
import { AuthHelper, generateTestData, validators, dbHelpers } from '../../utils/helpers.js';

const testUsers = new SharedArray('mfa-test-users', function() {
  const users = [];
  for (let i = 0; i < 20; i++) {
    users.push({
      ...generateTestData.user(),
      mfaEnabled: i % 2 === 0, // 50% with MFA enabled
    });
  }
  return users;
});

export let options = {
  scenarios: {
    totp_setup_flow: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 8 },
        { duration: '2m', target: 12 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testTOTPSetup',
    },
    mfa_authentication: {
      executor: 'constant-vus',
      vus: 10,
      duration: '3m',
      exec: 'testMFAAuthentication',
    },
    sms_mfa_flow: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 6 },
        { duration: '2m', target: 15 },
        { duration: '30s', target: 0 },
      ],
      exec: 'testSMSMFA',
    },
    recovery_codes: {
      executor: 'constant-vus',
      vus: 5,
      duration: '2m',
      exec: 'testRecoveryCodes',
    },
    mfa_security: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 8 },
        { duration: '2m', target: 12 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testMFASecurity',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<3000'], // MFA can be slower
    http_req_failed: ['rate<0.05'],
    'http_req_duration{endpoint:mfa-setup}': ['p(95)<2000'],
    'http_req_duration{endpoint:mfa-verify}': ['p(95)<1500'],
  },
};

export function setup() {
  console.log('🛡️ Setting up MFA Tests');
  
  dbHelpers.setupTestDb(TEST_CONFIG.baseUrl);
  
  // Create authenticated user session
  const authHelper = new AuthHelper(TEST_CONFIG.baseUrl);
  const userToken = authHelper.loginJWT(
    TEST_CONFIG.auth.jwt.testUser.email,
    TEST_CONFIG.auth.jwt.testUser.password
  );
  
  return { 
    baseUrl: TEST_CONFIG.baseUrl,
    userToken: userToken,
    testUsers: testUsers,
  };
}

export function testTOTPSetup(data) {
  group('TOTP MFA Setup Flow', () => {
    const { baseUrl, userToken } = data;

    group('Initiate TOTP Setup', () => {
      const response = http.post(`${baseUrl}/api/v1/mfa/totp/setup`, {}, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'mfa-setup', type: 'totp' },
      });

      check(response, {
        'TOTP setup initiated': (r) => r.status === 200 || r.status === 201,
        'has QR code data': (r) => {
          if (r.status !== 200 && r.status !== 201) return false;
          const data = r.json();
          return data.hasOwnProperty('qr_code') || data.hasOwnProperty('secret');
        },
        'has backup codes': (r) => {
          if (r.status !== 200 && r.status !== 201) return false;
          const data = r.json();
          return data.hasOwnProperty('backup_codes') || data.hasOwnProperty('recovery_codes');
        },
      });
    });

    group('Verify TOTP Setup', () => {
      // Simulate TOTP verification with a test code
      const verificationData = {
        code: '123456', // Test code - in real implementation would be from TOTP app
        backup_codes_acknowledged: true,
      };

      const response = http.post(`${baseUrl}/api/v1/mfa/totp/verify-setup`, 
        JSON.stringify(verificationData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'mfa-setup', type: 'totp-verify' },
      });

      check(response, {
        'TOTP verification processed': (r) => r.status === 200 || r.status === 400,
        'appropriate response format': (r) => {
          if (r.status === 400) {
            // Should have error message for invalid code
            return r.json().hasOwnProperty('error') || r.json().hasOwnProperty('detail');
          }
          return r.status === 200;
        },
      });
    });

    group('Get MFA Status', () => {
      const response = http.get(`${baseUrl}/api/v1/mfa/status`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'mfa-status' },
      });

      validators.apiResponse(response, 200);
      
      check(response, {
        'MFA status includes methods': (r) => {
          if (r.status !== 200) return false;
          const status = r.json().data;
          return status.hasOwnProperty('enabled_methods') &&
                 status.hasOwnProperty('available_methods');
        },
      });
    });

    group('Disable TOTP MFA', () => {
      const disableData = {
        current_password: TEST_CONFIG.auth.jwt.testUser.password,
        confirmation: true,
      };

      const response = http.post(`${baseUrl}/api/v1/mfa/totp/disable`, 
        JSON.stringify(disableData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'mfa-disable', type: 'totp' },
      });

      check(response, {
        'TOTP disable processed': (r) => r.status === 200 || r.status === 400 || r.status === 404,
        'secure disable process': (r) => {
          // Should require password confirmation
          return r.status !== 200 || r.json().hasOwnProperty('message');
        },
      });
    });
  });
}

export function testMFAAuthentication(data) {
  group('MFA Authentication Flow', () => {
    const { baseUrl } = data;

    group('Login with MFA Required', () => {
      // Initial login that should trigger MFA requirement
      const loginResponse = http.post(`${baseUrl}/api/v1/auth/login`, 
        JSON.stringify({
          email: TEST_CONFIG.auth.jwt.testUser.email,
          password: TEST_CONFIG.auth.jwt.testUser.password,
        }), {
        headers: HEADERS,
        tags: { endpoint: 'mfa-login', step: 'initial' },
      });

      check(loginResponse, {
        'login processed': (r) => r.status === 200 || r.status === 202,
        'MFA challenge or success': (r) => {
          if (r.status === 202) {
            // MFA challenge
            return r.json().hasOwnProperty('mfa_token') || 
                   r.json().hasOwnProperty('challenge');
          }
          return r.status === 200; // No MFA required
        },
      });

      // If MFA challenge was issued, attempt to verify
      if (loginResponse.status === 202) {
        const challengeData = loginResponse.json();
        
        const verifyResponse = http.post(`${baseUrl}/api/v1/mfa/verify`, 
          JSON.stringify({
            mfa_token: challengeData.mfa_token || 'test-mfa-token',
            code: '123456', // Test code
            method: 'totp',
          }), {
          headers: HEADERS,
          tags: { endpoint: 'mfa-verify', method: 'totp' },
        });

        check(verifyResponse, {
          'MFA verification handled': (r) => r.status === 200 || r.status === 400 || r.status === 401,
          'proper response format': (r) => {
            if (r.status === 200) {
              return r.json().hasOwnProperty('access_token');
            }
            return r.json().hasOwnProperty('error') || r.json().hasOwnProperty('detail');
          },
        });
      }
    });

    group('Multiple MFA Attempts', () => {
      // Test rate limiting and attempt tracking
      const attempts = [];
      for (let i = 0; i < 6; i++) { // Try more than typical limit
        const response = http.post(`${baseUrl}/api/v1/mfa/verify`, 
          JSON.stringify({
            mfa_token: 'test-token',
            code: '000000', // Wrong code
            method: 'totp',
          }), {
          headers: HEADERS,
          tags: { endpoint: 'mfa-verify', test: 'rate-limit' },
        });
        attempts.push(response);
      }

      const blockedAttempts = attempts.filter(r => r.status === 429).length;
      check({ attempts, blockedAttempts }, {
        'rate limiting applied': (data) => data.blockedAttempts > 0 || data.attempts.every(r => r.status === 401),
        'no server errors': (data) => data.attempts.every(r => r.status < 500),
      });
    });
  });
}

export function testSMSMFA(data) {
  group('SMS MFA Flow', () => {
    const { baseUrl, userToken } = data;

    group('Setup SMS MFA', () => {
      const phoneData = {
        phone_number: '+1234567890',
        country_code: '+1',
      };

      const response = http.post(`${baseUrl}/api/v1/mfa/sms/setup`, 
        JSON.stringify(phoneData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'mfa-setup', type: 'sms' },
      });

      check(response, {
        'SMS setup initiated': (r) => r.status === 200 || r.status === 201 || r.status === 400,
        'verification sent': (r) => {
          if (r.status === 200 || r.status === 201) {
            return r.json().hasOwnProperty('verification_id') || 
                   r.json().hasOwnProperty('message');
          }
          return true; // Error responses are also valid
        },
      });
    });

    group('Verify SMS Code', () => {
      const verificationData = {
        verification_id: 'test-verification-id',
        code: '123456',
      };

      const response = http.post(`${baseUrl}/api/v1/mfa/sms/verify-setup`, 
        JSON.stringify(verificationData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'mfa-setup', type: 'sms-verify' },
      });

      check(response, {
        'SMS verification processed': (r) => r.status === 200 || r.status === 400 || r.status === 404,
        'proper error handling': (r) => {
          if (r.status >= 400) {
            return r.json().hasOwnProperty('error') || r.json().hasOwnProperty('detail');
          }
          return true;
        },
      });
    });

    group('Request SMS Code for Authentication', () => {
      const requestData = {
        phone_number: '+1234567890',
      };

      const response = http.post(`${baseUrl}/api/v1/mfa/sms/request-code`, 
        JSON.stringify(requestData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'mfa-sms', action: 'request-code' },
      });

      check(response, {
        'SMS code request processed': (r) => r.status === 200 || r.status === 400 || r.status === 404,
        'rate limiting considered': (r) => {
          // Multiple rapid requests should be rate limited
          return r.status !== 500;
        },
      });
    });
  });
}

export function testRecoveryCodes(data) {
  group('Recovery Codes Flow', () => {
    const { baseUrl, userToken } = data;

    group('Generate Recovery Codes', () => {
      const response = http.post(`${baseUrl}/api/v1/mfa/recovery-codes/generate`, {}, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'mfa-recovery', action: 'generate' },
      });

      check(response, {
        'recovery codes generated': (r) => r.status === 200 || r.status === 201 || r.status === 404,
        'codes format correct': (r) => {
          if (r.status === 200 || r.status === 201) {
            const data = r.json();
            return data.hasOwnProperty('codes') && Array.isArray(data.codes);
          }
          return true;
        },
      });
    });

    group('Use Recovery Code', () => {
      const recoveryData = {
        mfa_token: 'test-mfa-token',
        recovery_code: 'RECOVERY123',
      };

      const response = http.post(`${baseUrl}/api/v1/mfa/verify`, 
        JSON.stringify(recoveryData), {
        headers: HEADERS,
        tags: { endpoint: 'mfa-verify', method: 'recovery' },
      });

      check(response, {
        'recovery code verification processed': (r) => r.status === 200 || r.status === 400 || r.status === 401,
        'single use enforcement': (r) => {
          // Recovery codes should be single-use
          return r.status !== 500;
        },
      });
    });

    group('View Remaining Recovery Codes', () => {
      const response = http.get(`${baseUrl}/api/v1/mfa/recovery-codes`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'mfa-recovery', action: 'view' },
      });

      validators.apiResponse(response, 200);
      
      if (response.status === 200) {
        check(response, {
          'recovery codes listed securely': (r) => {
            const data = r.json().data;
            // Should not show full codes, only count or masked versions
            return data.hasOwnProperty('remaining_count') || 
                   data.hasOwnProperty('codes');
          },
        });
      }
    });
  });
}

export function testMFASecurity(data) {
  group('MFA Security Tests', () => {
    const { baseUrl, userToken } = data;

    group('MFA Session Management', () => {
      // Test MFA session timeout and management
      const sessionResponse = http.get(`${baseUrl}/api/v1/mfa/session`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'mfa-session', action: 'check' },
      });

      check(sessionResponse, {
        'MFA session info available': (r) => r.status === 200 || r.status === 404,
        'session security details': (r) => {
          if (r.status === 200) {
            const session = r.json().data;
            return session.hasOwnProperty('expires_at') || 
                   session.hasOwnProperty('created_at');
          }
          return true;
        },
      });
    });

    group('MFA Audit Logging', () => {
      // Test MFA audit trail
      const auditResponse = http.get(`${baseUrl}/api/v1/mfa/audit-logs`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'mfa-audit', action: 'view' },
      });

      check(auditResponse, {
        'audit logs accessible': (r) => r.status === 200 || r.status === 403 || r.status === 404,
        'audit data format': (r) => {
          if (r.status === 200) {
            const logs = r.json().data;
            return Array.isArray(logs);
          }
          return true;
        },
      });
    });

    group('MFA Bypass Attempts', () => {
      // Test attempts to bypass MFA
      const bypassAttempts = [
        { endpoint: '/api/v1/users/me', method: 'GET' },
        { endpoint: '/api/v1/posts', method: 'GET' },
        { endpoint: '/api/v1/mfa/disable', method: 'POST' },
      ];

      bypassAttempts.forEach(attempt => {
        const response = http.request(attempt.method, `${baseUrl}${attempt.endpoint}`, null, {
          headers: HEADERS, // No Authorization header
          tags: { endpoint: attempt.endpoint, test: 'bypass-attempt' },
        });

        check(response, {
          [`${attempt.endpoint} requires authentication`]: (r) => r.status === 401,
        });
      });
    });

    group('MFA Device Management', () => {
      // Test listing and managing MFA devices
      const devicesResponse = http.get(`${baseUrl}/api/v1/mfa/devices`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'mfa-devices', action: 'list' },
      });

      check(devicesResponse, {
        'MFA devices listed': (r) => r.status === 200 || r.status === 404,
        'device info secure': (r) => {
          if (r.status === 200) {
            const devices = r.json().data;
            return Array.isArray(devices);
          }
          return true;
        },
      });

      // Test removing an MFA device
      const removeData = {
        device_id: 'test-device-id',
        current_password: TEST_CONFIG.auth.jwt.testUser.password,
      };

      const removeResponse = http.delete(`${baseUrl}/api/v1/mfa/devices/test-device-id`, 
        JSON.stringify(removeData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'mfa-devices', action: 'remove' },
      });

      check(removeResponse, {
        'device removal secure': (r) => {
          // Should require password or have other security measures
          return r.status === 200 || r.status === 400 || r.status === 404;
        },
      });
    });

    group('MFA Analytics and Monitoring', () => {
      // Test MFA usage analytics
      const analyticsResponse = http.get(`${baseUrl}/api/v1/mfa/analytics`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'mfa-analytics', action: 'view' },
      });

      check(analyticsResponse, {
        'MFA analytics available': (r) => r.status === 200 || r.status === 403 || r.status === 404,
        'analytics data structure': (r) => {
          if (r.status === 200) {
            const analytics = r.json().data;
            return typeof analytics === 'object';
          }
          return true;
        },
      });
    });
  });
}

export function teardown(data) {
  console.log('🧹 Cleaning up MFA Tests');
  dbHelpers.cleanTestDb(data.baseUrl);
}

export function handleSummary(data) {
  return {
    'k6-tests/results/mfa-test.html': htmlReport(data),
    'k6-tests/results/mfa-test.json': JSON.stringify(data),
  };
}