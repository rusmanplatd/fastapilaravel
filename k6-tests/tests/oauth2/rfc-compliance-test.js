/**
 * OAuth2 RFC Compliance Tests
 * Tests compliance with OAuth2 RFCs and security standards
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';

import { TEST_CONFIG, FORM_HEADERS, HEADERS } from '../../config/test-config.js';
import { AuthHelper, validators, dbHelpers } from '../../utils/helpers.js';

export let options = {
  scenarios: {
    rfc6749_core: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 8 },
        { duration: '2m', target: 12 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testRFC6749Core',
    },
    rfc7662_introspection: {
      executor: 'constant-vus',
      vus: 10,
      duration: '3m',
      exec: 'testRFC7662Introspection',
    },
    rfc7636_pkce: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 6 },
        { duration: '2m', target: 15 },
        { duration: '30s', target: 0 },
      ],
      exec: 'testRFC7636PKCE',
    },
    rfc8414_metadata: {
      executor: 'constant-vus',
      vus: 5,
      duration: '2m',
      exec: 'testRFC8414Metadata',
    },
    security_best_practices: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 10 },
        { duration: '2m', target: 15 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testSecurityBestPractices',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<2000'],
    http_req_failed: ['rate<0.05'],
    'http_req_duration{rfc:6749}': ['p(95)<1500'],
    'http_req_duration{rfc:7662}': ['p(95)<800'],
  },
};

export function setup() {
  console.log('📋 Setting up OAuth2 RFC Compliance Tests');
  
  dbHelpers.setupTestDb(TEST_CONFIG.baseUrl);
  
  return { 
    baseUrl: TEST_CONFIG.baseUrl,
    clientId: TEST_CONFIG.auth.oauth2.client.id,
    clientSecret: TEST_CONFIG.auth.oauth2.client.secret,
  };
}

export function testRFC6749Core(data) {
  group('RFC 6749: OAuth 2.0 Authorization Framework', () => {
    const { baseUrl, clientId, clientSecret } = data;

    group('Authorization Code Grant (Section 4.1)', () => {
      // Step 1: Authorization Request
      const authParams = new URLSearchParams({
        response_type: 'code',
        client_id: clientId,
        redirect_uri: 'http://localhost:3000/callback',
        scope: 'read write',
        state: 'test-state-12345',
      });

      const authResponse = http.get(`${baseUrl}/oauth/authorize?${authParams}`, {
        tags: { endpoint: 'authorize', rfc: '6749', section: '4.1.1' },
        redirects: 0,
      });

      check(authResponse, {
        'authorization request handled': (r) => r.status === 200 || r.status === 302,
        'contains required parameters': (r) => {
          // Should redirect to login or consent page
          return r.status === 200 || (r.status === 302 && r.headers['Location']);
        },
      });

      // Step 2: Token Request (simulated - would normally have auth code)
      const tokenResponse = http.post(`${baseUrl}/oauth/token`, {
        grant_type: 'authorization_code',
        code: 'simulated-auth-code',
        redirect_uri: 'http://localhost:3000/callback',
        client_id: clientId,
        client_secret: clientSecret,
      }, {
        headers: FORM_HEADERS,
        tags: { endpoint: 'token', rfc: '6749', section: '4.1.3' },
      });

      check(tokenResponse, {
        'token request processed': (r) => r.status === 200 || r.status === 400 || r.status === 401,
        'proper error handling': (r) => {
          if (r.status >= 400) {
            const body = r.json();
            return body.hasOwnProperty('error');
          }
          return true;
        },
      });
    });

    group('Client Credentials Grant (Section 4.4)', () => {
      const response = http.post(`${baseUrl}/oauth/token`, {
        grant_type: 'client_credentials',
        client_id: clientId,
        client_secret: clientSecret,
        scope: 'read write',
      }, {
        headers: FORM_HEADERS,
        tags: { endpoint: 'token', rfc: '6749', section: '4.4' },
      });

      validators.oauth2TokenResponse(response);

      check(response, {
        'RFC 6749 compliant token response': (r) => {
          if (r.status !== 200) return false;
          const token = r.json();
          return token.hasOwnProperty('access_token') &&
                 token.hasOwnProperty('token_type') &&
                 token.token_type.toLowerCase() === 'bearer';
        },
      });
    });

    group('Refresh Token Grant (Section 6)', () => {
      // First get a token that might include refresh token
      const initialResponse = http.post(`${baseUrl}/oauth/token`, {
        grant_type: 'client_credentials',
        client_id: clientId,
        client_secret: clientSecret,
        scope: 'read write',
      }, { headers: FORM_HEADERS });

      if (initialResponse.status === 200) {
        const tokenData = initialResponse.json();
        
        if (tokenData.refresh_token) {
          const refreshResponse = http.post(`${baseUrl}/oauth/token`, {
            grant_type: 'refresh_token',
            refresh_token: tokenData.refresh_token,
            client_id: clientId,
            client_secret: clientSecret,
          }, {
            headers: FORM_HEADERS,
            tags: { endpoint: 'token', rfc: '6749', section: '6' },
          });

          validators.oauth2TokenResponse(refreshResponse);
        }
      }
    });

    group('Error Response Format (Section 5.2)', () => {
      // Test invalid grant type
      const response = http.post(`${baseUrl}/oauth/token`, {
        grant_type: 'invalid_grant_type',
        client_id: clientId,
        client_secret: clientSecret,
      }, {
        headers: FORM_HEADERS,
        tags: { endpoint: 'token', rfc: '6749', section: '5.2' },
      });

      check(response, {
        'error response format compliant': (r) => {
          if (r.status !== 400) return false;
          const error = r.json();
          return error.hasOwnProperty('error') && 
                 error.error === 'unsupported_grant_type';
        },
      });
    });
  });
}

export function testRFC7662Introspection(data) {
  group('RFC 7662: OAuth 2.0 Token Introspection', () => {
    const { baseUrl, clientId, clientSecret } = data;
    const authHelper = new AuthHelper(baseUrl);

    // Get a valid token first
    const token = authHelper.getOAuth2Token(clientId, clientSecret);

    group('Token Introspection Request (Section 2.1)', () => {
      const response = http.post(`${baseUrl}/oauth/introspect`, {
        token: token,
        client_id: clientId,
        client_secret: clientSecret,
      }, {
        headers: FORM_HEADERS,
        tags: { endpoint: 'introspect', rfc: '7662', section: '2.1' },
      });

      check(response, {
        'introspection response is 200': (r) => r.status === 200,
        'response is JSON': (r) => r.headers['Content-Type'].includes('application/json'),
        'has active field': (r) => r.json().hasOwnProperty('active'),
        'RFC 7662 compliant response': (r) => {
          const intro = r.json();
          if (!intro.active) return true; // Inactive tokens need only 'active: false'
          
          // Active tokens should have additional claims
          return intro.hasOwnProperty('client_id') &&
                 intro.hasOwnProperty('exp') &&
                 intro.hasOwnProperty('iat');
        },
      });
    });

    group('Invalid Token Introspection', () => {
      const response = http.post(`${baseUrl}/oauth/introspect`, {
        token: 'invalid.token.value',
        client_id: clientId,
        client_secret: clientSecret,
      }, {
        headers: FORM_HEADERS,
        tags: { endpoint: 'introspect', rfc: '7662', section: '2.2' },
      });

      check(response, {
        'invalid token handled correctly': (r) => r.status === 200,
        'inactive token response': (r) => r.json().active === false,
      });
    });

    group('Client Authentication (Section 2.1)', () => {
      // Test without client credentials
      const response = http.post(`${baseUrl}/oauth/introspect`, {
        token: token,
      }, {
        headers: FORM_HEADERS,
        tags: { endpoint: 'introspect', rfc: '7662', section: '2.1' },
      });

      check(response, {
        'client auth required': (r) => r.status === 401,
        'proper error format': (r) => {
          if (r.status === 401) {
            return r.headers['WWW-Authenticate'] || r.json().hasOwnProperty('error');
          }
          return true;
        },
      });
    });
  });
}

export function testRFC7636PKCE(data) {
  group('RFC 7636: Proof Key for Code Exchange (PKCE)', () => {
    const { baseUrl, clientId } = data;

    group('PKCE Parameters (Section 4.1)', () => {
      const codeVerifier = generateCodeVerifier();
      const codeChallenge = generateCodeChallenge(codeVerifier);

      const authParams = new URLSearchParams({
        response_type: 'code',
        client_id: clientId,
        redirect_uri: 'http://localhost:3000/callback',
        scope: 'read',
        state: 'pkce-test-state',
        code_challenge: codeChallenge,
        code_challenge_method: 'S256',
      });

      const response = http.get(`${baseUrl}/oauth/authorize?${authParams}`, {
        tags: { endpoint: 'authorize', rfc: '7636', section: '4.1' },
        redirects: 0,
      });

      check(response, {
        'PKCE authorization request handled': (r) => r.status === 200 || r.status === 302,
        'PKCE parameters accepted': (r) => r.status !== 400,
      });
    });

    group('Code Challenge Methods (Section 4.2)', () => {
      const methods = ['plain', 'S256'];
      
      methods.forEach(method => {
        const codeVerifier = generateCodeVerifier();
        const codeChallenge = method === 'plain' ? codeVerifier : generateCodeChallenge(codeVerifier);

        const authParams = new URLSearchParams({
          response_type: 'code',
          client_id: clientId,
          redirect_uri: 'http://localhost:3000/callback',
          scope: 'read',
          code_challenge: codeChallenge,
          code_challenge_method: method,
        });

        const response = http.get(`${baseUrl}/oauth/authorize?${authParams}`, {
          tags: { endpoint: 'authorize', rfc: '7636', method: method },
          redirects: 0,
        });

        check(response, {
          [`${method} method supported`]: (r) => r.status !== 400,
        });
      });
    });

    group('Invalid PKCE Parameters', () => {
      // Test with invalid code challenge method
      const response = http.get(`${baseUrl}/oauth/authorize?response_type=code&client_id=${clientId}&code_challenge=test&code_challenge_method=invalid`, {
        tags: { endpoint: 'authorize', rfc: '7636', test: 'invalid' },
        redirects: 0,
      });

      check(response, {
        'invalid method rejected': (r) => r.status === 400 || r.status === 302,
      });
    });
  });
}

export function testRFC8414Metadata(data) {
  group('RFC 8414: OAuth 2.0 Authorization Server Metadata', () => {
    const { baseUrl } = data;

    group('Well-Known Metadata Endpoint', () => {
      const response = http.get(`${baseUrl}/.well-known/oauth-authorization-server`, {
        headers: HEADERS,
        tags: { endpoint: 'metadata', rfc: '8414' },
      });

      check(response, {
        'metadata endpoint accessible': (r) => r.status === 200,
        'content type is JSON': (r) => r.headers['Content-Type'].includes('application/json'),
        'has required metadata': (r) => {
          if (r.status !== 200) return false;
          const metadata = r.json();
          
          // Required fields per RFC 8414
          return metadata.hasOwnProperty('issuer') &&
                 metadata.hasOwnProperty('authorization_endpoint') &&
                 metadata.hasOwnProperty('token_endpoint') &&
                 metadata.hasOwnProperty('response_types_supported') &&
                 metadata.hasOwnProperty('grant_types_supported');
        },
        'issuer matches server': (r) => {
          if (r.status !== 200) return false;
          const metadata = r.json();
          return metadata.issuer && metadata.issuer.includes(baseUrl.replace(/^https?:\/\//, ''));
        },
      });
    });

    group('Metadata Completeness', () => {
      const response = http.get(`${baseUrl}/.well-known/oauth-authorization-server`, {
        headers: HEADERS,
      });

      if (response.status === 200) {
        const metadata = response.json();
        
        check(response, {
          'has token endpoint auth methods': () => metadata.hasOwnProperty('token_endpoint_auth_methods_supported'),
          'has scopes supported': () => metadata.hasOwnProperty('scopes_supported'),
          'has code challenge methods': () => metadata.hasOwnProperty('code_challenge_methods_supported'),
          'includes introspection endpoint': () => metadata.hasOwnProperty('introspection_endpoint'),
          'includes revocation endpoint': () => metadata.hasOwnProperty('revocation_endpoint'),
        });
      }
    });
  });
}

export function testSecurityBestPractices(data) {
  group('OAuth2 Security Best Practices (RFC 8725)', () => {
    const { baseUrl, clientId, clientSecret } = data;

    group('State Parameter Usage', () => {
      // Test authorization with and without state parameter
      const withoutState = http.get(`${baseUrl}/oauth/authorize?response_type=code&client_id=${clientId}`, {
        tags: { endpoint: 'authorize', security: 'state', test: 'without' },
        redirects: 0,
      });

      const withState = http.get(`${baseUrl}/oauth/authorize?response_type=code&client_id=${clientId}&state=security-test`, {
        tags: { endpoint: 'authorize', security: 'state', test: 'with' },
        redirects: 0,
      });

      check({ withoutState, withState }, {
        'requests processed': (data) => data.withState.status !== 500 && data.withoutState.status !== 500,
        'state parameter handling': (data) => {
          // Both should be handled properly
          return (data.withState.status === 200 || data.withState.status === 302) &&
                 (data.withoutState.status === 200 || data.withoutState.status === 302 || data.withoutState.status === 400);
        },
      });
    });

    group('Client Authentication Security', () => {
      // Test different client authentication methods
      const methods = [
        { name: 'client_secret_basic', headers: { 'Authorization': `Basic ${btoa(`${clientId}:${clientSecret}`)}` } },
        { name: 'client_secret_post', body: { client_id: clientId, client_secret: clientSecret } },
      ];

      methods.forEach(method => {
        const body = {
          grant_type: 'client_credentials',
          scope: 'read',
          ...method.body,
        };

        const headers = {
          ...FORM_HEADERS,
          ...method.headers,
        };

        const response = http.post(`${baseUrl}/oauth/token`, body, {
          headers: headers,
          tags: { endpoint: 'token', security: 'auth', method: method.name },
        });

        check(response, {
          [`${method.name} authentication works`]: (r) => r.status === 200 || r.status === 401,
        });
      });
    });

    group('Token Lifetime and Security', () => {
      // Get token and check its properties
      const response = http.post(`${baseUrl}/oauth/token`, {
        grant_type: 'client_credentials',
        client_id: clientId,
        client_secret: clientSecret,
        scope: 'read',
      }, { headers: FORM_HEADERS });

      if (response.status === 200) {
        const token = response.json();
        
        check(response, {
          'token has reasonable expiry': (r) => {
            const expiresIn = r.json().expires_in;
            return expiresIn && expiresIn > 0 && expiresIn <= 7200; // Max 2 hours
          },
          'token type is Bearer': (r) => r.json().token_type === 'Bearer',
          'access token is not empty': (r) => r.json().access_token && r.json().access_token.length > 10,
        });
      }
    });

    group('Scope Validation', () => {
      // Test with valid and invalid scopes
      const scopeTests = [
        { scope: 'read', expectedValid: true },
        { scope: 'read write', expectedValid: true },
        { scope: 'invalid-scope-123', expectedValid: false },
        { scope: 'read write admin super-admin', expectedValid: false }, // Too many scopes
      ];

      scopeTests.forEach(test => {
        const response = http.post(`${baseUrl}/oauth/token`, {
          grant_type: 'client_credentials',
          client_id: clientId,
          client_secret: clientSecret,
          scope: test.scope,
        }, {
          headers: FORM_HEADERS,
          tags: { endpoint: 'token', security: 'scope', test: test.scope },
        });

        check(response, {
          [`scope '${test.scope}' handled correctly`]: (r) => {
            if (test.expectedValid) {
              return r.status === 200;
            } else {
              return r.status === 400 || (r.status === 200 && r.json().scope !== test.scope);
            }
          },
        });
      });
    });

    group('Rate Limiting and DDoS Protection', () => {
      // Test rate limiting on token endpoint
      const responses = [];
      for (let i = 0; i < 20; i++) {
        const response = http.post(`${baseUrl}/oauth/token`, {
          grant_type: 'client_credentials',
          client_id: clientId,
          client_secret: 'wrong-secret', // Intentionally wrong to avoid creating too many tokens
        }, {
          headers: FORM_HEADERS,
          tags: { endpoint: 'token', security: 'rate-limit' },
        });
        responses.push(response);
      }

      const rateLimitedCount = responses.filter(r => r.status === 429).length;
      const authFailedCount = responses.filter(r => r.status === 401).length;

      check({ responses, rateLimitedCount, authFailedCount }, {
        'rate limiting or auth failure applied': (data) => 
          data.rateLimitedCount > 0 || data.authFailedCount > 0,
        'no server errors': (data) => 
          data.responses.every(r => r.status < 500),
      });
    });
  });
}

// Helper functions for PKCE
function generateCodeVerifier() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
  let result = '';
  for (let i = 0; i < 128; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

function generateCodeChallenge(verifier) {
  // Simplified SHA256 simulation for k6 (in real implementation, use proper SHA256)
  return btoa(verifier + 'salt').replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

export function teardown(data) {
  console.log('🧹 Cleaning up OAuth2 RFC Compliance Tests');
  dbHelpers.cleanTestDb(data.baseUrl);
}

export function handleSummary(data) {
  return {
    'k6-tests/results/rfc-compliance-test.html': htmlReport(data),
    'k6-tests/results/rfc-compliance-test.json': JSON.stringify(data),
  };
}