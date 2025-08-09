# PostgreSQL Setup Guide for K6 Testing

This guide provides detailed instructions for setting up PostgreSQL for the k6 test suite.

## 🐘 PostgreSQL Installation

### Ubuntu/Debian
```bash
# Update package list
sudo apt-get update

# Install PostgreSQL and additional contributed packages
sudo apt-get install postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify installation
sudo systemctl status postgresql
```

### macOS
```bash
# Install via Homebrew
brew install postgresql

# Start PostgreSQL service
brew services start postgresql

# Verify installation
brew services list | grep postgresql
```

### CentOS/RHEL/Fedora
```bash
# Install PostgreSQL
sudo dnf install postgresql postgresql-server postgresql-contrib

# Initialize database
sudo postgresql-setup --initdb

# Start and enable service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Docker (Alternative)
```bash
# Run PostgreSQL in Docker container
docker run --name k6-postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_DB=postgres \
  -p 5432:5432 \
  -d postgres:15

# Verify container is running
docker ps | grep k6-postgres
```

## ⚙️ PostgreSQL Configuration

### 1. Create Database User
```bash
# Switch to postgres user and create user
sudo -u postgres psql

-- In PostgreSQL shell
CREATE USER k6_user WITH PASSWORD 'k6_password';
ALTER USER k6_user CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE postgres TO k6_user;

-- Exit PostgreSQL shell
\q
```

### 2. Configure Authentication (Optional)
Edit PostgreSQL configuration to allow connections:

```bash
# Find PostgreSQL config directory
sudo -u postgres psql -c "SHOW config_file;"

# Edit pg_hba.conf to allow local connections
sudo nano /etc/postgresql/*/main/pg_hba.conf

# Add or modify this line for local development:
# local   all             all                                     md5
# host    all             all             127.0.0.1/32            md5
```

### 3. Restart PostgreSQL
```bash
sudo systemctl restart postgresql
```

## 🧪 Test Database Configuration

### Environment Variables
Create a `.env` file in your project root or set environment variables:

```bash
# PostgreSQL connection settings for k6 tests
export TEST_DB_URL="postgresql://postgres:password@localhost:5432/test_k6_db"
export POSTGRES_USER="postgres"
export POSTGRES_PASSWORD="password"
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
export POSTGRES_DB="test_k6_db"
```

### Custom Configuration
You can customize the database connection by modifying `k6-tests/config/test-config.js`:

```javascript
export const TEST_DB_URL = __ENV.TEST_DB_URL || 'postgresql://your_user:your_password@your_host:5432/your_test_db';
```

## 🔧 Python Dependencies

### Install Required Packages
```bash
# Install PostgreSQL adapter for Python
pip install psycopg2-binary

# Alternative: Install from source (if binary fails)
pip install psycopg2

# Install SQLAlchemy with PostgreSQL support
pip install sqlalchemy[postgresql]

# Verify installation
python -c "import psycopg2; print('✅ psycopg2 installed successfully')"
```

### Requirements File
Add to your `requirements.txt`:
```txt
psycopg2-binary>=2.9.5
sqlalchemy[postgresql]>=2.0.0
```

## ✅ Verification

### 1. Test PostgreSQL Connection
```bash
# Test basic connection
psql -h localhost -U postgres -c "SELECT version();"

# Test with custom user
psql -h localhost -U k6_user -d postgres -c "SELECT current_user, current_database();"
```

### 2. Test Python Connection
```python
# test_connection.py
import psycopg2
from sqlalchemy import create_engine, text

# Test psycopg2 connection
try:
    conn = psycopg2.connect(
        host="localhost",
        database="postgres", 
        user="postgres",
        password="password"
    )
    print("✅ psycopg2 connection successful")
    conn.close()
except Exception as e:
    print(f"❌ psycopg2 connection failed: {e}")

# Test SQLAlchemy connection
try:
    engine = create_engine("postgresql://postgres:password@localhost:5432/postgres")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        print(f"✅ SQLAlchemy connection successful: {result.fetchone()[0][:50]}...")
except Exception as e:
    print(f"❌ SQLAlchemy connection failed: {e}")
```

### 3. Test Database Setup Script
```bash
# Run the k6 database setup script
cd k6-tests
python setup/test-db-setup.py

# Should output:
# 🧪 K6 Test Database Setup
# ================================================
# ✅ PostgreSQL database 'test_k6_db' created successfully
# Creating database tables...
# ✅ Database tables created successfully
# ...
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Connection Refused
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check if PostgreSQL is listening on port 5432
sudo netstat -plntu | grep 5432

# Restart PostgreSQL
sudo systemctl restart postgresql
```

#### 2. Authentication Failed
```bash
# Reset postgres user password
sudo -u postgres psql
\password postgres

# Check pg_hba.conf authentication method
sudo cat /etc/postgresql/*/main/pg_hba.conf | grep -v "^#"
```

#### 3. Database Creation Permission
```bash
# Grant CREATEDB permission to user
sudo -u postgres psql
ALTER USER your_user CREATEDB;
```

#### 4. Python Connection Issues
```bash
# Install development headers (Ubuntu/Debian)
sudo apt-get install libpq-dev python3-dev

# Reinstall psycopg2
pip uninstall psycopg2 psycopg2-binary
pip install psycopg2-binary
```

#### 5. Performance Issues
```bash
# Increase connection limits in postgresql.conf
sudo nano /etc/postgresql/*/main/postgresql.conf

# Modify these settings:
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Error Messages and Solutions

| Error | Solution |
|-------|----------|
| `FATAL: database "test_k6_db" does not exist` | Database creation is handled automatically by the setup script |
| `FATAL: password authentication failed` | Check password in connection string and pg_hba.conf |
| `could not connect to server: Connection refused` | PostgreSQL service is not running |
| `permission denied to create database` | Grant CREATEDB permission to the user |
| `ImportError: No module named 'psycopg2'` | Install psycopg2-binary package |

## 📊 Performance Tuning for Testing

### Optimized PostgreSQL Settings for K6 Testing
```sql
-- Temporary settings for testing (reset after tests)
SET synchronous_commit = OFF;
SET fsync = OFF;
SET full_page_writes = OFF;
SET checkpoint_segments = 32;
SET checkpoint_completion_target = 0.9;
SET wal_buffers = 16MB;
SET shared_buffers = '256MB';
```

### Connection Pooling
For high-load testing, consider using connection pooling:

```python
# In your test setup
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    "postgresql://postgres:password@localhost:5432/test_k6_db",
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_recycle=3600,
    pool_pre_ping=True
)
```

## 🔒 Security Considerations

### For Testing Environment
- Use dedicated test database and user
- Restrict network access to testing environment only
- Use strong passwords even for test environments
- Clean up test data after testing

### Connection Security
```bash
# Use SSL connection (production)
TEST_DB_URL="postgresql://user:pass@localhost:5432/testdb?sslmode=require"

# For testing, you can disable SSL
TEST_DB_URL="postgresql://user:pass@localhost:5432/testdb?sslmode=disable"
```

This setup ensures your k6 test suite runs efficiently with PostgreSQL while maintaining proper isolation and performance.