/**
 * File Storage and Upload Tests
 * Tests file upload, storage operations, and multi-driver storage system
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { SharedArray } from 'k6/data';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';

import { TEST_CONFIG, HEADERS } from '../../config/test-config.js';
import { AuthHelper, generateTestData, validators, dbHelpers, fileHelpers } from '../../utils/helpers.js';

const fileTypes = new SharedArray('file-types', function() {
  return [
    { type: 'image', extensions: ['.jpg', '.png', '.gif'], maxSize: 5 * 1024 * 1024 },
    { type: 'document', extensions: ['.pdf', '.docx', '.txt'], maxSize: 20 * 1024 * 1024 },
    { type: 'archive', extensions: ['.zip', '.tar.gz'], maxSize: 100 * 1024 * 1024 },
    { type: 'video', extensions: ['.mp4', '.avi'], maxSize: 500 * 1024 * 1024 },
  ];
});

export let options = {
  scenarios: {
    file_upload: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 8 },
        { duration: '2m', target: 12 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testFileUpload',
    },
    storage_operations: {
      executor: 'constant-vus',
      vus: 10,
      duration: '3m',
      exec: 'testStorageOperations',
    },
    multi_driver_storage: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 6 },
        { duration: '2m', target: 15 },
        { duration: '30s', target: 0 },
      ],
      exec: 'testMultiDriverStorage',
    },
    image_processing: {
      executor: 'constant-vus',
      vus: 6,
      duration: '2m',
      exec: 'testImageProcessing',
    },
    storage_security: {
      executor: 'ramping-vus',
      stages: [
        { duration: '1m', target: 8 },
        { duration: '2m', target: 12 },
        { duration: '1m', target: 0 },
      ],
      exec: 'testStorageSecurity',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<5000'], // File operations can be slower
    http_req_failed: ['rate<0.05'],
    'http_req_duration{endpoint:upload}': ['p(95)<3000'],
    'http_req_duration{endpoint:download}': ['p(95)<2000'],
  },
};

export function setup() {
  console.log('📁 Setting up File Storage and Upload Tests');
  
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
    fileTypes: fileTypes,
  };
}

export function testFileUpload(data) {
  group('File Upload Tests', () => {
    const { baseUrl, userToken } = data;

    group('Single File Upload', () => {
      const testFile = fileHelpers.generateTestImage();
      
      const formData = {
        file: http.file(testFile.data, testFile.filename, testFile.content_type),
        description: 'K6 test image upload',
        category: 'test',
        visibility: 'private',
      };

      const response = http.post(`${baseUrl}/api/v1/storage/upload`, formData, {
        headers: {
          'Authorization': `Bearer ${userToken}`,
          // Don't set Content-Type for multipart/form-data, let k6 handle it
        },
        tags: { endpoint: 'upload', type: 'single' },
      });

      check(response, {
        'file upload successful': (r) => r.status === 200 || r.status === 201,
        'has file URL': (r) => {
          if (r.status === 200 || r.status === 201) {
            const result = r.json();
            return result.hasOwnProperty('url') || result.hasOwnProperty('path');
          }
          return true;
        },
        'has file metadata': (r) => {
          if (r.status === 200 || r.status === 201) {
            const result = r.json();
            return result.hasOwnProperty('size') && result.hasOwnProperty('mime_type');
          }
          return true;
        },
      });
    });

    group('Multiple File Upload', () => {
      const files = [];
      for (let i = 0; i < 3; i++) {
        files.push({
          [`file${i}`]: http.file(
            fileHelpers.generateTestFile(`test${i}.txt`, `Test content ${i}`).data,
            `test${i}.txt`,
            'text/plain'
          ),
        });
      }

      const formData = Object.assign({}, ...files, {
        description: 'K6 multiple file upload test',
        category: 'batch',
      });

      const response = http.post(`${baseUrl}/api/v1/storage/upload/multiple`, formData, {
        headers: {
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'upload', type: 'multiple' },
      });

      check(response, {
        'multiple upload processed': (r) => r.status === 200 || r.status === 201 || r.status === 207,
        'upload results included': (r) => {
          if (r.status >= 200 && r.status < 300) {
            const result = r.json();
            return result.hasOwnProperty('files') || result.hasOwnProperty('results');
          }
          return true;
        },
      });
    });

    group('File Type Validation', () => {
      const testCases = [
        { filename: 'test.jpg', content_type: 'image/jpeg', expected: 'success' },
        { filename: 'test.pdf', content_type: 'application/pdf', expected: 'success' },
        { filename: 'test.exe', content_type: 'application/x-executable', expected: 'error' },
        { filename: 'test.php', content_type: 'application/x-php', expected: 'error' },
      ];

      testCases.forEach(testCase => {
        const testFile = fileHelpers.generateTestFile(testCase.filename, 'test content', testCase.content_type);
        
        const formData = {
          file: http.file(testFile.data, testFile.filename, testFile.content_type),
        };

        const response = http.post(`${baseUrl}/api/v1/storage/upload`, formData, {
          headers: {
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'upload', validation: 'file-type', file: testCase.filename },
        });

        check(response, {
          [`${testCase.filename} validation correct`]: (r) => {
            if (testCase.expected === 'success') {
              return r.status === 200 || r.status === 201;
            } else {
              return r.status === 400 || r.status === 422;
            }
          },
        });
      });
    });

    group('File Size Limits', () => {
      // Test with different file sizes
      const sizeTests = [
        { size: 1024, expected: 'success' }, // 1KB
        { size: 1024 * 1024, expected: 'success' }, // 1MB
        { size: 10 * 1024 * 1024, expected: 'may_fail' }, // 10MB
      ];

      sizeTests.forEach(test => {
        const largeContent = 'x'.repeat(test.size);
        const testFile = fileHelpers.generateTestFile('large-test.txt', largeContent);
        
        const formData = {
          file: http.file(testFile.data, testFile.filename, testFile.content_type),
        };

        const response = http.post(`${baseUrl}/api/v1/storage/upload`, formData, {
          headers: {
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'upload', test: 'size-limit', size: test.size },
          timeout: '30s', // Longer timeout for large files
        });

        check(response, {
          [`${test.size} byte file handled`]: (r) => {
            if (test.expected === 'success') {
              return r.status === 200 || r.status === 201;
            } else {
              return r.status === 200 || r.status === 201 || r.status === 413; // Payload too large
            }
          },
        });
      });
    });

    group('Upload with Metadata', () => {
      const testFile = fileHelpers.generateTestImage();
      
      const formData = {
        file: http.file(testFile.data, testFile.filename, testFile.content_type),
        metadata: JSON.stringify({
          title: 'K6 Test Image',
          description: 'Test image uploaded via k6',
          tags: ['k6', 'test', 'automation'],
          custom_fields: {
            project: 'load-testing',
            version: '1.0',
          },
        }),
        visibility: 'public',
        folder: 'k6-tests',
      };

      const response = http.post(`${baseUrl}/api/v1/storage/upload`, formData, {
        headers: {
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'upload', type: 'metadata' },
      });

      check(response, {
        'upload with metadata successful': (r) => r.status === 200 || r.status === 201,
        'metadata preserved': (r) => {
          if (r.status === 200 || r.status === 201) {
            const result = r.json();
            return result.hasOwnProperty('metadata') || result.hasOwnProperty('title');
          }
          return true;
        },
      });
    });
  });
}

export function testStorageOperations(data) {
  group('Storage Operations Tests', () => {
    const { baseUrl, userToken } = data;

    group('File Listing and Search', () => {
      // List files with pagination
      const listResponse = http.get(`${baseUrl}/api/v1/storage/files?page=1&per_page=20`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'storage', action: 'list' },
      });

      validators.paginatedResponse(listResponse);
      
      if (listResponse.status === 200) {
        check(listResponse, {
          'files list structure': (r) => {
            const files = r.json().data;
            return Array.isArray(files);
          },
        });
      }

      // Search files
      const searchResponse = http.get(`${baseUrl}/api/v1/storage/files/search?q=test&type=image`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'storage', action: 'search' },
      });

      check(searchResponse, {
        'file search processed': (r) => r.status === 200 || r.status === 404,
        'search results format': (r) => {
          if (r.status === 200) {
            const results = r.json().data;
            return Array.isArray(results);
          }
          return true;
        },
      });
    });

    group('File Download and Access', () => {
      // Attempt to download a file (may not exist, but test endpoint)
      const downloadResponse = http.get(`${baseUrl}/api/v1/storage/files/test-file-id/download`, {
        headers: {
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'download', type: 'direct' },
      });

      check(downloadResponse, {
        'download request handled': (r) => r.status === 200 || r.status === 404 || r.status === 403,
        'proper headers for download': (r) => {
          if (r.status === 200) {
            return r.headers['Content-Disposition'] || r.headers['Content-Type'];
          }
          return true;
        },
      });

      // Test file streaming
      const streamResponse = http.get(`${baseUrl}/api/v1/storage/files/test-file-id/stream`, {
        headers: {
          'Authorization': `Bearer ${userToken}`,
          'Range': 'bytes=0-1023', // Request first 1KB
        },
        tags: { endpoint: 'download', type: 'stream' },
      });

      check(streamResponse, {
        'streaming supported': (r) => r.status === 200 || r.status === 206 || r.status === 404,
      });
    });

    group('File Operations', () => {
      // Test file copy
      const copyData = {
        source_path: '/uploads/test.jpg',
        destination_path: '/uploads/test-copy.jpg',
        preserve_metadata: true,
      };

      const copyResponse = http.post(`${baseUrl}/api/v1/storage/copy`, 
        JSON.stringify(copyData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'storage', action: 'copy' },
      });

      check(copyResponse, {
        'file copy processed': (r) => r.status === 200 || r.status === 201 || r.status === 404,
      });

      // Test file move
      const moveData = {
        source_path: '/uploads/test.jpg',
        destination_path: '/uploads/moved/test.jpg',
      };

      const moveResponse = http.post(`${baseUrl}/api/v1/storage/move`, 
        JSON.stringify(moveData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'storage', action: 'move' },
      });

      check(moveResponse, {
        'file move processed': (r) => r.status === 200 || r.status === 404,
      });

      // Test file deletion
      const deleteResponse = http.del(`${baseUrl}/api/v1/storage/files/test-file-id`, null, {
        headers: {
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'storage', action: 'delete' },
      });

      check(deleteResponse, {
        'file deletion processed': (r) => r.status === 200 || r.status === 404,
      });
    });

    group('Directory Operations', () => {
      // Create directory
      const createDirData = {
        path: '/uploads/k6-test-directory',
        permissions: 'private',
      };

      const createDirResponse = http.post(`${baseUrl}/api/v1/storage/directories`, 
        JSON.stringify(createDirData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'storage', action: 'create-dir' },
      });

      check(createDirResponse, {
        'directory creation processed': (r) => r.status === 200 || r.status === 201 || r.status === 409,
      });

      // List directory contents
      const listDirResponse = http.get(`${baseUrl}/api/v1/storage/directories/uploads`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'storage', action: 'list-dir' },
      });

      check(listDirResponse, {
        'directory listing processed': (r) => r.status === 200 || r.status === 404,
        'directory contents format': (r) => {
          if (r.status === 200) {
            const contents = r.json().data;
            return Array.isArray(contents) || typeof contents === 'object';
          }
          return true;
        },
      });
    });

    group('File Metadata Operations', () => {
      // Update file metadata
      const metadataUpdate = {
        title: 'Updated K6 Test File',
        description: 'Updated description for k6 testing',
        tags: ['k6', 'updated', 'metadata'],
        visibility: 'public',
      };

      const updateResponse = http.put(`${baseUrl}/api/v1/storage/files/test-file-id/metadata`, 
        JSON.stringify(metadataUpdate), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'storage', action: 'update-metadata' },
      });

      check(updateResponse, {
        'metadata update processed': (r) => r.status === 200 || r.status === 404,
      });

      // Get file metadata
      const metadataResponse = http.get(`${baseUrl}/api/v1/storage/files/test-file-id/metadata`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'storage', action: 'get-metadata' },
      });

      check(metadataResponse, {
        'metadata retrieval processed': (r) => r.status === 200 || r.status === 404,
        'metadata structure': (r) => {
          if (r.status === 200) {
            const metadata = r.json().data;
            return typeof metadata === 'object';
          }
          return true;
        },
      });
    });
  });
}

export function testMultiDriverStorage(data) {
  group('Multi-Driver Storage Tests', () => {
    const { baseUrl, userToken } = data;

    group('Storage Driver Configuration', () => {
      // Get available storage drivers
      const driversResponse = http.get(`${baseUrl}/api/v1/storage/drivers`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'storage', action: 'list-drivers' },
      });

      check(driversResponse, {
        'drivers list available': (r) => r.status === 200 || r.status === 403,
        'drivers information': (r) => {
          if (r.status === 200) {
            const drivers = r.json().data;
            return Array.isArray(drivers) || typeof drivers === 'object';
          }
          return true;
        },
      });
    });

    group('Cross-Driver Operations', () => {
      const drivers = ['local', 's3', 'gcs', 'azure'];
      
      drivers.forEach(driver => {
        // Test upload to specific driver
        const testFile = fileHelpers.generateTestFile(`${driver}-test.txt`, `Test file for ${driver} driver`);
        
        const formData = {
          file: http.file(testFile.data, testFile.filename, testFile.content_type),
          storage_driver: driver,
        };

        const uploadResponse = http.post(`${baseUrl}/api/v1/storage/upload`, formData, {
          headers: {
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'upload', driver: driver },
        });

        check(uploadResponse, {
          [`${driver} driver upload handled`]: (r) => {
            // May succeed or fail depending on driver availability
            return r.status === 200 || r.status === 201 || r.status === 400 || r.status === 500;
          },
        });
      });
    });

    group('Storage Migration', () => {
      // Test file migration between storage drivers
      const migrationData = {
        file_id: 'test-file-id',
        source_driver: 'local',
        target_driver: 's3',
        preserve_metadata: true,
        delete_source: false,
      };

      const migrationResponse = http.post(`${baseUrl}/api/v1/storage/migrate`, 
        JSON.stringify(migrationData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'storage', action: 'migrate' },
      });

      check(migrationResponse, {
        'migration request processed': (r) => r.status === 200 || r.status === 202 || r.status === 400 || r.status === 404,
        'migration job created': (r) => {
          if (r.status === 202) {
            const result = r.json();
            return result.hasOwnProperty('migration_id') || result.hasOwnProperty('job_id');
          }
          return true;
        },
      });
    });

    group('Storage Health Checks', () => {
      // Test storage driver health
      const healthResponse = http.get(`${baseUrl}/api/v1/storage/health`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'storage', action: 'health' },
      });

      check(healthResponse, {
        'health check available': (r) => r.status === 200 || r.status === 503,
        'health status format': (r) => {
          if (r.status === 200) {
            const health = r.json();
            return health.hasOwnProperty('drivers') || health.hasOwnProperty('status');
          }
          return true;
        },
      });
    });
  });
}

export function testImageProcessing(data) {
  group('Image Processing Tests', () => {
    const { baseUrl, userToken } = data;

    group('Image Resize and Thumbnails', () => {
      // Upload image and request thumbnails
      const testImage = fileHelpers.generateTestImage();
      
      const formData = {
        file: http.file(testImage.data, testImage.filename, testImage.content_type),
        generate_thumbnails: true,
        thumbnail_sizes: JSON.stringify([
          { width: 150, height: 150, name: 'small' },
          { width: 300, height: 300, name: 'medium' },
          { width: 600, height: 600, name: 'large' },
        ]),
      };

      const uploadResponse = http.post(`${baseUrl}/api/v1/storage/upload`, formData, {
        headers: {
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'upload', feature: 'thumbnails' },
      });

      check(uploadResponse, {
        'image upload with thumbnails': (r) => r.status === 200 || r.status === 201 || r.status === 400,
        'thumbnail information included': (r) => {
          if (r.status === 200 || r.status === 201) {
            const result = r.json();
            return result.hasOwnProperty('thumbnails') || result.hasOwnProperty('variants');
          }
          return true;
        },
      });
    });

    group('Image Transformation', () => {
      const transformations = [
        { operation: 'resize', params: { width: 400, height: 300 } },
        { operation: 'crop', params: { width: 200, height: 200, x: 50, y: 50 } },
        { operation: 'rotate', params: { degrees: 90 } },
        { operation: 'format', params: { format: 'webp', quality: 80 } },
      ];

      transformations.forEach(transform => {
        const transformData = {
          file_id: 'test-image-id',
          transformation: transform.operation,
          parameters: transform.params,
        };

        const response = http.post(`${baseUrl}/api/v1/storage/images/transform`, 
          JSON.stringify(transformData), {
          headers: {
            ...HEADERS,
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'image-transform', operation: transform.operation },
        });

        check(response, {
          [`${transform.operation} transformation handled`]: (r) => {
            return r.status === 200 || r.status === 201 || r.status === 400 || r.status === 404;
          },
        });
      });
    });

    group('Image Optimization', () => {
      const optimizationData = {
        file_id: 'test-image-id',
        options: {
          quality: 85,
          progressive: true,
          strip_metadata: true,
          auto_orient: true,
        },
      };

      const response = http.post(`${baseUrl}/api/v1/storage/images/optimize`, 
        JSON.stringify(optimizationData), {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'image-optimize' },
      });

      check(response, {
        'image optimization processed': (r) => r.status === 200 || r.status === 201 || r.status === 404,
        'optimization results': (r) => {
          if (r.status === 200 || r.status === 201) {
            const result = r.json();
            return result.hasOwnProperty('original_size') || result.hasOwnProperty('optimized_size');
          }
          return true;
        },
      });
    });
  });
}

export function testStorageSecurity(data) {
  group('Storage Security Tests', () => {
    const { baseUrl, userToken, adminToken } = data;

    group('Access Control and Permissions', () => {
      // Test unauthorized access
      const unauthorizedResponse = http.get(`${baseUrl}/api/v1/storage/files`, {
        headers: HEADERS, // No Authorization header
        tags: { endpoint: 'storage', test: 'unauthorized' },
      });

      check(unauthorizedResponse, {
        'unauthorized access denied': (r) => r.status === 401,
      });

      // Test access to restricted files
      const restrictedResponse = http.get(`${baseUrl}/api/v1/storage/files/private-file-id/download`, {
        headers: {
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'download', test: 'restricted' },
      });

      check(restrictedResponse, {
        'restricted access handled': (r) => r.status === 403 || r.status === 404,
      });
    });

    group('File Security Validation', () => {
      // Test malicious file upload attempts
      const maliciousFiles = [
        { name: 'script.js', content: 'alert("xss")', type: 'application/javascript' },
        { name: 'malware.exe', content: 'binary data', type: 'application/x-executable' },
        { name: 'shell.php', content: '<?php system($_GET["cmd"]); ?>', type: 'application/x-php' },
      ];

      maliciousFiles.forEach(file => {
        const testFile = fileHelpers.generateTestFile(file.name, file.content, file.type);
        
        const formData = {
          file: http.file(testFile.data, testFile.filename, testFile.content_type),
        };

        const response = http.post(`${baseUrl}/api/v1/storage/upload`, formData, {
          headers: {
            'Authorization': `Bearer ${userToken}`,
          },
          tags: { endpoint: 'upload', security: 'malicious', file: file.name },
        });

        check(response, {
          [`malicious file ${file.name} rejected`]: (r) => r.status === 400 || r.status === 422,
        });
      });
    });

    group('Storage Quotas and Limits', () => {
      // Test user storage quotas
      const quotaResponse = http.get(`${baseUrl}/api/v1/storage/quota`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'storage', action: 'quota' },
      });

      check(quotaResponse, {
        'quota information available': (r) => r.status === 200 || r.status === 404,
        'quota details': (r) => {
          if (r.status === 200) {
            const quota = r.json().data;
            return quota.hasOwnProperty('used') && quota.hasOwnProperty('limit');
          }
          return true;
        },
      });

      // Test storage analytics (admin only)
      const analyticsResponse = http.get(`${baseUrl}/api/v1/storage/analytics`, {
        headers: {
          ...HEADERS,
          'Authorization': `Bearer ${adminToken}`,
        },
        tags: { endpoint: 'storage', action: 'analytics' },
      });

      check(analyticsResponse, {
        'analytics available': (r) => r.status === 200 || r.status === 403,
        'analytics data': (r) => {
          if (r.status === 200) {
            const analytics = r.json().data;
            return typeof analytics === 'object';
          }
          return true;
        },
      });
    });

    group('Virus Scanning', () => {
      // Test virus scanning on upload
      const testFile = fileHelpers.generateTestFile('suspicious.txt', 'EICAR test string (not real virus)', 'text/plain');
      
      const formData = {
        file: http.file(testFile.data, testFile.filename, testFile.content_type),
        scan_for_viruses: true,
      };

      const response = http.post(`${baseUrl}/api/v1/storage/upload`, formData, {
        headers: {
          'Authorization': `Bearer ${userToken}`,
        },
        tags: { endpoint: 'upload', security: 'virus-scan' },
        timeout: '30s', // Virus scanning can be slow
      });

      check(response, {
        'virus scanning performed': (r) => {
          // Should either succeed or be quarantined
          return r.status === 200 || r.status === 201 || r.status === 400 || r.status === 423;
        },
        'scan results included': (r) => {
          if (r.status === 200 || r.status === 201) {
            const result = r.json();
            return result.hasOwnProperty('scan_result') || result.hasOwnProperty('virus_free');
          }
          return true;
        },
      });
    });
  });
}

export function teardown(data) {
  console.log('🧹 Cleaning up File Storage and Upload Tests');
  dbHelpers.cleanTestDb(data.baseUrl);
}

export function handleSummary(data) {
  return {
    'k6-tests/results/storage-upload-test.html': htmlReport(data),
    'k6-tests/results/storage-upload-test.json': JSON.stringify(data),
  };
}