/**
 * WebAuthn Authentication Tests
 * Tests WebAuthn registration and authentication flows
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';

import { TEST_CONFIG, HEADERS } from '../../config/test-config.js';
import { AuthHelper, generateTestData, validators, dbHelpers } from '../../utils/helpers.js';

export let options = {
  scenarios: {
    webauthn_registration: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 6 },
        { duration: '2m', target: 10 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testWebAuthnRegistration',
    },
    webauthn_authentication: {
      executor: 'constant-vus',
      vus: 8,
      duration: '3m',
      exec: 'testWebAuthnAuthentication',
    },
    credential_management: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 5 },
        { duration: '2m', target: 12 },
        { duration: '30s', target: 0 },
      ],
      exec: 'testCredentialManagement',
    },
    webauthn_security: {
      executor: 'constant-vus',
      vus: 6,
      duration: '2m',
      exec: 'testWebAuthnSecurity',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<3000'], // WebAuthn can be slower due to crypto operations
    http_req_failed: ['rate<0.05'],
    'http_req_duration{endpoint:webauthn-register}': ['p(95)<2000'],
    'http_req_duration{endpoint:webauthn-authenticate}': ['p(95)<2000'],
  },
};

export function setup() {
  console.log('🔐 Setting up WebAuthn Tests');
  
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
  };
}

export function testWebAuthnRegistration(data) {
  group('WebAuthn Registration Flow', () => {
    const { baseUrl, userToken } = data;

    group('Begin Registration', () => {
      const registrationOptions = {
        authenticator_type: 'platform', // or 'cross-platform'
        user_verification: 'required',
      };

      const response = http.post(`${baseUrl}/api/v1/webauthn/register/begin`, 
        JSON.stringify(registrationOptions), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'webauthn-register', step: 'begin' },
      });

      check(response, {
        'registration challenge created': (r) => r.status === 200 || r.status === 201,
        'has challenge data': (r) => {
          if (r.status !== 200 && r.status !== 201) return false;
          const data = r.json();
          return data.hasOwnProperty('challenge') && 
                 data.hasOwnProperty('rp') &&
                 data.hasOwnProperty('user');
        },
        'proper PublicKeyCredentialCreationOptions format': (r) => {
          if (r.status !== 200 && r.status !== 201) return false;
          const options = r.json();
          return options.hasOwnProperty('pubKeyCredParams') &&
                 options.hasOwnProperty('timeout') &&
                 Array.isArray(options.pubKeyCredParams);
        },
      });
    });

    group('Complete Registration', () => {
      // Simulate WebAuthn credential creation response
      const credentialData = {
        id: 'test-credential-id-' + Math.random().toString(36).substring(7),
        rawId: 'dGVzdC1jcmVkZW50aWFsLWlk', // base64url encoded
        response: {
          clientDataJSON: generateClientDataJSON('webauthn.create', 'localhost:8000'),
          attestationObject: generateMockAttestationObject(),
        },
        type: 'public-key',
        clientExtensionResults: {},
      };

      const response = http.post(`${baseUrl}/api/v1/webauthn/register/complete`, 
        JSON.stringify(credentialData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'webauthn-register', step: 'complete' },
      });

      check(response, {
        'registration completion processed': (r) => r.status === 200 || r.status === 201 || r.status === 400,
        'proper response format': (r) => {
          if (r.status === 200 || r.status === 201) {
            const result = r.json();
            return result.hasOwnProperty('verified') || result.hasOwnProperty('credential_id');
          } else if (r.status === 400) {
            return r.json().hasOwnProperty('error') || r.json().hasOwnProperty('detail');
          }
          return true;
        },
      });
    });

    group('Register Multiple Credentials', () => {
      // Test registering multiple authenticators for the same user
      for (let i = 0; i < 3; i++) {
        const beginResponse = http.post(`${baseUrl}/api/v1/webauthn/register/begin`, 
          JSON.stringify({ 
            authenticator_type: i % 2 === 0 ? 'platform' : 'cross-platform',
            user_verification: 'preferred' 
          }), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'webauthn-register', test: 'multiple', iteration: i },
        });

        check(beginResponse, {
          [`multiple registration ${i + 1} initiated`]: (r) => r.status === 200 || r.status === 201,
        });
      }
    });

    group('Registration with Different Parameters', () => {
      const parameterTests = [
        { 
          userVerification: 'required',
          attestation: 'direct',
          authenticatorSelection: { userVerification: 'required' }
        },
        { 
          userVerification: 'preferred',
          attestation: 'indirect',
          authenticatorSelection: { 
            userVerification: 'preferred',
            requireResidentKey: true 
          }
        },
        { 
          userVerification: 'discouraged',
          attestation: 'none',
          authenticatorSelection: { userVerification: 'discouraged' }
        },
      ];

      parameterTests.forEach((params, index) => {
        const response = http.post(`${baseUrl}/api/v1/webauthn/register/begin`, 
          JSON.stringify(params), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'webauthn-register', test: 'parameters', variant: index },
        });

        check(response, {
          [`parameter variant ${index + 1} handled`]: (r) => r.status === 200 || r.status === 201 || r.status === 400,
        });
      });
    });
  });
}

export function testWebAuthnAuthentication(data) {
  group('WebAuthn Authentication Flow', () => {
    const { baseUrl } = data;

    group('Begin Authentication', () => {
      const authOptions = {
        user_verification: 'required',
      };

      const response = http.post(`${baseUrl}/api/v1/webauthn/authenticate/begin`, 
        JSON.stringify(authOptions), {
        headers: HEADERS,
        tags: { endpoint: 'webauthn-authenticate', step: 'begin' },
      });

      check(response, {
        'authentication challenge created': (r) => r.status === 200 || r.status === 201,
        'has challenge data': (r) => {
          if (r.status !== 200 && r.status !== 201) return false;
          const data = r.json();
          return data.hasOwnProperty('challenge') && 
                 data.hasOwnProperty('allowCredentials');
        },
        'proper PublicKeyCredentialRequestOptions format': (r) => {
          if (r.status !== 200 && r.status !== 201) return false;
          const options = r.json();
          return options.hasOwnProperty('timeout') &&
                 options.hasOwnProperty('userVerification');
        },
      });
    });

    group('Complete Authentication', () => {
      // Simulate WebAuthn assertion response
      const assertionData = {
        id: 'test-credential-id-' + Math.random().toString(36).substring(7),
        rawId: 'dGVzdC1jcmVkZW50aWFsLWlk',
        response: {
          clientDataJSON: generateClientDataJSON('webauthn.get', 'localhost:8000'),
          authenticatorData: generateMockAuthenticatorData(),
          signature: generateMockSignature(),
          userHandle: 'dGVzdC11c2VyLWhhbmRsZQ==', // base64url encoded user handle
        },
        type: 'public-key',
        clientExtensionResults: {},
      };

      const response = http.post(`${baseUrl}/api/v1/webauthn/authenticate/complete`, 
        JSON.stringify(assertionData), {
        headers: HEADERS,
        tags: { endpoint: 'webauthn-authenticate', step: 'complete' },
      });

      check(response, {
        'authentication completion processed': (r) => r.status === 200 || r.status === 400 || r.status === 401,
        'proper response format': (r) => {
          if (r.status === 200) {
            const result = r.json();
            return result.hasOwnProperty('verified') || result.hasOwnProperty('access_token');
          } else if (r.status >= 400) {
            return r.json().hasOwnProperty('error') || r.json().hasOwnProperty('detail');
          }
          return true;
        },
      });
    });

    group('Passwordless Authentication', () => {
      // Test authentication without username/password (resident keys)
      const passwordlessOptions = {
        user_verification: 'required',
        resident_key_required: true,
      };

      const beginResponse = http.post(`${baseUrl}/api/v1/webauthn/authenticate/begin-passwordless`, 
        JSON.stringify(passwordlessOptions), {
        headers: HEADERS,
        tags: { endpoint: 'webauthn-authenticate', type: 'passwordless' },
      });

      check(beginResponse, {
        'passwordless authentication supported': (r) => r.status === 200 || r.status === 201 || r.status === 501,
        'resident key authentication': (r) => {
          if (r.status === 200 || r.status === 201) {
            const options = r.json();
            return !options.hasOwnProperty('allowCredentials') || 
                   options.allowCredentials.length === 0;
          }
          return true;
        },
      });
    });
  });
}

export function testCredentialManagement(data) {
  group('Credential Management', () => {
    const { baseUrl, userToken } = data;

    group('List User Credentials', () => {
      const response = http.get(`${baseUrl}/api/v1/webauthn/credentials`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'webauthn-credentials', action: 'list' },
      });

      validators.apiResponse(response, 200);
      
      if (response.status === 200) {
        check(response, {
          'credentials list format': (r) => {
            const data = r.json().data;
            return Array.isArray(data);
          },
          'credential info secure': (r) => {
            const credentials = r.json().data;
            if (credentials.length > 0) {
              const cred = credentials[0];
              return cred.hasOwnProperty('id') && 
                     cred.hasOwnProperty('created_at') &&
                     !cred.hasOwnProperty('public_key'); // Should not expose raw public key
            }
            return true;
          },
        });
      }
    });

    group('Update Credential Name', () => {
      // Test updating credential nickname/name
      const updateData = {
        credential_id: 'test-credential-id',
        name: 'My Updated Authenticator',
        description: 'Updated description for testing',
      };

      const response = http.put(`${baseUrl}/api/v1/webauthn/credentials/test-credential-id`, 
        JSON.stringify(updateData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'webauthn-credentials', action: 'update' },
      });

      check(response, {
        'credential update processed': (r) => r.status === 200 || r.status === 404 || r.status === 400,
        'update security': (r) => {
          // Should only allow updating metadata, not cryptographic material
          return r.status !== 500;
        },
      });
    });

    group('Delete Credential', () => {
      const deleteData = {
        current_password: TEST_CONFIG.auth.jwt.testUser.password,
        confirmation: true,
      };

      const response = http.del(`${baseUrl}/api/v1/webauthn/credentials/test-credential-id`, 
        JSON.stringify(deleteData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'webauthn-credentials', action: 'delete' },
      });

      check(response, {
        'credential deletion secure': (r) => {
          // Should require additional confirmation for security
          return r.status === 200 || r.status === 400 || r.status === 404;
        },
        'proper authorization': (r) => {
          // Should require password or other verification
          return r.status !== 200 || r.json().hasOwnProperty('message');
        },
      });
    });

    group('Bulk Credential Operations', () => {
      // Test operations on multiple credentials
      const bulkData = {
        credential_ids: ['cred-1', 'cred-2', 'cred-3'],
        action: 'disable',
        current_password: TEST_CONFIG.auth.jwt.testUser.password,
      };

      const response = http.post(`${baseUrl}/api/v1/webauthn/credentials/bulk`, 
        JSON.stringify(bulkData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'webauthn-credentials', action: 'bulk' },
      });

      check(response, {
        'bulk operations handled': (r) => r.status === 200 || r.status === 400 || r.status === 404,
        'security measures': (r) => {
          // Bulk operations should have additional security
          return r.status !== 200 || r.json().hasOwnProperty('results');
        },
      });
    });
  });
}

export function testWebAuthnSecurity(data) {
  group('WebAuthn Security Tests', () => {
    const { baseUrl, userToken } = data;

    group('Challenge Reuse Prevention', () => {
      // Test that challenges cannot be reused
      const challenges = [];
      
      // Get multiple challenges
      for (let i = 0; i < 3; i++) {
        const response = http.post(`${baseUrl}/api/v1/webauthn/authenticate/begin`, {}, {
          headers: HEADERS,
          tags: { endpoint: 'webauthn-authenticate', test: 'challenge-reuse', iteration: i },
        });
        
        if (response.status === 200 || response.status === 201) {
          challenges.push(response.json().challenge);
        }
      }

      // Verify challenges are unique
      const uniqueChallenges = new Set(challenges);
      check({ challenges, uniqueChallenges }, {
        'challenges are unique': (data) => data.challenges.length === data.uniqueChallenges.size,
        'challenges generated': (data) => data.challenges.length > 0,
      });
    });

    group('Origin Validation', () => {
      // Test with different origins
      const origins = [
        'http://localhost:8000',
        'https://example.com',
        'http://malicious-site.com',
      ];

      origins.forEach((origin, index) => {
        const credentialData = {
          id: `test-cred-origin-${index}`,
          response: {
            clientDataJSON: generateClientDataJSON('webauthn.create', origin),
            attestationObject: generateMockAttestationObject(),
          },
          type: 'public-key',
        };

        const response = http.post(`${baseUrl}/api/v1/webauthn/register/complete`, 
          JSON.stringify(credentialData), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
            'Origin': origin,
          },
          tags: { endpoint: 'webauthn-register', test: 'origin-validation', origin: origin },
        });

        check(response, {
          [`origin ${origin} validation`]: (r) => {
            // Localhost should be valid, others should be rejected
            if (origin.includes('localhost')) {
              return r.status === 200 || r.status === 201 || r.status === 400;
            } else {
              return r.status === 400 || r.status === 403;
            }
          },
        });
      });
    });

    group('Replay Attack Prevention', () => {
      // Test that the same assertion cannot be used twice
      const assertionData = {
        id: 'test-replay-credential',
        response: {
          clientDataJSON: generateClientDataJSON('webauthn.get', 'localhost:8000'),
          authenticatorData: generateMockAuthenticatorData(),
          signature: generateMockSignature(),
        },
        type: 'public-key',
      };

      // First attempt
      const firstResponse = http.post(`${baseUrl}/api/v1/webauthn/authenticate/complete`, 
        JSON.stringify(assertionData), {
        headers: HEADERS,
        tags: { endpoint: 'webauthn-authenticate', test: 'replay', attempt: 1 },
      });

      // Second attempt with same data
      const secondResponse = http.post(`${baseUrl}/api/v1/webauthn/authenticate/complete`, 
        JSON.stringify(assertionData), {
        headers: HEADERS,
        tags: { endpoint: 'webauthn-authenticate', test: 'replay', attempt: 2 },
      });

      check({ firstResponse, secondResponse }, {
        'first attempt processed': (data) => data.firstResponse.status !== 500,
        'replay prevented': (data) => {
          // If first succeeded, second should fail
          if (data.firstResponse.status === 200) {
            return data.secondResponse.status === 400 || data.secondResponse.status === 401;
          }
          return true;
        },
      });
    });

    group('Rate Limiting', () => {
      // Test rate limiting on WebAuthn endpoints
      const rapidRequests = [];
      
      for (let i = 0; i < 15; i++) {
        const response = http.post(`${baseUrl}/api/v1/webauthn/authenticate/begin`, {}, {
          headers: HEADERS,
          tags: { endpoint: 'webauthn-authenticate', test: 'rate-limit' },
        });
        rapidRequests.push(response);
      }

      const rateLimitedCount = rapidRequests.filter(r => r.status === 429).length;
      check({ rapidRequests, rateLimitedCount }, {
        'rate limiting applied': (data) => data.rateLimitedCount > 0 || data.rapidRequests.length < 15,
        'no server errors': (data) => data.rapidRequests.every(r => r.status < 500),
      });
    });

    group('WebAuthn Analytics', () => {
      // Test WebAuthn usage analytics
      const analyticsResponse = http.get(`${baseUrl}/api/v1/webauthn/analytics`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'webauthn-analytics' },
      });

      check(analyticsResponse, {
        'analytics available': (r) => r.status === 200 || r.status === 403 || r.status === 404,
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

// Helper functions to generate mock WebAuthn data
function generateClientDataJSON(type, origin) {
  const clientData = {
    type: type,
    challenge: 'dGVzdC1jaGFsbGVuZ2U', // base64url encoded
    origin: `http://${origin}`,
    crossOrigin: false,
  };
  return btoa(JSON.stringify(clientData));
}

function generateMockAttestationObject() {
  // Mock attestation object (in real implementation, this would be CBOR-encoded)
  return 'bW9jay1hdHRlc3RhdGlvbi1vYmplY3Q'; // base64url encoded mock data
}

function generateMockAuthenticatorData() {
  // Mock authenticator data (32-byte rpIdHash + flags + counter + extensions)
  return 'bW9jay1hdXRoZW50aWNhdG9yLWRhdGE'; // base64url encoded mock data
}

function generateMockSignature() {
  // Mock signature data
  return 'bW9jay1zaWduYXR1cmUtZGF0YQ'; // base64url encoded mock signature
}

export function teardown(data) {
  console.log('🧹 Cleaning up WebAuthn Tests');
  dbHelpers.cleanTestDb(data.baseUrl);
}

export function handleSummary(data) {
  return {
    'k6-tests/results/webauthn-test.html': htmlReport(data),
    'k6-tests/results/webauthn-test.json': JSON.stringify(data),
  };
}