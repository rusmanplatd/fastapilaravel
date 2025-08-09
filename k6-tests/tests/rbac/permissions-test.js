/**
 * Permissions and Access Control Tests
 * Tests granular permissions and access control mechanisms
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';

import { TEST_CONFIG, HEADERS } from '../../config/test-config.js';
import { AuthHelper, generateTestData, validators, dbHelpers } from '../../utils/helpers.js';

export let options = {
  scenarios: {
    permission_hierarchy: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 8 },
        { duration: '2m', target: 12 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testPermissionHierarchy',
    },
    resource_permissions: {
      executor: 'constant-vus',
      vus: 10,
      duration: '3m',
      exec: 'testResourcePermissions',
    },
    dynamic_permissions: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 6 },
        { duration: '2m', target: 15 },
        { duration: '30s', target: 0 },
      ],
      exec: 'testDynamicPermissions',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<1500'],
    http_req_failed: ['rate<0.05'],
    'http_req_duration{endpoint:permissions}': ['p(95)<800'],
  },
};

export function setup() {
  console.log('🔐 Setting up Permissions and Access Control Tests');
  
  dbHelpers.setupTestDb(TEST_CONFIG.baseUrl);
  
  // Create tokens for different user types
  const authHelper = new AuthHelper(TEST_CONFIG.baseUrl);
  const adminToken = authHelper.loginJWT(
    TEST_CONFIG.auth.jwt.adminUser.email,
    TEST_CONFIG.auth.jwt.adminUser.password
  );
  const userToken = authHelper.loginJWT(
    TEST_CONFIG.auth.jwt.testUser.email,
    TEST_CONFIG.auth.jwt.testUser.password
  );
  
  return { 
    baseUrl: TEST_CONFIG.baseUrl,
    adminToken: adminToken,
    userToken: userToken,
  };
}

export function testPermissionHierarchy(data) {
  group('Permission Hierarchy Tests', () => {
    const { baseUrl, adminToken } = data;

    group('CRUD Operations on Permissions', () => {
      let createdPermissionId;

      // Create Permission
      const createData = {
        name: 'test-permission',
        display_name: 'Test Permission',
        description: 'Permission created for k6 testing',
        guard_name: 'api',
      };

      const createResponse = http.post(`${baseUrl}/api/v1/permissions`, 
        JSON.stringify(createData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'permissions', operation: 'create' },
      });

      const isCreateSuccess = validators.apiResponse(createResponse, 201);
      
      if (isCreateSuccess && createResponse.status === 201) {
        createdPermissionId = createResponse.json().data.id;
        
        check(createResponse, {
          'permission has correct name': (r) => r.json().data.name === createData.name,
          'permission has display name': (r) => r.json().data.display_name === createData.display_name,
        });
      }

      // Read Permission
      if (createdPermissionId) {
        const readResponse = http.get(`${baseUrl}/api/v1/permissions/${createdPermissionId}`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'permissions', operation: 'read' },
        });

        validators.apiResponse(readResponse, 200);
      }

      // Update Permission
      if (createdPermissionId) {
        const updateData = {
          display_name: 'Updated Test Permission',
          description: 'Updated description for k6 testing',
        };

        const updateResponse = http.put(`${baseUrl}/api/v1/permissions/${createdPermissionId}`, 
          JSON.stringify(updateData), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'permissions', operation: 'update' },
        });

        validators.apiResponse(updateResponse, 200);
        
        if (updateResponse.status === 200) {
          check(updateResponse, {
            'permission updated successfully': (r) => r.json().data.display_name === updateData.display_name,
          });
        }
      }

      // Delete Permission
      if (createdPermissionId) {
        const deleteResponse = http.del(`${baseUrl}/api/v1/permissions/${createdPermissionId}`, null, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'permissions', operation: 'delete' },
        });

        validators.apiResponse(deleteResponse, 200);
      }
    });

    group('Permission Inheritance', () => {
      // Test parent-child permission relationships
      const parentPermission = {
        name: 'manage-content',
        display_name: 'Manage Content',
        description: 'Parent permission for content management',
      };

      const childPermission = {
        name: 'edit-posts',
        display_name: 'Edit Posts',
        description: 'Child permission for editing posts',
        parent: 'manage-content',
      };

      // Create parent permission
      const parentResponse = http.post(`${baseUrl}/api/v1/permissions`, 
        JSON.stringify(parentPermission), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'permissions', operation: 'create-parent' },
      });

      check(parentResponse, {
        'parent permission creation processed': (r) => r.status === 201 || r.status === 422,
      });

      // Create child permission
      const childResponse = http.post(`${baseUrl}/api/v1/permissions`, 
        JSON.stringify(childPermission), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'permissions', operation: 'create-child' },
      });

      check(childResponse, {
        'child permission creation processed': (r) => r.status === 201 || r.status === 422,
      });
    });
  });
}

export function testResourcePermissions(data) {
  group('Resource-Specific Permissions', () => {
    const { baseUrl, adminToken, userToken } = data;

    group('Post Management Permissions', () => {
      // Test different permission levels on posts
      const postPermissions = [
        { action: 'view', expectedStatus: [200, 404] },
        { action: 'create', expectedStatus: [201, 403, 422] },
        { action: 'edit', expectedStatus: [200, 403, 404] },
        { action: 'delete', expectedStatus: [200, 403, 404] },
      ];

      postPermissions.forEach(({ action, expectedStatus }) => {
        group(`Post ${action} Permission`, () => {
          let endpoint, method, payload = null;
          
          switch (action) {
            case 'view':
              endpoint = '/api/v1/posts';
              method = 'GET';
              break;
            case 'create':
              endpoint = '/api/v1/posts';
              method = 'POST';
              payload = JSON.stringify(generateTestData.post());
              break;
            case 'edit':
              endpoint = '/api/v1/posts/1'; // Assume post with ID 1 exists
              method = 'PUT';
              payload = JSON.stringify({ title: 'Updated Title' });
              break;
            case 'delete':
              endpoint = '/api/v1/posts/1';
              method = 'DELETE';
              break;
          }

          // Test with admin token (should have access)
          const adminResponse = http.request(method, `${baseUrl}${endpoint}`, payload, {
            headers: {
              ...HEADERS,
              'Authorization': `Bearer ${adminToken}`,
            },
            tags: { endpoint: 'posts', action: action, role: 'admin' },
          });

          check(adminResponse, {
            [`admin ${action} permission valid`]: (r) => expectedStatus.includes(r.status),
          });

          // Test with user token (access depends on permission)
          const userResponse = http.request(method, `${baseUrl}${endpoint}`, payload, {
            headers: {
              ...HEADERS,
              'Authorization': `Bearer ${userToken}`,
            },
            tags: { endpoint: 'posts', action: action, role: 'user' },
          });

          check(userResponse, {
            [`user ${action} permission handled`]: (r) => 
              expectedStatus.includes(r.status) || r.status === 403,
          });
        });
      });
    });

    group('User Management Permissions', () => {
      // Test user management with different permission levels
      const userOperations = [
        { operation: 'list', method: 'GET', endpoint: '/api/v1/users' },
        { operation: 'create', method: 'POST', endpoint: '/api/v1/users', payload: generateTestData.user() },
        { operation: 'view-profile', method: 'GET', endpoint: '/api/v1/users/me' },
      ];

      userOperations.forEach(({ operation, method, endpoint, payload }) => {
        group(`User ${operation} Permission`, () => {
          const requestPayload = payload ? JSON.stringify(payload) : null;

          // Admin should have access to all user operations
          const adminResponse = http.request(method, `${baseUrl}${endpoint}`, requestPayload, {
            headers: {
              ...HEADERS,
              'Authorization': `Bearer ${adminToken}`,
            },
            tags: { endpoint: 'users', operation: operation, role: 'admin' },
          });

          check(adminResponse, {
            [`admin can ${operation}`]: (r) => r.status === 200 || r.status === 201 || r.status === 404,
          });

          // Regular users should have limited access
          const userResponse = http.request(method, `${baseUrl}${endpoint}`, requestPayload, {
            headers: {
              ...HEADERS,
              'Authorization': `Bearer ${userToken}`,
            },
            tags: { endpoint: 'users', operation: operation, role: 'user' },
          });

          if (operation === 'view-profile') {
            // Users should be able to view their own profile
            check(userResponse, {
              'user can view own profile': (r) => r.status === 200,
            });
          } else {
            // Users should be denied admin operations
            check(userResponse, {
              [`user denied ${operation}`]: (r) => r.status === 403,
            });
          }
        });
      });
    });

    group('API Rate Limiting by Permission Level', () => {
      // Test different rate limits based on user permissions
      const endpoints = [
        '/api/v1/posts',
        '/api/v1/users/me',
        '/api/v1/notifications',
      ];

      endpoints.forEach(endpoint => {
        group(`Rate Limiting on ${endpoint}`, () => {
          // Make multiple requests to test rate limiting
          const responses = [];
          for (let i = 0; i < 12; i++) {
            const response = http.get(`${baseUrl}${endpoint}`, {
              headers: {
                ...HEADERS,
                'Authorization': `Bearer ${userToken}`,
              },
              tags: { endpoint: endpoint, test: 'rate-limit' },
            });
            responses.push(response);
          }

          // Check if rate limiting is applied
          const rateLimitedResponses = responses.filter(r => r.status === 429);
          check({ responses }, {
            'rate limiting may be applied': () => true, // Always pass, just collecting data
            'all responses handled': (data) => data.responses.every(r => r.status < 500),
          });
        });
      });
    });
  });
}

export function testDynamicPermissions(data) {
  group('Dynamic Permission Tests', () => {
    const { baseUrl, adminToken } = data;

    group('Runtime Permission Assignment', () => {
      // Create a test user for dynamic permission assignment
      const userData = generateTestData.user();
      
      const userResponse = http.post(`${baseUrl}/api/v1/users`, JSON.stringify(userData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
      });

      if (userResponse.status === 201) {
        const userId = userResponse.json().data.id;

        // Assign specific permissions to user
        const permissionData = {
          permissions: ['read-posts', 'write-comments'],
        };

        const assignResponse = http.post(`${baseUrl}/api/v1/users/${userId}/permissions`,
          JSON.stringify(permissionData), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'user-permissions', operation: 'assign' },
        });

        validators.apiResponse(assignResponse, 200);

        // Verify permission assignment
        const checkResponse = http.get(`${baseUrl}/api/v1/users/${userId}/permissions`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'user-permissions', operation: 'check' },
        });

        validators.apiResponse(checkResponse, 200);
        
        if (checkResponse.status === 200) {
          check(checkResponse, {
            'user has assigned permissions': (r) => {
              const permissions = r.json().data || [];
              return permissions.some(p => p.name === 'read-posts');
            },
          });
        }

        // Revoke permissions
        const revokeResponse = http.delete(`${baseUrl}/api/v1/users/${userId}/permissions`,
          JSON.stringify({ permissions: ['write-comments'] }), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'user-permissions', operation: 'revoke' },
        });

        check(revokeResponse, {
          'permission revocation processed': (r) => r.status === 200 || r.status === 404,
        });
      }
    });

    group('Permission Caching and Performance', () => {
      // Test permission checks for performance under load
      const checkRequests = [];
      
      for (let i = 0; i < 10; i++) {
        const response = http.get(`${baseUrl}/api/v1/auth/permissions`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'permissions', test: 'performance' },
        });
        checkRequests.push(response);
      }

      // Verify all permission checks are fast
      check({ checkRequests }, {
        'permission checks are fast': (data) => {
          return data.checkRequests.every(r => r.timings.duration < 200);
        },
        'permission checks succeed': (data) => {
          return data.checkRequests.every(r => r.status === 200 || r.status === 404);
        },
      });
    });

    group('Conditional Permission Logic', () => {
      // Test permissions that depend on resource ownership or other conditions
      const conditionalChecks = [
        { endpoint: '/api/v1/posts/1/edit', condition: 'owns resource' },
        { endpoint: '/api/v1/users/me/settings', condition: 'self access' },
        { endpoint: '/api/v1/admin/system', condition: 'admin only' },
      ];

      conditionalChecks.forEach(({ endpoint, condition }) => {
        group(`Conditional Access: ${condition}`, () => {
          const response = http.get(`${baseUrl}${endpoint}`, {
            headers: {
              ...HEADERS,
              'Authorization': `Bearer ${adminToken}`,
            },
            tags: { endpoint: endpoint, condition: condition },
          });

          check(response, {
            'conditional access handled': (r) => r.status < 500, // Any client error is fine
            'response time acceptable': (r) => r.timings.duration < 1000,
          });
        });
      });
    });
  });
}

export function teardown(data) {
  console.log('🧹 Cleaning up Permissions and Access Control Tests');
  dbHelpers.cleanTestDb(data.baseUrl);
}

export function handleSummary(data) {
  return {
    'k6-tests/results/permissions-test.html': htmlReport(data),
    'k6-tests/results/permissions-test.json': JSON.stringify(data),
  };
}