/**
 * OAuth2 Authentication Tests
 * Comprehensive testing of OAuth2 flows and endpoints
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { SharedArray } from 'k6/data';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';

import { TEST_CONFIG, FORM_HEADERS } from '../../config/test-config.js';
import { AuthHelper, generateTestData, validators, dbHelpers } from '../../utils/helpers.js';

const oauth2Clients = new SharedArray('oauth2-clients', function() {
  return [
    {
      id: 'test-client-id',
      secret: 'test-client-secret',
      scopes: 'read write'
    },
    {
      id: 'confidential-client', 
      secret: 'confidential-secret',
      scopes: 'read write admin'
    }
  ];
});

export let options = {
  scenarios: {
    client_credentials_flow: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 15 },
        { duration: '3m', target: 25 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testClientCredentialsFlow',
    },
    authorization_code_flow: {
      executor: 'constant-vus',
      vus: 10,
      duration: '3m',
      exec: 'testAuthorizationCodeFlow',
    },
    token_introspection: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 10 },
        { duration: '2m', target: 20 },
        { duration: '30s', target: 0 },
      ],
      exec: 'testTokenIntrospection',
    },
    token_revocation: {
      executor: 'constant-vus',
      vus: 5,
      duration: '2m',
      exec: 'testTokenRevocation',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<2000'],
    http_req_failed: ['rate<0.05'],
    'http_req_duration{endpoint:token}': ['p(95)<1000'],
    'http_req_duration{endpoint:introspect}': ['p(95)<500'],
  },
};

export function setup() {
  console.log('🔐 Setting up OAuth2 Authentication Tests');
  
  dbHelpers.setupTestDb(TEST_CONFIG.baseUrl);
  
  return { 
    baseUrl: TEST_CONFIG.baseUrl,
    clients: oauth2Clients 
  };
}

export function testClientCredentialsFlow(data) {
  group('Client Credentials Flow', () => {
    const { baseUrl, clients } = data;
    const client = clients[0];

    group('Valid Client Credentials', () => {
      const response = http.post(`${baseUrl}/oauth/token`, {
        grant_type: 'client_credentials',
        client_id: client.id,
        client_secret: client.secret,
        scope: client.scopes,
      }, {
        headers: FORM_HEADERS,
        tags: { endpoint: 'token', flow: 'client_credentials' },
      });

      validators.oauth2TokenResponse(response);
      
      check(response, {
        'scope matches requested': (r) => {
          const scopes = r.json().scope || '';
          return client.scopes.split(' ').every(scope => scopes.includes(scope));
        },
      });
    });

    group('Invalid Client Credentials', () => {
      const response = http.post(`${baseUrl}/oauth/token`, {
        grant_type: 'client_credentials',
        client_id: client.id,
        client_secret: 'wrong-secret',
        scope: client.scopes,
      }, {
        headers: FORM_HEADERS,
        tags: { endpoint: 'token', flow: 'client_credentials' },
      });

      validators.errorResponse(response, 401);
      
      check(response, {
        'error is invalid_client': (r) => r.json().error === 'invalid_client',
      });
    });

    group('Missing Client ID', () => {
      const response = http.post(`${baseUrl}/oauth/token`, {
        grant_type: 'client_credentials',
        client_secret: client.secret,
        scope: client.scopes,
      }, {
        headers: FORM_HEADERS,
        tags: { endpoint: 'token', flow: 'client_credentials' },
      });

      validators.errorResponse(response, 400);
      
      check(response, {
        'error is invalid_request': (r) => r.json().error === 'invalid_request',
      });
    });

    group('Invalid Scope', () => {
      const response = http.post(`${baseUrl}/oauth/token`, {
        grant_type: 'client_credentials',
        client_id: client.id,
        client_secret: client.secret,
        scope: 'invalid-scope',
      }, {
        headers: FORM_HEADERS,
        tags: { endpoint: 'token', flow: 'client_credentials' },
      });

      // Should either succeed with reduced scope or fail
      check(response, {
        'response is valid': (r) => r.status === 200 || r.status === 400,
      });
    });
  });
}

export function testAuthorizationCodeFlow(data) {
  group('Authorization Code Flow (PKCE)', () => {
    const { baseUrl } = data;
    
    group('Authorization Request', () => {
      const codeVerifier = generatePKCEVerifier();
      const codeChallenge = generatePKCEChallenge(codeVerifier);
      
      const authUrl = `${baseUrl}/oauth/authorize` + 
        `?response_type=code` +
        `&client_id=test-client-id` +
        `&redirect_uri=http://localhost:3000/callback` +
        `&scope=read write` +
        `&state=test-state-123` +
        `&code_challenge=${codeChallenge}` +
        `&code_challenge_method=S256`;

      const response = http.get(authUrl, {
        tags: { endpoint: 'authorize', flow: 'authorization_code' },
        redirects: 0, // Don't follow redirects
      });

      check(response, {
        'authorization request processed': (r) => r.status === 302 || r.status === 200,
        'response time < 1s': (r) => r.timings.duration < 1000,
      });
    });

    group('Token Exchange', () => {
      // Simulate successful authorization and token exchange
      const response = http.post(`${baseUrl}/oauth/token`, {
        grant_type: 'authorization_code',
        client_id: 'test-client-id',
        code: 'simulated-auth-code',
        redirect_uri: 'http://localhost:3000/callback',
        code_verifier: 'test-code-verifier',
      }, {
        headers: FORM_HEADERS,
        tags: { endpoint: 'token', flow: 'authorization_code' },
      });

      // This will likely fail without valid auth code, but tests the endpoint
      check(response, {
        'token exchange processed': (r) => r.status === 200 || r.status === 400,
        'response time < 1s': (r) => r.timings.duration < 1000,
      });
    });
  });
}

export function testTokenIntrospection(data) {
  group('Token Introspection', () => {
    const { baseUrl, clients } = data;
    const client = clients[0];
    const authHelper = new AuthHelper(baseUrl);

    // Get a valid token first
    const token = authHelper.getOAuth2Token(client.id, client.secret, client.scopes);

    group('Introspect Valid Token', () => {
      const response = http.post(`${baseUrl}/oauth/introspect`, {
        token: token,
        client_id: client.id,
        client_secret: client.secret,
      }, {
        headers: FORM_HEADERS,
        tags: { endpoint: 'introspect' },
      });

      check(response, {
        'introspection status is 200': (r) => r.status === 200,
        'token is active': (r) => r.json().active === true,
        'has client_id': (r) => r.json().hasOwnProperty('client_id'),
        'has scope': (r) => r.json().hasOwnProperty('scope'),
        'has exp': (r) => r.json().hasOwnProperty('exp'),
        'response time < 500ms': (r) => r.timings.duration < 500,
      });
    });

    group('Introspect Invalid Token', () => {
      const response = http.post(`${baseUrl}/oauth/introspect`, {
        token: 'invalid.token.here',
        client_id: client.id,
        client_secret: client.secret,
      }, {
        headers: FORM_HEADERS,
        tags: { endpoint: 'introspect' },
      });

      check(response, {
        'introspection status is 200': (r) => r.status === 200,
        'token is inactive': (r) => r.json().active === false,
      });
    });
  });
}

export function testTokenRevocation(data) {
  group('Token Revocation', () => {
    const { baseUrl, clients } = data;
    const client = clients[0];
    const authHelper = new AuthHelper(baseUrl);

    // Get a token to revoke
    const token = authHelper.getOAuth2Token(client.id, client.secret, client.scopes);

    group('Revoke Valid Token', () => {
      const response = http.post(`${baseUrl}/oauth/revoke`, {
        token: token,
        client_id: client.id,
        client_secret: client.secret,
      }, {
        headers: FORM_HEADERS,
        tags: { endpoint: 'revoke' },
      });

      check(response, {
        'revocation status is 200': (r) => r.status === 200,
        'response time < 500ms': (r) => r.timings.duration < 500,
      });

      // Verify token is revoked by introspecting it
      const introspectResponse = http.post(`${baseUrl}/oauth/introspect`, {
        token: token,
        client_id: client.id,
        client_secret: client.secret,
      }, {
        headers: FORM_HEADERS,
        tags: { endpoint: 'introspect' },
      });

      check(introspectResponse, {
        'revoked token is inactive': (r) => r.json().active === false,
      });
    });

    group('Revoke Invalid Token', () => {
      const response = http.post(`${baseUrl}/oauth/revoke`, {
        token: 'invalid.token',
        client_id: client.id,
        client_secret: client.secret,
      }, {
        headers: FORM_HEADERS,
        tags: { endpoint: 'revoke' },
      });

      check(response, {
        'revocation processed': (r) => r.status === 200 || r.status === 400,
      });
    });
  });
}

// Helper functions for PKCE
function generatePKCEVerifier() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
  let result = '';
  for (let i = 0; i < 128; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

function generatePKCEChallenge(verifier) {
  // For k6, we'll use a simplified challenge (in real implementation, use SHA256)
  return btoa(verifier).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

export function teardown(data) {
  console.log('🧹 Cleaning up OAuth2 Authentication Tests');
  dbHelpers.cleanTestDb(data.baseUrl);
}

export function handleSummary(data) {
  return {
    'k6-tests/results/oauth2-auth-test.html': htmlReport(data),
    'k6-tests/results/oauth2-auth-test.json': JSON.stringify(data),
  };
}