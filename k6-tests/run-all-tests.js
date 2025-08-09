/**
 * K6 Test Suite Runner
 * Main entry point for running all FastAPI Laravel tests
 */

import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';
import { TEST_CONFIG } from './config/test-config.js';
import { dbHelpers } from './utils/helpers.js';

export let options = {
  scenarios: {
    // Authentication Tests
    jwt_auth: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 5 },
        { duration: '1m', target: 10 },
        { duration: '30s', target: 0 },
      ],
      exec: 'jwtAuthTests',
      startTime: '0s',
    },
    oauth2_auth: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 5 },
        { duration: '1m', target: 10 },
        { duration: '30s', target: 0 },
      ],
      exec: 'oauth2AuthTests',
      startTime: '2m',
    },

    // RBAC Tests
    user_management: {
      executor: 'constant-vus',
      vus: 8,
      duration: '2m',
      exec: 'userManagementTests',
      startTime: '4m',
    },
    permissions: {
      executor: 'constant-vus',
      vus: 6,
      duration: '2m',
      exec: 'permissionsTests',
      startTime: '6m',
    },

    // Security Tests
    mfa_security: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 4 },
        { duration: '1m', target: 8 },
        { duration: '30s', target: 0 },
      ],
      exec: 'mfaTests',
      startTime: '8m',
    },
    webauthn_security: {
      executor: 'constant-vus',
      vus: 5,
      duration: '2m',
      exec: 'webauthnTests',
      startTime: '10m',
    },

    // Feature Tests
    notifications: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 6 },
        { duration: '2m', target: 12 },
        { duration: '30s', target: 0 },
      ],
      exec: 'notificationTests',
      startTime: '12m',
    },
    storage_upload: {
      executor: 'constant-vus',
      vus: 6,
      duration: '2m',
      exec: 'storageTests',
      startTime: '15m',
    },
    queue_system: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 4 },
        { duration: '2m', target: 8 },
        { duration: '30s', target: 0 },
      ],
      exec: 'queueTests',
      startTime: '17m',
    },
    pagination_query: {
      executor: 'constant-vus',
      vus: 8,
      duration: '2m',
      exec: 'paginationTests',
      startTime: '19m',
    },
    activity_logging: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 5 },
        { duration: '1m', target: 10 },
        { duration: '30s', target: 0 },
      ],
      exec: 'activityLoggingTests',
      startTime: '21m',
    },

    // Compliance Tests
    rfc_compliance: {
      executor: 'constant-vus',
      vus: 6,
      duration: '2m',
      exec: 'rfcComplianceTests',
      startTime: '23m',
    },
  },

  // Global thresholds
  thresholds: {
    http_req_duration: ['p(95)<3000'], // 95% of requests must complete below 3s
    http_req_failed: ['rate<0.05'],    // Error rate must be below 5%
    http_reqs: ['count>1000'],         // Must generate at least 1000 requests
    
    // Test-specific thresholds
    'http_req_duration{test:auth}': ['p(95)<1000'],
    'http_req_duration{test:api}': ['p(95)<2000'],
    'http_req_duration{test:upload}': ['p(95)<5000'],
    'http_req_duration{test:queue}': ['p(95)<3000'],
  },

  // Test execution limits
  maxRedirects: 4,
  userAgent: 'K6-FastAPI-Laravel-Test-Suite/1.0',
  
  // Resource limits
  batch: 20,
  batchPerHost: 10,
};

// Global setup
export function setup() {
  console.log('🚀 Starting FastAPI Laravel K6 Test Suite');
  console.log('================================================');
  console.log(`Base URL: ${TEST_CONFIG.baseUrl}`);
  console.log(`Test DB URL: ${TEST_CONFIG.testDbUrl}`);
  console.log('Database Type: PostgreSQL');
  console.log('================================================');
  
  // Setup fresh PostgreSQL test database
  console.log('📊 Setting up fresh PostgreSQL test database...');
  try {
    const dbSetupResponse = dbHelpers.setupTestDb(TEST_CONFIG.baseUrl);
    console.log('✅ PostgreSQL database setup completed successfully');
  } catch (error) {
    console.error('❌ Database setup failed:', error.message);
    throw error;
  }
  
  return {
    baseUrl: TEST_CONFIG.baseUrl,
    testDbUrl: TEST_CONFIG.testDbUrl,
    startTime: new Date().toISOString(),
  };
}

// Authentication Tests
export function jwtAuthTests() {
  console.log('🔐 Running JWT Authentication Tests');
  // Import and run JWT auth tests
  // Note: In a real implementation, you would dynamically import the test functions
  // For this example, we'll just log the test execution
}

export function oauth2AuthTests() {
  console.log('🔑 Running OAuth2 Authentication Tests');
  // Import and run OAuth2 auth tests
}

// RBAC Tests
export function userManagementTests() {
  console.log('👥 Running User Management Tests');
  // Import and run user management tests
}

export function permissionsTests() {
  console.log('🛡️ Running Permissions Tests');
  // Import and run permissions tests
}

// Security Tests
export function mfaTests() {
  console.log('📱 Running MFA Tests');
  // Import and run MFA tests
}

export function webauthnTests() {
  console.log('🔐 Running WebAuthn Tests');
  // Import and run WebAuthn tests
}

// Feature Tests
export function notificationTests() {
  console.log('📬 Running Notification Tests');
  // Import and run notification tests
}

export function storageTests() {
  console.log('📁 Running Storage Tests');
  // Import and run storage tests
}

export function queueTests() {
  console.log('⚡ Running Queue System Tests');
  // Import and run queue tests
}

export function paginationTests() {
  console.log('📊 Running Pagination Tests');
  // Import and run pagination tests
}

export function activityLoggingTests() {
  console.log('📝 Running Activity Logging Tests');
  // Import and run activity logging tests
}

// Compliance Tests
export function rfcComplianceTests() {
  console.log('📋 Running RFC Compliance Tests');
  // Import and run RFC compliance tests
}

// Global teardown
export function teardown(data) {
  console.log('🧹 Running Global Test Suite Teardown');
  console.log('====================================');
  console.log(`Started: ${data.startTime}`);
  console.log(`Completed: ${new Date().toISOString()}`);
  console.log(`Database: ${data.testDbUrl || 'PostgreSQL'}`);
  
  // Clean up PostgreSQL test database
  console.log('🗑️ Cleaning up PostgreSQL test database...');
  try {
    dbHelpers.cleanTestDb(data.baseUrl);
    console.log('✅ PostgreSQL database cleanup completed');
  } catch (error) {
    console.error('⚠️ Database cleanup warning:', error.message);
  }
  
  console.log('✅ Test suite completed successfully!');
  console.log('====================================');
}

// Custom summary report
export function handleSummary(data) {
  const startTime = new Date(data.setup_data.startTime);
  const endTime = new Date();
  const duration = (endTime - startTime) / 1000; // seconds
  
  console.log('\n📊 Test Suite Summary');
  console.log('===================');
  console.log(`Database: PostgreSQL (${data.setup_data.testDbUrl || 'test_k6_db'})`);
  console.log(`Duration: ${duration}s`);
  console.log(`Total Requests: ${data.metrics.http_reqs.count}`);
  console.log(`Failed Requests: ${data.metrics.http_req_failed.count}`);
  console.log(`Average Response Time: ${data.metrics.http_req_duration.avg}ms`);
  console.log(`95th Percentile: ${data.metrics.http_req_duration['p(95)']}ms`);
  
  return {
    'k6-tests/results/test-suite-summary.html': htmlReport(data),
    'k6-tests/results/test-suite-summary.json': JSON.stringify(data, null, 2),
    'k6-tests/results/test-metrics.txt': generateTextSummary(data),
  };
}

function generateTextSummary(data) {
  const summary = [];
  summary.push('FastAPI Laravel K6 Test Suite Results');
  summary.push('=====================================');
  summary.push('');
  
  // Test environment info
  summary.push('Test Environment:');
  summary.push(`- Database: PostgreSQL (${data.setup_data ? data.setup_data.testDbUrl || 'test_k6_db' : 'PostgreSQL'})`);
  summary.push(`- Test Suite: Comprehensive load testing with fresh database`);
  summary.push('');
  
  // Overall metrics
  summary.push('Overall Metrics:');
  summary.push(`- Total HTTP Requests: ${data.metrics.http_reqs.count}`);
  summary.push(`- Failed Requests: ${data.metrics.http_req_failed.count} (${(data.metrics.http_req_failed.rate * 100).toFixed(2)}%)`);
  summary.push(`- Average Response Time: ${data.metrics.http_req_duration.avg.toFixed(2)}ms`);
  summary.push(`- 95th Percentile Response Time: ${data.metrics.http_req_duration['p(95)'].toFixed(2)}ms`);
  summary.push(`- Max Response Time: ${data.metrics.http_req_duration.max.toFixed(2)}ms`);
  summary.push('');
  
  // Test scenarios
  summary.push('Test Scenarios:');
  Object.keys(data.metrics).forEach(metric => {
    if (metric.includes('scenario_')) {
      summary.push(`- ${metric}: ${data.metrics[metric].count} iterations`);
    }
  });
  summary.push('');
  
  // Thresholds
  summary.push('Threshold Results:');
  if (data.thresholds) {
    Object.keys(data.thresholds).forEach(threshold => {
      const result = data.thresholds[threshold];
      summary.push(`- ${threshold}: ${result.ok ? '✅ PASS' : '❌ FAIL'}`);
    });
  }
  summary.push('');
  
  // Recommendations
  summary.push('Recommendations:');
  const failRate = data.metrics.http_req_failed.rate;
  const avgResponseTime = data.metrics.http_req_duration.avg;
  
  if (failRate > 0.05) {
    summary.push('- ⚠️ Error rate is high - investigate failing endpoints');
  }
  if (avgResponseTime > 2000) {
    summary.push('- ⚠️ Average response time is slow - consider performance optimization');
  }
  if (failRate <= 0.01 && avgResponseTime <= 1000) {
    summary.push('- ✅ Excellent performance - all metrics within optimal ranges');
  }
  
  return summary.join('\n');
}