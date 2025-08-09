/**
 * Queue System Tests
 * Tests Laravel-style queue system with job processing, batching, chaining
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { SharedArray } from 'k6/data';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';

import { TEST_CONFIG, HEADERS } from '../../config/test-config.js';
import { AuthHelper, generateTestData, validators, dbHelpers } from '../../utils/helpers.js';

const jobTypes = new SharedArray('job-types', function() {
  return [
    { type: 'SendEmailJob', data: { to: 'test@example.com', subject: 'Test Email' }, queue: 'emails' },
    { type: 'ProcessImageJob', data: { image_path: '/uploads/test.jpg' }, queue: 'media' },
    { type: 'SendNotificationJob', data: { user_id: 1, message: 'Test notification' }, queue: 'notifications' },
    { type: 'GenerateReportJob', data: { report_type: 'monthly', user_id: 1 }, queue: 'reports' },
    { type: 'BackupDatabaseJob', data: { tables: ['users', 'posts'] }, queue: 'maintenance' },
  ];
});

export let options = {
  scenarios: {
    job_dispatch: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 10 },
        { duration: '2m', target: 15 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testJobDispatch',
    },
    job_processing: {
      executor: 'constant-vus',
      vus: 8,
      duration: '3m',
      exec: 'testJobProcessing',
    },
    batch_jobs: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 6 },
        { duration: '2m', target: 12 },
        { duration: '30s', target: 0 },
      ],
      exec: 'testBatchJobs',
    },
    job_chains: {
      executor: 'constant-vus',
      vus: 5,
      duration: '2m',
      exec: 'testJobChains',
    },
    queue_management: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 8 },
        { duration: '2m', target: 12 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testQueueManagement',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<3000'], // Queue operations can be slower
    http_req_failed: ['rate<0.05'],
    'http_req_duration{endpoint:job-dispatch}': ['p(95)<2000'],
    'http_req_duration{endpoint:queue-status}': ['p(95)<1000'],
  },
};

export function setup() {
  console.log('⚡ Setting up Queue System Tests');
  
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
    jobTypes: jobTypes,
  };
}

export function testJobDispatch(data) {
  group('Job Dispatch Tests', () => {
    const { baseUrl, userToken, jobTypes } = data;

    group('Dispatch Single Job', () => {
      const job = jobTypes[0]; // SendEmailJob
      
      const jobData = {
        job: job.type,
        payload: job.data,
        queue: job.queue,
        options: {
          delay: 0,
          max_tries: 3,
          timeout: 60,
          priority: 'normal',
        },
      };

      const response = http.post(`${baseUrl}/api/v1/jobs/dispatch`, 
        JSON.stringify(jobData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'job-dispatch', type: 'single', job: job.type },
      });

      check(response, {
        'job dispatch successful': (r) => r.status === 200 || r.status === 201 || r.status === 202,
        'has job ID': (r) => {
          if (r.status >= 200 && r.status < 300) {
            const result = r.json();
            return result.hasOwnProperty('job_id') || result.hasOwnProperty('id');
          }
          return true;
        },
        'dispatch response format': (r) => {
          if (r.status >= 200 && r.status < 300) {
            const result = r.json();
            return result.hasOwnProperty('status') || result.hasOwnProperty('message');
          }
          return true;
        },
      });
    });

    group('Dispatch Jobs to Different Queues', () => {
      jobTypes.forEach((job, index) => {
        const jobData = {
          job: job.type,
          payload: { ...job.data, test_id: index },
          queue: job.queue,
          options: {
            delay: index * 5, // Staggered delays
            priority: index % 2 === 0 ? 'high' : 'normal',
          },
        };

        const response = http.post(`${baseUrl}/api/v1/jobs/dispatch`, 
          JSON.stringify(jobData), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'job-dispatch', queue: job.queue, job: job.type },
        });

        check(response, {
          [`${job.type} dispatched to ${job.queue}`]: (r) => r.status >= 200 && r.status < 300,
        });
      });
    });

    group('Dispatch with Scheduling', () => {
      const scheduledJob = {
        job: 'SendEmailJob',
        payload: {
          to: 'scheduled@example.com',
          subject: 'Scheduled Email',
          body: 'This email was scheduled via k6 test',
        },
        queue: 'emails',
        schedule: {
          delay_seconds: 30,
          // scheduled_at: new Date(Date.now() + 60000).toISOString(), // 1 minute from now
        },
      };

      const response = http.post(`${baseUrl}/api/v1/jobs/schedule`, 
        JSON.stringify(scheduledJob), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'job-dispatch', type: 'scheduled' },
      });

      check(response, {
        'scheduled job created': (r) => r.status === 200 || r.status === 201 || r.status === 202,
        'schedule information': (r) => {
          if (r.status >= 200 && r.status < 300) {
            const result = r.json();
            return result.hasOwnProperty('scheduled_for') || result.hasOwnProperty('delay');
          }
          return true;
        },
      });
    });

    group('Job Dispatch Validation', () => {
      // Test invalid job dispatch
      const invalidJobs = [
        { job: 'NonExistentJob', payload: {}, expected: 'error' },
        { job: '', payload: {}, expected: 'error' },
        { job: 'SendEmailJob', payload: 'invalid-payload', expected: 'error' },
      ];

      invalidJobs.forEach((testJob, index) => {
        const response = http.post(`${baseUrl}/api/v1/jobs/dispatch`, 
          JSON.stringify(testJob), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'job-dispatch', test: 'validation', case: index },
        });

        check(response, {
          [`invalid job ${index} rejected`]: (r) => r.status === 400 || r.status === 422,
        });
      });
    });
  });
}

export function testJobProcessing(data) {
  group('Job Processing Tests', () => {
    const { baseUrl, adminToken } = data;

    group('Queue Worker Status', () => {
      const response = http.get(`${baseUrl}/api/v1/queue/workers/status`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'queue-status', type: 'workers' },
      });

      validators.apiResponse(response, 200);
      
      if (response.status === 200) {
        check(response, {
          'worker status information': (r) => {
            const status = r.json().data;
            return typeof status === 'object' && 
                   (status.hasOwnProperty('workers') || status.hasOwnProperty('active'));
          },
        });
      }
    });

    group('Queue Statistics', () => {
      const statsResponse = http.get(`${baseUrl}/api/v1/queue/stats`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'queue-status', type: 'stats' },
      });

      check(statsResponse, {
        'queue stats available': (r) => r.status === 200 || r.status === 403,
        'stats data structure': (r) => {
          if (r.status === 200) {
            const stats = r.json().data;
            return typeof stats === 'object';
          }
          return true;
        },
      });
    });

    group('Failed Jobs Management', () => {
      // List failed jobs
      const failedJobsResponse = http.get(`${baseUrl}/api/v1/queue/failed`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'queue-management', type: 'failed' },
      });

      check(failedJobsResponse, {
        'failed jobs list available': (r) => r.status === 200 || r.status === 403,
        'failed jobs format': (r) => {
          if (r.status === 200) {
            const failed = r.json().data;
            return Array.isArray(failed);
          }
          return true;
        },
      });

      // Retry failed jobs
      const retryData = {
        job_ids: ['failed-job-1', 'failed-job-2'],
        retry_all: false,
      };

      const retryResponse = http.post(`${baseUrl}/api/v1/queue/failed/retry`, 
        JSON.stringify(retryData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'queue-management', action: 'retry' },
      });

      check(retryResponse, {
        'retry request processed': (r) => r.status === 200 || r.status === 404,
      });

      // Flush failed jobs
      const flushResponse = http.delete(`${baseUrl}/api/v1/queue/failed/flush`, null, {
        headers: {
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'queue-management', action: 'flush' },
      });

      check(flushResponse, {
        'flush request processed': (r) => r.status === 200 || r.status === 404,
      });
    });

    group('Job Monitoring', () => {
      // Monitor specific job
      const jobId = 'test-job-id-' + Date.now();
      const monitorResponse = http.get(`${baseUrl}/api/v1/jobs/${jobId}/status`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'job-monitor', action: 'status' },
      });

      check(monitorResponse, {
        'job monitoring handled': (r) => r.status === 200 || r.status === 404,
        'job status format': (r) => {
          if (r.status === 200) {
            const status = r.json().data;
            return status.hasOwnProperty('status') || status.hasOwnProperty('state');
          }
          return true;
        },
      });

      // Get job logs
      const logsResponse = http.get(`${baseUrl}/api/v1/jobs/${jobId}/logs`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'job-monitor', action: 'logs' },
      });

      check(logsResponse, {
        'job logs available': (r) => r.status === 200 || r.status === 404,
      });
    });

    group('Real-time Queue Monitoring', () => {
      // Test queue dashboard/metrics endpoint
      const dashboardResponse = http.get(`${baseUrl}/api/v1/queue/dashboard`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'queue-dashboard' },
      });

      check(dashboardResponse, {
        'queue dashboard available': (r) => r.status === 200 || r.status === 403,
        'dashboard data complete': (r) => {
          if (r.status === 200) {
            const dashboard = r.json().data;
            return typeof dashboard === 'object';
          }
          return true;
        },
      });
    });
  });
}

export function testBatchJobs(data) {
  group('Batch Jobs Tests', () => {
    const { baseUrl, adminToken } = data;

    group('Create Job Batch', () => {
      const batchJobs = [];
      
      // Create multiple jobs for batch processing
      for (let i = 0; i < 5; i++) {
        batchJobs.push({
          job: 'ProcessDataJob',
          payload: {
            data_id: `data-${i}`,
            chunk: i,
            total_chunks: 5,
          },
          queue: 'processing',
        });
      }

      const batchData = {
        name: 'K6 Test Data Processing Batch',
        jobs: batchJobs,
        options: {
          allow_failures: 1, // Allow 1 job to fail
          progress_callback: '/api/v1/batch-progress',
          completion_callback: '/api/v1/batch-complete',
        },
      };

      const response = http.post(`${baseUrl}/api/v1/jobs/batch`, 
        JSON.stringify(batchData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'job-batch', action: 'create' },
      });

      check(response, {
        'batch creation successful': (r) => r.status === 200 || r.status === 201 || r.status === 202,
        'batch ID provided': (r) => {
          if (r.status >= 200 && r.status < 300) {
            const result = r.json();
            return result.hasOwnProperty('batch_id') || result.hasOwnProperty('id');
          }
          return true;
        },
        'batch metadata': (r) => {
          if (r.status >= 200 && r.status < 300) {
            const result = r.json();
            return result.hasOwnProperty('total_jobs') || result.hasOwnProperty('jobs_count');
          }
          return true;
        },
      });
    });

    group('Monitor Batch Progress', () => {
      const batchId = 'test-batch-' + Date.now();
      
      const statusResponse = http.get(`${baseUrl}/api/v1/jobs/batch/${batchId}`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'job-batch', action: 'status' },
      });

      check(statusResponse, {
        'batch status available': (r) => r.status === 200 || r.status === 404,
        'batch progress information': (r) => {
          if (r.status === 200) {
            const batch = r.json().data;
            return batch.hasOwnProperty('progress') || 
                   (batch.hasOwnProperty('completed_jobs') && batch.hasOwnProperty('total_jobs'));
          }
          return true;
        },
      });

      // Test batch cancellation
      const cancelResponse = http.post(`${baseUrl}/api/v1/jobs/batch/${batchId}/cancel`, {}, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'job-batch', action: 'cancel' },
      });

      check(cancelResponse, {
        'batch cancellation handled': (r) => r.status === 200 || r.status === 404,
      });
    });

    group('Batch Job Analytics', () => {
      const analyticsResponse = http.get(`${baseUrl}/api/v1/jobs/batch/analytics?days=7`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'job-batch', action: 'analytics' },
      });

      check(analyticsResponse, {
        'batch analytics available': (r) => r.status === 200 || r.status === 403,
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

export function testJobChains(data) {
  group('Job Chains Tests', () => {
    const { baseUrl, adminToken } = data;

    group('Create Job Chain', () => {
      const chainJobs = [
        {
          job: 'ExtractDataJob',
          payload: { source: 'database', table: 'users' },
          queue: 'etl',
        },
        {
          job: 'TransformDataJob',
          payload: { transformation: 'normalize', format: 'json' },
          queue: 'etl',
        },
        {
          job: 'LoadDataJob',
          payload: { destination: 'warehouse', table: 'processed_users' },
          queue: 'etl',
        },
        {
          job: 'NotifyCompletionJob',
          payload: { recipients: ['admin@example.com'], type: 'etl_complete' },
          queue: 'notifications',
        },
      ];

      const chainData = {
        name: 'K6 ETL Processing Chain',
        jobs: chainJobs,
        options: {
          stop_on_failure: true,
          chain_callback: '/api/v1/chain-complete',
        },
      };

      const response = http.post(`${baseUrl}/api/v1/jobs/chain`, 
        JSON.stringify(chainData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'job-chain', action: 'create' },
      });

      check(response, {
        'chain creation successful': (r) => r.status === 200 || r.status === 201 || r.status === 202,
        'chain ID provided': (r) => {
          if (r.status >= 200 && r.status < 300) {
            const result = r.json();
            return result.hasOwnProperty('chain_id') || result.hasOwnProperty('id');
          }
          return true;
        },
        'chain steps information': (r) => {
          if (r.status >= 200 && r.status < 300) {
            const result = r.json();
            return result.hasOwnProperty('total_steps') || result.hasOwnProperty('jobs_count');
          }
          return true;
        },
      });
    });

    group('Monitor Chain Progress', () => {
      const chainId = 'test-chain-' + Date.now();
      
      const progressResponse = http.get(`${baseUrl}/api/v1/jobs/chain/${chainId}`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'job-chain', action: 'progress' },
      });

      check(progressResponse, {
        'chain progress available': (r) => r.status === 200 || r.status === 404,
        'chain status details': (r) => {
          if (r.status === 200) {
            const chain = r.json().data;
            return chain.hasOwnProperty('current_step') || chain.hasOwnProperty('completed_steps');
          }
          return true;
        },
      });

      // Test chain pause/resume
      const pauseResponse = http.post(`${baseUrl}/api/v1/jobs/chain/${chainId}/pause`, {}, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'job-chain', action: 'pause' },
      });

      check(pauseResponse, {
        'chain pause handled': (r) => r.status === 200 || r.status === 404,
      });

      const resumeResponse = http.post(`${baseUrl}/api/v1/jobs/chain/${chainId}/resume`, {}, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'job-chain', action: 'resume' },
      });

      check(resumeResponse, {
        'chain resume handled': (r) => r.status === 200 || r.status === 404,
      });
    });

    group('Chain Dependencies and Conditions', () => {
      const conditionalChain = {
        name: 'Conditional Processing Chain',
        jobs: [
          {
            job: 'ValidateInputJob',
            payload: { data: 'test-data' },
            queue: 'validation',
          },
          {
            job: 'ProcessDataJob',
            payload: { data: 'test-data' },
            queue: 'processing',
            conditions: {
              depends_on: 'ValidateInputJob',
              continue_if: 'success',
            },
          },
          {
            job: 'CleanupJob',
            payload: { cleanup_type: 'temp_files' },
            queue: 'maintenance',
            conditions: {
              depends_on: 'ProcessDataJob',
              continue_if: 'any', // Run regardless of previous job result
            },
          },
        ],
        options: {
          allow_parallel: false,
          timeout_minutes: 30,
        },
      };

      const response = http.post(`${baseUrl}/api/v1/jobs/chain`, 
        JSON.stringify(conditionalChain), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'job-chain', type: 'conditional' },
      });

      check(response, {
        'conditional chain created': (r) => r.status === 200 || r.status === 201 || r.status === 202,
      });
    });
  });
}

export function testQueueManagement(data) {
  group('Queue Management Tests', () => {
    const { baseUrl, adminToken } = data;

    group('Queue Configuration', () => {
      // Get queue configuration
      const configResponse = http.get(`${baseUrl}/api/v1/queue/config`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'queue-management', action: 'config' },
      });

      check(configResponse, {
        'queue config available': (r) => r.status === 200 || r.status === 403,
        'config structure': (r) => {
          if (r.status === 200) {
            const config = r.json().data;
            return typeof config === 'object';
          }
          return true;
        },
      });

      // Update queue settings
      const updateSettings = {
        default_timeout: 300,
        max_retries: 3,
        retry_delay: 60,
        batch_size: 10,
        worker_memory_limit: '512M',
      };

      const updateResponse = http.put(`${baseUrl}/api/v1/queue/config`, 
        JSON.stringify(updateSettings), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'queue-management', action: 'update-config' },
      });

      check(updateResponse, {
        'config update handled': (r) => r.status === 200 || r.status === 403,
      });
    });

    group('Queue Operations', () => {
      const queues = ['emails', 'notifications', 'processing', 'maintenance'];
      
      queues.forEach(queueName => {
        // Get queue size
        const sizeResponse = http.get(`${baseUrl}/api/v1/queue/${queueName}/size`, {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'queue-management', queue: queueName, action: 'size' },
        });

        check(sizeResponse, {
          [`${queueName} queue size available`]: (r) => r.status === 200 || r.status === 404,
        });

        // Purge queue
        const purgeResponse = http.delete(`${baseUrl}/api/v1/queue/${queueName}/purge`, null, {
          headers: {
            'Authorization': `Bearer ${adminToken}`,
          },
          tags: { endpoint: 'queue-management', queue: queueName, action: 'purge' },
        });

        check(purgeResponse, {
          [`${queueName} purge handled`]: (r) => r.status === 200 || r.status === 404,
        });
      });
    });

    group('Worker Management', () => {
      // List active workers
      const workersResponse = http.get(`${baseUrl}/api/v1/queue/workers`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'queue-management', action: 'workers' },
      });

      check(workersResponse, {
        'workers list available': (r) => r.status === 200 || r.status === 403,
        'workers information': (r) => {
          if (r.status === 200) {
            const workers = r.json().data;
            return Array.isArray(workers) || typeof workers === 'object';
          }
          return true;
        },
      });

      // Restart workers
      const restartResponse = http.post(`${baseUrl}/api/v1/queue/workers/restart`, {
        worker_ids: ['worker-1', 'worker-2'],
        restart_all: false,
      }, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'queue-management', action: 'restart-workers' },
      });

      check(restartResponse, {
        'worker restart handled': (r) => r.status === 200 || r.status === 404,
      });
    });

    group('Queue Health and Monitoring', () => {
      // Health check
      const healthResponse = http.get(`${baseUrl}/api/v1/queue/health`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'queue-health' },
      });

      check(healthResponse, {
        'queue health available': (r) => r.status === 200 || r.status === 503,
        'health status format': (r) => {
          if (r.status === 200) {
            const health = r.json();
            return health.hasOwnProperty('status') || health.hasOwnProperty('healthy');
          }
          return true;
        },
      });

      // Performance metrics
      const metricsResponse = http.get(`${baseUrl}/api/v1/queue/metrics`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'queue-metrics' },
      });

      check(metricsResponse, {
        'metrics available': (r) => r.status === 200 || r.status === 403,
        'metrics data structure': (r) => {
          if (r.status === 200) {
            const metrics = r.json().data;
            return typeof metrics === 'object';
          }
          return true;
        },
      });

      // Queue alerts and notifications
      const alertsResponse = http.get(`${baseUrl}/api/v1/queue/alerts`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'queue-alerts' },
      });

      check(alertsResponse, {
        'alerts system available': (r) => r.status === 200 || r.status === 404,
      });
    });
  });
}

export function teardown(data) {
  console.log('🧹 Cleaning up Queue System Tests');
  dbHelpers.cleanTestDb(data.baseUrl);
}

export function handleSummary(data) {
  return {
    'k6-tests/results/queue-system-test.html': htmlReport(data),
    'k6-tests/results/queue-system-test.json': JSON.stringify(data),
  };
}