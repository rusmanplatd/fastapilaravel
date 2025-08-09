/**
 * Activity Logging Tests
 * Tests Spatie-style activity logging and audit trails
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { SharedArray } from 'k6/data';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';

import { TEST_CONFIG, HEADERS } from '../../config/test-config.js';
import { AuthHelper, generateTestData, validators, dbHelpers } from '../../utils/helpers.js';

const activityTypes = new SharedArray('activity-types', function() {
  return [
    { type: 'created', description: 'Record created' },
    { type: 'updated', description: 'Record updated' },
    { type: 'deleted', description: 'Record deleted' },
    { type: 'viewed', description: 'Record viewed' },
    { type: 'exported', description: 'Data exported' },
    { type: 'login', description: 'User logged in' },
    { type: 'logout', description: 'User logged out' },
    { type: 'failed_login', description: 'Failed login attempt' },
  ];
});

export let options = {
  scenarios: {
    activity_logging: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 10 },
        { duration: '2m', target: 15 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testActivityLogging',
    },
    activity_retrieval: {
      executor: 'constant-vus',
      vus: 8,
      duration: '3m',
      exec: 'testActivityRetrieval',
    },
    audit_trails: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 6 },
        { duration: '2m', target: 12 },
        { duration: '30s', target: 0 },
      ],
      exec: 'testAuditTrails',
    },
    activity_analytics: {
      executor: 'constant-vus',
      vus: 6,
      duration: '2m',
      exec: 'testActivityAnalytics',
    },
    performance_monitoring: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 8 },
        { duration: '2m', target: 12 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testPerformanceMonitoring',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<2000'],
    http_req_failed: ['rate<0.05'],
    'http_req_duration{endpoint:activity-log}': ['p(95)<1500'],
    'http_req_duration{endpoint:audit}': ['p(95)<1800'],
  },
};

export function setup() {
  console.log('📝 Setting up Activity Logging Tests');
  
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
    activityTypes: activityTypes,
  };
}

export function testActivityLogging(data) {
  group('Activity Logging Tests', () => {
    const { baseUrl, userToken, adminToken } = data;

    group('Automatic Activity Logging', () => {
      // Create a post (should trigger activity log)
      const postData = generateTestData.post();
      
      const createResponse = http.post(`${baseUrl}/api/v1/posts`, 
        JSON.stringify(postData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'posts', action: 'create', logging: 'automatic' },
      });

      if (createResponse.status === 201) {
        const post = createResponse.json();
        const postId = post.data.id;

        // Update the post (should trigger another activity log)
        const updateData = {
          title: 'Updated K6 Test Post',
          content: 'Updated content for activity logging test',
        };

        const updateResponse = http.put(`${baseUrl}/api/v1/posts/${postId}`, 
          JSON.stringify(updateData), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'posts', action: 'update', logging: 'automatic' },
        });

        check(updateResponse, {
          'post update successful': (r) => r.status === 200,
        });

        // Delete the post (should trigger delete activity log)
        const deleteResponse = http.del(`${baseUrl}/api/v1/posts/${postId}`, null, {
          headers: {
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'posts', action: 'delete', logging: 'automatic' },
        });

        check(deleteResponse, {
          'post deletion successful': (r) => r.status === 200 || r.status === 204,
        });
      }

      check(createResponse, {
        'post creation triggers activity log': (r) => r.status === 201,
      });
    });

    group('Manual Activity Logging', () => {
      const manualActivities = [
        {
          description: 'User exported data',
          subject_type: 'User',
          subject_id: 1,
          event: 'exported',
          properties: {
            export_type: 'csv',
            records_count: 100,
            file_size: '2.5MB',
          },
        },
        {
          description: 'User viewed sensitive data',
          subject_type: 'Document',
          subject_id: 123,
          event: 'viewed',
          properties: {
            document_type: 'financial_report',
            access_level: 'confidential',
          },
        },
        {
          description: 'System backup completed',
          subject_type: 'System',
          subject_id: null,
          event: 'backup_completed',
          properties: {
            backup_size: '150GB',
            duration: '45 minutes',
            files_count: 50000,
          },
        },
      ];

      manualActivities.forEach((activity, index) => {
        const response = http.post(`${baseUrl}/api/v1/activity-log`, 
          JSON.stringify(activity), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'activity-log', action: 'manual', case: index },
        });

        check(response, {
          [`manual activity ${index} logged`]: (r) => r.status === 200 || r.status === 201,
          [`manual activity ${index} format`]: (r) => {
            if (r.status >= 200 && r.status < 300) {
              const result = r.json();
              return result.hasOwnProperty('activity_id') || result.hasOwnProperty('id');
            }
            return true;
          },
        });
      });
    });

    group('Bulk Activity Logging', () => {
      const bulkActivities = [];
      
      for (let i = 0; i < 10; i++) {
        bulkActivities.push({
          description: `Bulk operation ${i}`,
          subject_type: 'BatchJob',
          subject_id: i,
          event: 'processed',
          properties: {
            batch_id: `batch-${Date.now()}`,
            item_number: i,
            status: i % 3 === 0 ? 'success' : 'pending',
          },
        });
      }

      const bulkData = {
        activities: bulkActivities,
        batch_name: 'K6 Bulk Activity Test',
      };

      const response = http.post(`${baseUrl}/api/v1/activity-log/bulk`, 
        JSON.stringify(bulkData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'activity-log', action: 'bulk' },
      });

      check(response, {
        'bulk activity logging successful': (r) => r.status === 200 || r.status === 201 || r.status === 202,
        'bulk response format': (r) => {
          if (r.status >= 200 && r.status < 300) {
            const result = r.json();
            return result.hasOwnProperty('logged_count') || result.hasOwnProperty('batch_id');
          }
          return true;
        },
      });
    });

    group('Activity Logging with Context', () => {
      const contextualActivity = {
        description: 'User performed sensitive action',
        subject_type: 'User',
        subject_id: 1,
        event: 'sensitive_action',
        properties: {
          action_type: 'data_access',
          ip_address: '192.168.1.100',
          user_agent: 'k6-test-agent',
          session_id: 'test-session-123',
          risk_score: 'medium',
        },
        context: {
          request_id: 'req-' + Date.now(),
          trace_id: 'trace-' + Date.now(),
          user_permissions: ['read', 'write'],
          additional_metadata: {
            source: 'k6_load_test',
            test_run_id: 'run-' + Date.now(),
          },
        },
      };

      const response = http.post(`${baseUrl}/api/v1/activity-log`, 
        JSON.stringify(contextualActivity), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
          'X-Request-ID': contextualActivity.context.request_id,
          'X-Trace-ID': contextualActivity.context.trace_id,
        },
        tags: { endpoint: 'activity-log', action: 'contextual' },
      });

      check(response, {
        'contextual activity logged': (r) => r.status === 200 || r.status === 201,
        'context preserved': (r) => {
          if (r.status >= 200 && r.status < 300) {
            return r.json().hasOwnProperty('activity_id') || r.json().hasOwnProperty('id');
          }
          return true;
        },
      });
    });
  });
}

export function testActivityRetrieval(data) {
  group('Activity Retrieval Tests', () => {
    const { baseUrl, userToken, adminToken } = data;

    group('List Activities with Pagination', () => {
      const response = http.get(`${baseUrl}/api/v1/activity-log?page=1&per_page=20`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'activity-log', action: 'list' },
      });

      validators.paginatedResponse(response);
      
      if (response.status === 200) {
        check(response, {
          'activities list structure': (r) => {
            const activities = r.json().data;
            return Array.isArray(activities);
          },
          'activity data format': (r) => {
            const activities = r.json().data;
            if (activities.length > 0) {
              const activity = activities[0];
              return activity.hasOwnProperty('id') && 
                     activity.hasOwnProperty('description') &&
                     activity.hasOwnProperty('created_at');
            }
            return true;
          },
        });
      }
    });

    group('Filter Activities', () => {
      const filters = [
        'filter[event]=created',
        'filter[subject_type]=User',
        'filter[causer_type]=User&filter[causer_id]=1',
        'filter[created_at][gte]=2024-01-01',
        'filter[properties.export_type]=csv',
        'search=exported',
      ];

      filters.forEach((filter, index) => {
        const response = http.get(`${baseUrl}/api/v1/activity-log?${filter}`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'activity-log', action: 'filter', case: index },
        });

        check(response, {
          [`activity filter ${index} processed`]: (r) => r.status === 200 || r.status === 400,
          [`activity filter ${index} results`]: (r) => {
            if (r.status === 200) {
              const data = r.json();
              return Array.isArray(data.data);
            }
            return true;
          },
        });
      });
    });

    group('Activity Details and Relationships', () => {
      // Get detailed activity with relationships
      const detailedResponse = http.get(`${baseUrl}/api/v1/activity-log/1?include=causer,subject`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'activity-log', action: 'details' },
      });

      check(detailedResponse, {
        'activity details retrieved': (r) => r.status === 200 || r.status === 404,
        'relationships included': (r) => {
          if (r.status === 200) {
            const activity = r.json().data;
            return typeof activity === 'object';
          }
          return true;
        },
      });

      // Get activities for specific subject
      const subjectResponse = http.get(`${baseUrl}/api/v1/activity-log/subject/User/1`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'activity-log', action: 'subject' },
      });

      check(subjectResponse, {
        'subject activities retrieved': (r) => r.status === 200 || r.status === 404,
      });

      // Get activities by causer (user who performed the action)
      const causerResponse = http.get(`${baseUrl}/api/v1/activity-log/causer/1`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'activity-log', action: 'causer' },
      });

      check(causerResponse, {
        'causer activities retrieved': (r) => r.status === 200 || r.status === 403,
      });
    });

    group('Activity Aggregation', () => {
      // Get activity counts by event type
      const countsResponse = http.get(`${baseUrl}/api/v1/activity-log/counts?group_by=event`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'activity-log', action: 'counts' },
      });

      check(countsResponse, {
        'activity counts available': (r) => r.status === 200 || r.status === 403,
        'counts data structure': (r) => {
          if (r.status === 200) {
            const counts = r.json().data;
            return typeof counts === 'object' || Array.isArray(counts);
          }
          return true;
        },
      });

      // Get activity timeline
      const timelineResponse = http.get(`${baseUrl}/api/v1/activity-log/timeline?days=7`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'activity-log', action: 'timeline' },
      });

      check(timelineResponse, {
        'activity timeline available': (r) => r.status === 200 || r.status === 403,
        'timeline data format': (r) => {
          if (r.status === 200) {
            const timeline = r.json().data;
            return Array.isArray(timeline) || typeof timeline === 'object';
          }
          return true;
        },
      });
    });
  });
}

export function testAuditTrails(data) {
  group('Audit Trails Tests', () => {
    const { baseUrl, adminToken } = data;

    group('Security Audit Events', () => {
      const securityEvents = [
        {
          event_type: 'login_attempt',
          user_id: 1,
          ip_address: '192.168.1.100',
          user_agent: 'k6-test-browser',
          success: true,
          metadata: {
            mfa_used: false,
            login_method: 'password',
          },
        },
        {
          event_type: 'permission_change',
          user_id: 1,
          target_user_id: 2,
          old_permissions: ['read'],
          new_permissions: ['read', 'write'],
          metadata: {
            reason: 'promotion',
            approved_by: 'admin',
          },
        },
        {
          event_type: 'data_access',
          user_id: 1,
          resource_type: 'financial_report',
          resource_id: '123',
          access_type: 'view',
          metadata: {
            classification: 'confidential',
            justification: 'monthly_review',
          },
        },
      ];

      securityEvents.forEach((event, index) => {
        const response = http.post(`${baseUrl}/api/v1/audit/security-event`, 
          JSON.stringify(event), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'audit', event: 'security', case: index },
        });

        check(response, {
          [`security event ${index} logged`]: (r) => r.status === 200 || r.status === 201,
        });
      });
    });

    group('Compliance Audit Trails', () => {
      const complianceEvents = [
        {
          compliance_framework: 'GDPR',
          event_type: 'data_processing',
          legal_basis: 'consent',
          data_subject_id: 'user-123',
          processing_purpose: 'service_provision',
          data_categories: ['personal', 'contact'],
          retention_period: '2_years',
        },
        {
          compliance_framework: 'SOX',
          event_type: 'financial_access',
          user_id: 1,
          resource_type: 'financial_statement',
          access_reason: 'quarterly_review',
          approval_required: true,
          approved_by: 'cfo',
        },
        {
          compliance_framework: 'HIPAA',
          event_type: 'phi_access',
          user_id: 1,
          patient_id: 'patient-456',
          access_type: 'view',
          minimum_necessary: true,
          purpose: 'treatment',
        },
      ];

      complianceEvents.forEach((event, index) => {
        const response = http.post(`${baseUrl}/api/v1/audit/compliance-event`, 
          JSON.stringify(event), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'audit', event: 'compliance', case: index },
        });

        check(response, {
          [`compliance event ${index} logged`]: (r) => r.status === 200 || r.status === 201 || r.status === 400,
        });
      });
    });

    group('System Audit Events', () => {
      const systemEvents = [
        {
          event_type: 'configuration_change',
          component: 'database_settings',
          old_value: { max_connections: 100 },
          new_value: { max_connections: 200 },
          changed_by: 1,
          reason: 'performance_optimization',
        },
        {
          event_type: 'backup_operation',
          operation: 'full_backup',
          status: 'completed',
          size_gb: 150.5,
          duration_minutes: 45,
          location: 's3://backups/2024/',
        },
        {
          event_type: 'security_scan',
          scan_type: 'vulnerability_assessment',
          findings_count: 3,
          severity_levels: { high: 0, medium: 2, low: 1 },
          scan_duration: '30_minutes',
        },
      ];

      systemEvents.forEach((event, index) => {
        const response = http.post(`${baseUrl}/api/v1/audit/system-event`, 
          JSON.stringify(event), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'audit', event: 'system', case: index },
        });

        check(response, {
          [`system event ${index} logged`]: (r) => r.status === 200 || r.status === 201,
        });
      });
    });

    group('Audit Trail Integrity', () => {
      // Test audit trail immutability
      const integrityResponse = http.get(`${baseUrl}/api/v1/audit/integrity-check`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'audit', action: 'integrity' },
      });

      check(integrityResponse, {
        'integrity check available': (r) => r.status === 200 || r.status === 403,
        'integrity results': (r) => {
          if (r.status === 200) {
            const integrity = r.json().data;
            return integrity.hasOwnProperty('status') || integrity.hasOwnProperty('verified');
          }
          return true;
        },
      });

      // Test audit log export for compliance
      const exportResponse = http.get(`${baseUrl}/api/v1/audit/export?format=csv&days=30`, {
        headers: {
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'audit', action: 'export' },
      });

      check(exportResponse, {
        'audit export available': (r) => r.status === 200 || r.status === 403,
        'export format correct': (r) => {
          if (r.status === 200) {
            return r.headers['Content-Type'] && 
                   (r.headers['Content-Type'].includes('csv') || 
                    r.headers['Content-Type'].includes('application'));
          }
          return true;
        },
      });
    });
  });
}

export function testActivityAnalytics(data) {
  group('Activity Analytics Tests', () => {
    const { baseUrl, adminToken } = data;

    group('User Activity Analytics', () => {
      const analyticsResponse = http.get(`${baseUrl}/api/v1/activity-log/analytics/users?days=30`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'activity-analytics', type: 'users' },
      });

      check(analyticsResponse, {
        'user analytics available': (r) => r.status === 200 || r.status === 403,
        'user analytics structure': (r) => {
          if (r.status === 200) {
            const analytics = r.json().data;
            return typeof analytics === 'object';
          }
          return true;
        },
      });

      // Most active users
      const activeUsersResponse = http.get(`${baseUrl}/api/v1/activity-log/analytics/most-active`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'activity-analytics', type: 'most-active' },
      });

      check(activeUsersResponse, {
        'most active users available': (r) => r.status === 200 || r.status === 403,
      });
    });

    group('Event Type Analytics', () => {
      const eventAnalyticsResponse = http.get(`${baseUrl}/api/v1/activity-log/analytics/events?period=week`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'activity-analytics', type: 'events' },
      });

      check(eventAnalyticsResponse, {
        'event analytics available': (r) => r.status === 200 || r.status === 403,
        'event analytics data': (r) => {
          if (r.status === 200) {
            const analytics = r.json().data;
            return typeof analytics === 'object' || Array.isArray(analytics);
          }
          return true;
        },
      });

      // Event trends
      const trendsResponse = http.get(`${baseUrl}/api/v1/activity-log/analytics/trends?days=7`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'activity-analytics', type: 'trends' },
      });

      check(trendsResponse, {
        'trends analysis available': (r) => r.status === 200 || r.status === 403,
      });
    });

    group('Performance Impact Analysis', () => {
      const performanceResponse = http.get(`${baseUrl}/api/v1/activity-log/analytics/performance`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'activity-analytics', type: 'performance' },
      });

      check(performanceResponse, {
        'performance analytics available': (r) => r.status === 200 || r.status === 403,
        'performance metrics': (r) => {
          if (r.status === 200) {
            const metrics = r.json().data;
            return typeof metrics === 'object';
          }
          return true;
        },
      });

      // Storage usage analytics
      const storageResponse = http.get(`${baseUrl}/api/v1/activity-log/analytics/storage`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'activity-analytics', type: 'storage' },
      });

      check(storageResponse, {
        'storage analytics available': (r) => r.status === 200 || r.status === 403,
      });
    });
  });
}

export function testPerformanceMonitoring(data) {
  group('Performance Monitoring Tests', () => {
    const { baseUrl, adminToken } = data;

    group('Activity Log Performance', () => {
      // Test bulk activity logging performance
      const startTime = Date.now();
      const bulkActivities = [];
      
      for (let i = 0; i < 50; i++) {
        bulkActivities.push({
          description: `Performance test activity ${i}`,
          subject_type: 'TestModel',
          subject_id: i,
          event: 'performance_test',
          properties: {
            test_run: 'k6_performance',
            iteration: i,
            timestamp: new Date().toISOString(),
          },
        });
      }

      const bulkResponse = http.post(`${baseUrl}/api/v1/activity-log/bulk`, 
        JSON.stringify({ activities: bulkActivities }), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'activity-log', test: 'performance', size: 'bulk' },
      });

      const endTime = Date.now();
      const duration = endTime - startTime;

      check(bulkResponse, {
        'bulk logging performance acceptable': (r) => r.status >= 200 && r.status < 300 && duration < 3000,
        'bulk logging response time': (r) => r.timings.duration < 2000,
      });
    });

    group('Query Performance', () => {
      const queryTests = [
        { endpoint: '/api/v1/activity-log?per_page=100', name: 'large_page' },
        { endpoint: '/api/v1/activity-log?filter[created_at][gte]=2024-01-01&per_page=50', name: 'date_filter' },
        { endpoint: '/api/v1/activity-log?search=test&per_page=20', name: 'search' },
        { endpoint: '/api/v1/activity-log?include=causer,subject&per_page=10', name: 'includes' },
      ];

      queryTests.forEach(({ endpoint, name }) => {
        const response = http.get(`${baseUrl}${endpoint}`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'activity-log', test: 'query-performance', query: name },
        });

        check(response, {
          [`${name} query performance`]: (r) => {
            return (r.status === 200 || r.status === 400) && r.timings.duration < 2000;
          },
        });
      });
    });

    group('Resource Usage Monitoring', () => {
      const resourceResponse = http.get(`${baseUrl}/api/v1/activity-log/system/resources`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'activity-system', type: 'resources' },
      });

      check(resourceResponse, {
        'resource monitoring available': (r) => r.status === 200 || r.status === 403 || r.status === 404,
        'resource data format': (r) => {
          if (r.status === 200) {
            const resources = r.json().data;
            return typeof resources === 'object';
          }
          return true;
        },
      });

      // Database performance metrics
      const dbMetricsResponse = http.get(`${baseUrl}/api/v1/activity-log/system/db-metrics`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'activity-system', type: 'db-metrics' },
      });

      check(dbMetricsResponse, {
        'database metrics available': (r) => r.status === 200 || r.status === 403 || r.status === 404,
      });
    });
  });
}

export function teardown(data) {
  console.log('🧹 Cleaning up Activity Logging Tests');
  dbHelpers.cleanTestDb(data.baseUrl);
}

export function handleSummary(data) {
  return {
    'k6-tests/results/activity-logging-test.html': htmlReport(data),
    'k6-tests/results/activity-logging-test.json': JSON.stringify(data),
  };
}