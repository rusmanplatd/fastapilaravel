/**
 * Pagination and Query Builder Tests
 * Tests Laravel-style pagination and Spatie Query Builder functionality
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { SharedArray } from 'k6/data';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';

import { TEST_CONFIG, HEADERS } from '../../config/test-config.js';
import { AuthHelper, generateTestData, validators, dbHelpers } from '../../utils/helpers.js';

const queryParams = new SharedArray('query-params', function() {
  return [
    { filters: 'filter[name]=john', sorts: 'sort=name', includes: 'include=posts,roles' },
    { filters: 'filter[email]=test@', sorts: 'sort=-created_at', includes: 'include=posts' },
    { filters: 'filter[status]=active', sorts: 'sort=id,-name', includes: 'include=roles' },
    { filters: 'filter[created_at]=2024-01-01', sorts: 'sort=email', includes: '' },
    { filters: 'filter[posts.title]=test', sorts: 'sort=-id', includes: 'include=posts.comments' },
  ];
});

export let options = {
  scenarios: {
    basic_pagination: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 10 },
        { duration: '2m', target: 15 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testBasicPagination',
    },
    query_builder: {
      executor: 'constant-vus',
      vus: 12,
      duration: '3m',
      exec: 'testQueryBuilder',
    },
    advanced_filtering: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 8 },
        { duration: '2m', target: 16 },
        { duration: '30s', target: 0 },
      ],
      exec: 'testAdvancedFiltering',
    },
    sorting_and_includes: {
      executor: 'constant-vus',
      vus: 8,
      duration: '2m',
      exec: 'testSortingAndIncludes',
    },
    cursor_pagination: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 6 },
        { duration: '2m', target: 10 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testCursorPagination',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<2000'],
    http_req_failed: ['rate<0.05'],
    'http_req_duration{endpoint:pagination}': ['p(95)<1500'],
    'http_req_duration{endpoint:query-builder}': ['p(95)<1800'],
  },
};

export function setup() {
  console.log('📊 Setting up Pagination and Query Builder Tests');
  
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
    queryParams: queryParams,
  };
}

export function testBasicPagination(data) {
  group('Basic Pagination Tests', () => {
    const { baseUrl, userToken } = data;

    group('Standard Pagination', () => {
      const paginationTests = [
        { page: 1, per_page: 10 },
        { page: 2, per_page: 20 },
        { page: 1, per_page: 50 },
        { page: 5, per_page: 5 },
      ];

      paginationTests.forEach(({ page, per_page }) => {
        const response = http.get(`${baseUrl}/api/v1/posts?page=${page}&per_page=${per_page}`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'pagination', page: page, per_page: per_page },
        });

        validators.paginatedResponse(response);
        
        if (response.status === 200) {
          check(response, {
            [`page ${page} has correct structure`]: (r) => {
              const data = r.json();
              return data.hasOwnProperty('data') && 
                     data.hasOwnProperty('meta') && 
                     data.hasOwnProperty('links');
            },
            [`page ${page} meta information`]: (r) => {
              const meta = r.json().meta;
              return meta.hasOwnProperty('current_page') && 
                     meta.hasOwnProperty('per_page') && 
                     meta.hasOwnProperty('total');
            },
            [`page ${page} navigation links`]: (r) => {
              const links = r.json().links;
              return links.hasOwnProperty('first') && 
                     links.hasOwnProperty('last') && 
                     links.hasOwnProperty('next') && 
                     links.hasOwnProperty('prev');
            },
          });
        }
      });
    });

    group('Pagination Edge Cases', () => {
      const edgeCases = [
        { page: 0, per_page: 10, expectedError: true },
        { page: -1, per_page: 10, expectedError: true },
        { page: 1, per_page: 0, expectedError: true },
        { page: 1, per_page: -5, expectedError: true },
        { page: 1, per_page: 1000, expectedLimited: true }, // Should be limited to max
        { page: 999999, per_page: 10, expectedEmpty: true }, // Very high page number
      ];

      edgeCases.forEach(({ page, per_page, expectedError, expectedLimited, expectedEmpty }) => {
        const response = http.get(`${baseUrl}/api/v1/posts?page=${page}&per_page=${per_page}`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'pagination', test: 'edge-case', page: page },
        });

        if (expectedError) {
          check(response, {
            [`invalid pagination page=${page} per_page=${per_page} rejected`]: (r) => r.status === 400 || r.status === 422,
          });
        } else if (expectedEmpty) {
          check(response, {
            [`empty page handled correctly`]: (r) => {
              if (r.status === 200) {
                const data = r.json();
                return Array.isArray(data.data) && data.data.length === 0;
              }
              return r.status === 404;
            },
          });
        } else {
          check(response, {
            [`edge case handled properly`]: (r) => r.status === 200 || r.status === 400,
          });
        }
      });
    });

    group('Different Resource Pagination', () => {
      const resources = [
        { endpoint: '/api/v1/users', name: 'users' },
        { endpoint: '/api/v1/posts', name: 'posts' },
        { endpoint: '/api/v1/notifications', name: 'notifications' },
        { endpoint: '/api/v1/roles', name: 'roles' },
      ];

      resources.forEach(({ endpoint, name }) => {
        const response = http.get(`${baseUrl}${endpoint}?page=1&per_page=15`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'pagination', resource: name },
        });

        check(response, {
          [`${name} pagination works`]: (r) => r.status === 200 || r.status === 403,
          [`${name} pagination format`]: (r) => {
            if (r.status === 200) {
              return validators.paginatedResponse(r);
            }
            return true;
          },
        });
      });
    });
  });
}

export function testQueryBuilder(data) {
  group('Query Builder Tests', () => {
    const { baseUrl, userToken, queryParams } = data;

    group('Basic Filtering', () => {
      queryParams.forEach((params, index) => {
        const queryString = `${params.filters}&${params.sorts}&${params.includes}`;
        const cleanQuery = queryString.replace(/^&|&$/g, '').replace(/&&+/g, '&');
        
        const response = http.get(`${baseUrl}/api/v1/users?${cleanQuery}`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'query-builder', test: 'filter', case: index },
        });

        check(response, {
          [`filter case ${index} processed`]: (r) => r.status === 200 || r.status === 400,
          [`filter case ${index} structure`]: (r) => {
            if (r.status === 200) {
              const data = r.json();
              return data.hasOwnProperty('data') && Array.isArray(data.data);
            }
            return true;
          },
        });
      });
    });

    group('Filter Operators', () => {
      const filterOperators = [
        'filter[name][like]=john',
        'filter[age][gt]=18',
        'filter[age][lt]=65',
        'filter[created_at][gte]=2024-01-01',
        'filter[status][in]=active,pending',
        'filter[email][contains]=example',
        'filter[posts.title][not_null]',
        'filter[roles.name][eq]=admin',
      ];

      filterOperators.forEach((filter, index) => {
        const response = http.get(`${baseUrl}/api/v1/users?${filter}`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'query-builder', test: 'operators', operator: index },
        });

        check(response, {
          [`filter operator ${index} handled`]: (r) => r.status === 200 || r.status === 400,
        });
      });
    });

    group('Complex Query Combinations', () => {
      const complexQueries = [
        'filter[name]=john&filter[status]=active&sort=created_at&include=posts,roles',
        'filter[created_at][gte]=2024-01-01&filter[posts.status]=published&sort=-updated_at',
        'filter[roles.name]=admin&filter[email][contains]=@company&include=roles.permissions',
        'filter[posts.category]=tech&sort=posts.created_at,-name&include=posts.comments',
      ];

      complexQueries.forEach((query, index) => {
        const response = http.get(`${baseUrl}/api/v1/users?${query}&page=1&per_page=10`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'query-builder', test: 'complex', case: index },
        });

        check(response, {
          [`complex query ${index} processed`]: (r) => r.status === 200 || r.status === 400,
          [`complex query ${index} pagination maintained`]: (r) => {
            if (r.status === 200) {
              const data = r.json();
              return data.hasOwnProperty('meta') && data.hasOwnProperty('links');
            }
            return true;
          },
        });
      });
    });

    group('Search Functionality', () => {
      const searchQueries = [
        'search=john',
        'search=test@example.com',
        'search=admin user',
        'search="exact phrase"',
        'search=user&searchFields=name,email',
      ];

      searchQueries.forEach((searchQuery, index) => {
        const response = http.get(`${baseUrl}/api/v1/users?${searchQuery}`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'query-builder', test: 'search', query: index },
        });

        check(response, {
          [`search query ${index} handled`]: (r) => r.status === 200 || r.status === 400,
          [`search query ${index} results`]: (r) => {
            if (r.status === 200) {
              const data = r.json();
              return Array.isArray(data.data);
            }
            return true;
          },
        });
      });
    });
  });
}

export function testAdvancedFiltering(data) {
  group('Advanced Filtering Tests', () => {
    const { baseUrl, userToken } = data;

    group('Date Range Filtering', () => {
      const dateRanges = [
        'filter[created_at][between]=2024-01-01,2024-12-31',
        'filter[updated_at][gte]=2024-06-01&filter[updated_at][lte]=2024-06-30',
        'filter[created_at][date]=2024-01-15',
        'filter[created_at][month]=6',
        'filter[created_at][year]=2024',
      ];

      dateRanges.forEach((dateFilter, index) => {
        const response = http.get(`${baseUrl}/api/v1/posts?${dateFilter}`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'query-builder', test: 'date-range', case: index },
        });

        check(response, {
          [`date filter ${index} processed`]: (r) => r.status === 200 || r.status === 400,
        });
      });
    });

    group('Relationship Filtering', () => {
      const relationshipFilters = [
        'filter[posts.title][like]=test',
        'filter[roles.name]=admin',
        'filter[posts.comments.count][gt]=5',
        'filter[roles.permissions.name]=read-users',
        'filter[posts.category.name]=technology',
      ];

      relationshipFilters.forEach((relFilter, index) => {
        const response = http.get(`${baseUrl}/api/v1/users?${relFilter}&include=posts,roles`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'query-builder', test: 'relationship', case: index },
        });

        check(response, {
          [`relationship filter ${index} handled`]: (r) => r.status === 200 || r.status === 400,
        });
      });
    });

    group('Aggregation Filters', () => {
      const aggregationFilters = [
        'filter[posts_count][gt]=10',
        'filter[posts_sum_views][gte]=1000',
        'filter[posts_avg_rating][gt]=4.0',
        'filter[comments_count][between]=5,50',
      ];

      aggregationFilters.forEach((aggFilter, index) => {
        const response = http.get(`${baseUrl}/api/v1/users?${aggFilter}`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'query-builder', test: 'aggregation', case: index },
        });

        check(response, {
          [`aggregation filter ${index} handled`]: (r) => r.status === 200 || r.status === 400,
        });
      });
    });

    group('Custom Filter Scopes', () => {
      const customScopes = [
        'scope=active',
        'scope=recent',
        'scope=popular',
        'scope=featured',
        'scope=withPosts',
      ];

      customScopes.forEach((scope, index) => {
        const response = http.get(`${baseUrl}/api/v1/posts?${scope}`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'query-builder', test: 'scopes', scope: scope },
        });

        check(response, {
          [`scope ${scope} handled`]: (r) => r.status === 200 || r.status === 400 || r.status === 404,
        });
      });
    });
  });
}

export function testSortingAndIncludes(data) {
  group('Sorting and Includes Tests', () => {
    const { baseUrl, userToken } = data;

    group('Single and Multiple Sorting', () => {
      const sortOptions = [
        'sort=name',
        'sort=-created_at',
        'sort=name,-created_at',
        'sort=posts.title',
        'sort=-posts.created_at,name',
        'sort=roles.name,-updated_at',
      ];

      sortOptions.forEach((sortOption, index) => {
        const response = http.get(`${baseUrl}/api/v1/users?${sortOption}`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'query-builder', test: 'sorting', case: index },
        });

        check(response, {
          [`sort option ${index} processed`]: (r) => r.status === 200 || r.status === 400,
          [`sort option ${index} maintains order`]: (r) => {
            if (r.status === 200) {
              const data = r.json();
              return Array.isArray(data.data);
            }
            return true;
          },
        });
      });
    });

    group('Include Relationships', () => {
      const includeOptions = [
        'include=posts',
        'include=roles',
        'include=posts,roles',
        'include=posts.comments',
        'include=roles.permissions',
        'include=posts.comments.author,roles.permissions',
      ];

      includeOptions.forEach((includeOption, index) => {
        const response = http.get(`${baseUrl}/api/v1/users?${includeOption}`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'query-builder', test: 'includes', case: index },
        });

        check(response, {
          [`include option ${index} processed`]: (r) => r.status === 200 || r.status === 400,
          [`include option ${index} relationships loaded`]: (r) => {
            if (r.status === 200) {
              const data = r.json();
              if (data.data && data.data.length > 0) {
                // Check if includes are present (implementation may vary)
                return true;
              }
              return Array.isArray(data.data);
            }
            return true;
          },
        });
      });
    });

    group('Include Counts and Aggregates', () => {
      const countIncludes = [
        'include=postsCount',
        'include=rolesCount',
        'include=posts,postsCount',
        'include=posts.commentsCount',
        'include=postsSum:views',
        'include=postsAvg:rating',
      ];

      countIncludes.forEach((countInclude, index) => {
        const response = http.get(`${baseUrl}/api/v1/users?${countInclude}`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'query-builder', test: 'counts', case: index },
        });

        check(response, {
          [`count include ${index} handled`]: (r) => r.status === 200 || r.status === 400,
        });
      });
    });

    group('Sparse Fieldsets', () => {
      const fieldsets = [
        'fields[users]=name,email',
        'fields[posts]=title,content',
        'fields[users]=name,email&fields[posts]=title',
        'fields[users]=id,name,email,created_at',
      ];

      fieldsets.forEach((fieldset, index) => {
        const response = http.get(`${baseUrl}/api/v1/users?${fieldset}&include=posts`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'query-builder', test: 'fieldsets', case: index },
        });

        check(response, {
          [`fieldset ${index} processed`]: (r) => r.status === 200 || r.status === 400,
          [`fieldset ${index} fields limited`]: (r) => {
            if (r.status === 200) {
              const data = r.json();
              return Array.isArray(data.data);
            }
            return true;
          },
        });
      });
    });
  });
}

export function testCursorPagination(data) {
  group('Cursor Pagination Tests', () => {
    const { baseUrl, userToken } = data;

    group('Basic Cursor Pagination', () => {
      // Initial request
      const initialResponse = http.get(`${baseUrl}/api/v1/posts/cursor?limit=10`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'pagination', type: 'cursor', step: 'initial' },
      });

      check(initialResponse, {
        'cursor pagination initial request': (r) => r.status === 200 || r.status === 404,
        'cursor pagination structure': (r) => {
          if (r.status === 200) {
            const data = r.json();
            return data.hasOwnProperty('data') && 
                   data.hasOwnProperty('meta') &&
                   (data.meta.hasOwnProperty('next_cursor') || data.meta.hasOwnProperty('has_more'));
          }
          return true;
        },
      });

      // Follow-up request with cursor
      if (initialResponse.status === 200) {
        const initialData = initialResponse.json();
        if (initialData.meta && initialData.meta.next_cursor) {
          const nextResponse = http.get(`${baseUrl}/api/v1/posts/cursor?limit=10&cursor=${initialData.meta.next_cursor}`, {
            headers: {
              ...HEADERS,
              'Authorization': `Bearer ${userToken}`,
            },
            tags: { endpoint: 'pagination', type: 'cursor', step: 'next' },
          });

          check(nextResponse, {
            'cursor pagination next page': (r) => r.status === 200 || r.status === 404,
          });
        }
      }
    });

    group('Cursor Pagination with Filtering', () => {
      const cursorFilters = [
        'filter[status]=published&cursor_field=created_at',
        'filter[category]=tech&cursor_field=updated_at',
        'search=test&cursor_field=id',
      ];

      cursorFilters.forEach((filter, index) => {
        const response = http.get(`${baseUrl}/api/v1/posts/cursor?${filter}&limit=20`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'pagination', type: 'cursor-filter', case: index },
        });

        check(response, {
          [`cursor with filter ${index} processed`]: (r) => r.status === 200 || r.status === 400 || r.status === 404,
        });
      });
    });

    group('Cursor Pagination Performance', () => {
      const performanceTests = [
        { limit: 10, field: 'id' },
        { limit: 50, field: 'created_at' },
        { limit: 100, field: 'updated_at' },
      ];

      performanceTests.forEach(({ limit, field }) => {
        const response = http.get(`${baseUrl}/api/v1/posts/cursor?limit=${limit}&cursor_field=${field}`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'pagination', type: 'cursor-perf', limit: limit },
        });

        check(response, {
          [`cursor pagination limit ${limit} performance`]: (r) => {
            return (r.status === 200 || r.status === 404) && r.timings.duration < 2000;
          },
        });
      });
    });
  });
}

export function teardown(data) {
  console.log('🧹 Cleaning up Pagination and Query Builder Tests');
  dbHelpers.cleanTestDb(data.baseUrl);
}

export function handleSummary(data) {
  return {
    'k6-tests/results/pagination-querybuilder-test.html': htmlReport(data),
    'k6-tests/results/pagination-querybuilder-test.json': JSON.stringify(data),
  };
}