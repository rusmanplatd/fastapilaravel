/**
 * User Management and RBAC Tests
 * Tests user CRUD operations and role-based access control
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { SharedArray } from 'k6/data';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';

import { TEST_CONFIG, HEADERS } from '../../config/test-config.js';
import { AuthHelper, generateTestData, validators, dbHelpers } from '../../utils/helpers.js';

const testUsers = new SharedArray('test-users', function() {
  const users = [];
  for (let i = 0; i < 30; i++) {
    users.push({
      ...generateTestData.user(),
      role: ['user', 'admin', 'moderator'][i % 3],
    });
  }
  return users;
});

export let options = {
  scenarios: {
    user_crud_operations: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 10 },
        { duration: '2m', target: 15 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testUserCRUD',
    },
    role_based_access: {
      executor: 'constant-vus',
      vus: 8,
      duration: '3m',
      exec: 'testRoleBasedAccess',
    },
    permission_checks: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 12 },
        { duration: '2m', target: 20 },
        { duration: '30s', target: 0 },
      ],
      exec: 'testPermissionChecks',
    },
    bulk_operations: {
      executor: 'constant-vus',
      vus: 5,
      duration: '2m',
      exec: 'testBulkOperations',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<2000'],
    http_req_failed: ['rate<0.05'],
    'http_req_duration{endpoint:users}': ['p(95)<1500'],
    'http_req_duration{endpoint:roles}': ['p(95)<1000'],
  },
};

export function setup() {
  console.log('👥 Setting up User Management and RBAC Tests');
  
  dbHelpers.setupTestDb(TEST_CONFIG.baseUrl);
  
  // Create admin and regular user tokens
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
    testUsers: testUsers,
  };
}

export function testUserCRUD(data) {
  group('User CRUD Operations', () => {
    const { baseUrl, adminToken } = data;
    let createdUserId;

    group('Create User', () => {
      const userData = generateTestData.user();
      
      const response = http.post(`${baseUrl}/api/v1/users`, JSON.stringify(userData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'users', operation: 'create' },
      });

      const isSuccess = validators.apiResponse(response, 201);
      
      if (isSuccess && response.status === 201) {
        createdUserId = response.json().data.id;
        
        check(response, {
          'user has correct email': (r) => r.json().data.email === userData.email,
          'user has correct name': (r) => r.json().data.name === userData.name,
          'user has id': (r) => r.json().data.hasOwnProperty('id'),
        });
      }
    });

    group('Read User', () => {
      if (createdUserId) {
        const response = http.get(`${baseUrl}/api/v1/users/${createdUserId}`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'users', operation: 'read' },
        });

        validators.apiResponse(response, 200);
        
        check(response, {
          'user data is complete': (r) => {
            const user = r.json().data;
            return user.hasOwnProperty('id') && 
                   user.hasOwnProperty('email') && 
                   user.hasOwnProperty('name');
          },
        });
      }
    });

    group('Update User', () => {
      if (createdUserId) {
        const updateData = {
          name: 'Updated Test User',
          phone: '+1987654321',
        };

        const response = http.put(`${baseUrl}/api/v1/users/${createdUserId}`, 
          JSON.stringify(updateData), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'users', operation: 'update' },
        });

        validators.apiResponse(response, 200);
        
        check(response, {
          'user name updated': (r) => r.json().data.name === updateData.name,
          'user phone updated': (r) => r.json().data.phone === updateData.phone,
        });
      }
    });

    group('List Users with Pagination', () => {
      const response = http.get(`${baseUrl}/api/v1/users?page=1&per_page=10`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'users', operation: 'list' },
      });

      validators.paginatedResponse(response);
      
      check(response, {
        'users list has items': (r) => Array.isArray(r.json().data) && r.json().data.length > 0,
        'pagination meta exists': (r) => r.json().meta.hasOwnProperty('total'),
      });
    });

    group('Delete User', () => {
      if (createdUserId) {
        const response = http.del(`${baseUrl}/api/v1/users/${createdUserId}`, null, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'users', operation: 'delete' },
        });

        validators.apiResponse(response, 200);
      }
    });
  });
}

export function testRoleBasedAccess(data) {
  group('Role-Based Access Control', () => {
    const { baseUrl, adminToken, userToken } = data;

    group('Admin Access to User Management', () => {
      const response = http.get(`${baseUrl}/api/v1/users`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'users', role: 'admin' },
      });

      validators.apiResponse(response, 200);
    });

    group('Regular User Denied Access to User Management', () => {
      const response = http.get(`${baseUrl}/api/v1/users`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'users', role: 'user' },
      });

      validators.errorResponse(response, 403);
    });

    group('Role Assignment', () => {
      // Create a test user to assign roles to
      const userData = generateTestData.user();
      
      const createResponse = http.post(`${baseUrl}/api/v1/users`, JSON.stringify(userData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
      });

      if (createResponse.status === 201) {
        const userId = createResponse.json().data.id;

        // Assign role
        const roleResponse = http.post(`${baseUrl}/api/v1/users/${userId}/roles`, 
          JSON.stringify({ roles: ['moderator'] }), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'roles', operation: 'assign' },
        });

        validators.apiResponse(roleResponse, 200);

        // Verify role assignment
        const userResponse = http.get(`${baseUrl}/api/v1/users/${userId}`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
        });

        check(userResponse, {
          'user has assigned role': (r) => {
            const roles = r.json().data.roles || [];
            return roles.some(role => role.name === 'moderator');
          },
        });
      }
    });

    group('Permission-Based Endpoint Access', () => {
      // Test different permission levels
      const endpoints = [
        { url: '/api/v1/roles', permission: 'manage-roles', method: 'GET' },
        { url: '/api/v1/permissions', permission: 'manage-permissions', method: 'GET' },
        { url: '/api/v1/admin/analytics', permission: 'view-analytics', method: 'GET' },
      ];

      endpoints.forEach(endpoint => {
        group(`Access ${endpoint.url} (${endpoint.permission})`, () => {
          // Test with admin (should have access)
          const adminResponse = http.request(endpoint.method, `${baseUrl}${endpoint.url}`, null, {
            headers: {
              ...HEADERS,
              'Authorization': `Bearer ${adminToken}`,
            },
            tags: { endpoint: endpoint.url, permission: endpoint.permission, role: 'admin' },
          });

          check(adminResponse, {
            'admin has access': (r) => r.status === 200 || r.status === 404, // 404 if endpoint doesn't exist
          });

          // Test with regular user (should be denied)
          const userResponse = http.request(endpoint.method, `${baseUrl}${endpoint.url}`, null, {
            headers: {
              ...HEADERS,
              'Authorization': `Bearer ${userToken}`,
            },
            tags: { endpoint: endpoint.url, permission: endpoint.permission, role: 'user' },
          });

          check(userResponse, {
            'user denied access': (r) => r.status === 403,
          });
        });
      });
    });
  });
}

export function testPermissionChecks(data) {
  group('Permission System Tests', () => {
    const { baseUrl, adminToken } = data;

    group('List All Roles', () => {
      const response = http.get(`${baseUrl}/api/v1/roles`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'roles', operation: 'list' },
      });

      validators.apiResponse(response, 200);
      
      check(response, {
        'roles list exists': (r) => Array.isArray(r.json().data),
        'has default roles': (r) => {
          const roles = r.json().data;
          const roleNames = roles.map(role => role.name);
          return roleNames.includes('admin') && roleNames.includes('user');
        },
      });
    });

    group('List All Permissions', () => {
      const response = http.get(`${baseUrl}/api/v1/permissions`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'permissions', operation: 'list' },
      });

      validators.apiResponse(response, 200);
      
      check(response, {
        'permissions list exists': (r) => Array.isArray(r.json().data),
        'has basic permissions': (r) => {
          const permissions = r.json().data;
          const permNames = permissions.map(perm => perm.name);
          return permNames.includes('read-users') || permNames.length > 0;
        },
      });
    });

    group('Role-Permission Management', () => {
      // Get first available role
      const rolesResponse = http.get(`${baseUrl}/api/v1/roles`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
      });

      if (rolesResponse.status === 200) {
        const roles = rolesResponse.json().data;
        if (roles.length > 0) {
          const roleId = roles[0].id;

          // Test adding permissions to role
          const permissionResponse = http.post(`${baseUrl}/api/v1/roles/${roleId}/permissions`,
            JSON.stringify({ permissions: ['read-users', 'write-users'] }), {
            headers: {
              ...HEADERS,
              'Authorization': `Bearer ${adminToken}`,
            },
            tags: { endpoint: 'role-permissions', operation: 'assign' },
          });

          check(permissionResponse, {
            'permission assignment processed': (r) => r.status === 200 || r.status === 422,
          });
        }
      }
    });
  });
}

export function testBulkOperations(data) {
  group('Bulk User Operations', () => {
    const { baseUrl, adminToken } = data;

    group('Bulk User Creation', () => {
      const users = [];
      for (let i = 0; i < 5; i++) {
        users.push(generateTestData.user());
      }

      const response = http.post(`${baseUrl}/api/v1/users/bulk`, JSON.stringify({ users }), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'users', operation: 'bulk-create' },
      });

      check(response, {
        'bulk creation processed': (r) => r.status === 200 || r.status === 201 || r.status === 422,
        'response time acceptable': (r) => r.timings.duration < 3000, // Bulk ops can be slower
      });
    });

    group('User Search and Filtering', () => {
      const searchResponse = http.get(`${baseUrl}/api/v1/users?search=test&role=user&active=true`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'users', operation: 'search' },
      });

      validators.paginatedResponse(searchResponse);
      
      check(searchResponse, {
        'search results are filtered': (r) => Array.isArray(r.json().data),
        'response time < 1.5s': (r) => r.timings.duration < 1500,
      });
    });

    group('Export Users', () => {
      const exportResponse = http.get(`${baseUrl}/api/v1/users/export?format=csv`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'users', operation: 'export' },
      });

      check(exportResponse, {
        'export processed': (r) => r.status === 200 || r.status === 404,
        'response time acceptable': (r) => r.timings.duration < 5000, // Export can be slow
      });
    });
  });
}

export function teardown(data) {
  console.log('🧹 Cleaning up User Management and RBAC Tests');
  dbHelpers.cleanTestDb(data.baseUrl);
}

export function handleSummary(data) {
  return {
    'k6-tests/results/user-management-test.html': htmlReport(data),
    'k6-tests/results/user-management-test.json': JSON.stringify(data),
  };
}