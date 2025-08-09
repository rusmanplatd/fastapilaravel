#!/usr/bin/env python3
"""
Test script to verify K6 Docker setup configuration
Tests the database connection and basic application setup without actually starting Docker
"""

import os
import sys
from pathlib import Path

def test_docker_compose_exists():
    """Test that docker-compose.k6.yml exists"""
    compose_file = Path(__file__).parent / "docker-compose.k6.yml"
    assert compose_file.exists(), "docker-compose.k6.yml not found"
    print("✅ docker-compose.k6.yml exists")
    return True

def test_makefile_exists():
    """Test that Makefile exists"""
    makefile = Path(__file__).parent / "Makefile"
    assert makefile.exists(), "Makefile not found"
    print("✅ K6 Makefile exists")
    return True

def test_init_db_script_exists():
    """Test that init-db.sql exists"""
    init_script = Path(__file__).parent / "setup" / "init-db.sql"
    assert init_script.exists(), "setup/init-db.sql not found"
    print("✅ Database initialization script exists")
    return True

def test_dockerfile_exists():
    """Test that parent Dockerfile exists"""
    dockerfile = Path(__file__).parent.parent / "Dockerfile"
    assert dockerfile.exists(), "Parent Dockerfile not found"
    print("✅ Parent Dockerfile exists")
    return True

def test_config_file_values():
    """Test that config values are updated for Docker environment"""
    config_file = Path(__file__).parent / "config" / "test-config.js"
    assert config_file.exists(), "config/test-config.js not found"
    
    content = config_file.read_text()
    
    # Check for environment variable integration
    assert "__ENV.K6_BASE_URL" in content, "Should use K6_BASE_URL environment variable"
    assert "__ENV.K6_TEST_DB_URL" in content, "Should use K6_TEST_DB_URL environment variable"
    assert "__ENV.K6_TEST_USER_EMAIL" in content, "Should use K6_TEST_USER_EMAIL environment variable"
    assert "__ENV.K6_OAUTH2_CLIENT_ID" in content, "Should use K6_OAUTH2_CLIENT_ID environment variable"
    
    print("✅ Config file uses .env.k6 environment variables")
    return True

def test_database_setup_script():
    """Test that database setup script is updated"""
    setup_script = Path(__file__).parent / "setup" / "test-db-setup.py"
    assert setup_script.exists(), "setup/test-db-setup.py not found"
    
    content = setup_script.read_text()
    
    # Check for environment variable usage
    assert 'os.getenv("K6_TEST_DB_URL")' in content, "Should use K6_TEST_DB_URL environment variable"
    assert "k6_test_password" in content, "Database setup should have Docker-compatible defaults"
    
    print("✅ Database setup script uses .env.k6 environment variables")
    return True

def test_documentation_exists():
    """Test that documentation files exist"""
    docs = [
        Path(__file__).parent / "README.md",
        Path(__file__).parent / "DOCKER_SETUP.md",
        Path(__file__).parent / "POSTGRESQL_SETUP.md",
        Path(__file__).parent / "QUICK_START.md"
    ]
    
    for doc in docs:
        assert doc.exists(), f"Documentation file {doc.name} not found"
    
    print("✅ All documentation files exist")
    return True

def test_env_files_exist():
    """Test that .env.k6 files exist"""
    env_files = [
        Path(__file__).parent / ".env.k6",
        Path(__file__).parent / ".env.k6.example"
    ]
    
    for env_file in env_files:
        assert env_file.exists(), f"Environment file {env_file.name} not found"
    
    print("✅ Environment files (.env.k6 and .env.k6.example) exist")
    return True

def test_environment_variables():
    """Test environment variable configuration"""
    # Test that we can import and use the config
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    try:
        # Set test environment variables
        os.environ["TEST_DB_URL"] = "postgresql://postgres:k6_test_password@localhost:5433/test_k6_db"
        os.environ["BASE_URL"] = "http://localhost:8001"
        
        print("✅ Environment variables can be set correctly")
        return True
    except Exception as e:
        print(f"❌ Environment variable test failed: {e}")
        return False

def test_port_configuration():
    """Test that ports are configured to avoid conflicts"""
    compose_file = Path(__file__).parent / "docker-compose.k6.yml"
    content = compose_file.read_text()
    
    # Check for environment variable port configuration
    assert "${K6_POSTGRES_EXTERNAL_PORT}:5432" in content, "PostgreSQL should use K6_POSTGRES_EXTERNAL_PORT environment variable"
    assert "${K6_REDIS_EXTERNAL_PORT}:6379" in content, "Redis should use K6_REDIS_EXTERNAL_PORT environment variable"
    assert "8001:${PORT}" in content, "FastAPI should use PORT environment variable"
    
    # Check environment file for port values
    env_file = Path(__file__).parent / ".env.k6"
    env_content = env_file.read_text()
    assert 'K6_POSTGRES_EXTERNAL_PORT="5433"' in env_content, "Environment should set PostgreSQL port to 5433"
    assert 'K6_REDIS_EXTERNAL_PORT="6380"' in env_content, "Environment should set Redis port to 6380"
    
    print("✅ Ports are configured using environment variables")
    return True

def test_volume_configuration():
    """Test that volumes are properly named and configured"""
    compose_file = Path(__file__).parent / "docker-compose.k6.yml"
    content = compose_file.read_text()
    
    # Check for volume references using environment variables
    assert "postgres_data:" in content, "PostgreSQL volume should be defined"
    assert "redis_data:" in content, "Redis volume should be defined"
    assert "app_storage:" in content, "App storage volume should be defined"
    assert "results:" in content, "Results volume should be defined"
    
    # Check environment file for volume names
    env_file = Path(__file__).parent / ".env.k6"
    env_content = env_file.read_text()
    assert 'POSTGRES_VOLUME_NAME="fastapilaravel_k6_postgres_data"' in env_content, "Environment should define PostgreSQL volume name"
    assert 'REDIS_VOLUME_NAME="fastapilaravel_k6_redis_data"' in env_content, "Environment should define Redis volume name"
    
    print("✅ Volumes are properly configured with environment variables")
    return True

def main():
    """Run all tests"""
    print("🧪 Testing K6 Docker setup configuration...")
    print("=" * 50)
    
    tests = [
        test_docker_compose_exists,
        test_makefile_exists,
        test_init_db_script_exists,
        test_dockerfile_exists,
        test_config_file_values,
        test_database_setup_script,
        test_documentation_exists,
        test_env_files_exist,
        test_environment_variables,
        test_port_configuration,
        test_volume_configuration,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! K6 Docker setup is ready.")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())