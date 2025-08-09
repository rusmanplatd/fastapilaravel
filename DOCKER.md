# Docker Setup Guide

This FastAPI Laravel application is fully containerized and ready to run with Docker.

## Quick Start

### Development Mode (with auto-reload)
```bash
# Start all services (app, postgres, redis, nginx)
docker compose up

# Or run in background
docker compose up -d

# View logs
docker compose logs -f app
```

### Production Mode
```bash
# Start with production configuration
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Scale the application (production only)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale app=3
```

## Architecture

The Docker setup includes:

- **FastAPI Application** (`app` service)
  - Python 3.12-slim base image
  - PostgreSQL support with psycopg2-binary
  - Automatic database initialization and seeding
  - Health checks and graceful shutdown
  - Non-root user for security

- **PostgreSQL Database** (`postgres` service)
  - PostgreSQL 17 Alpine
  - Persistent data volume
  - Health checks
  - Development/production database separation

- **Redis Cache** (`redis` service)
  - Redis 8 Alpine
  - Persistent data volume
  - Used for caching and queues

- **Nginx Reverse Proxy** (`nginx` service)
  - Alpine-based
  - SSL termination ready
  - Load balancing support

## Configuration

### Environment Variables

Development (docker-compose.override.yml):
```bash
APP_ENV=development
DB_CONNECTION=postgresql
DB_HOST=postgres
DB_SEED_ON_STARTUP=true
```

Production (docker-compose.prod.yml):
```bash
APP_ENV=production
DB_SEED_ON_STARTUP=false
RATE_LIMIT_ENABLED=true
```

### Database Configuration

The application automatically:
1. Waits for PostgreSQL to be ready
2. Creates database tables
3. Seeds initial data (development only)

### Volumes

- `postgres_data`: PostgreSQL database files
- `redis_data`: Redis persistent storage
- `app_storage`: Application file storage
- `app_logs`: Application logs

## Commands

```bash
# Build images
docker compose build

# Start services
docker compose up

# Stop services
docker compose down

# View logs
docker compose logs [service_name]

# Execute commands in containers
docker compose exec app python3 -c "print('Hello from container!')"
docker compose exec postgres psql -U postgres -d fastapi_laravel

# Clean up everything
docker compose down -v --rmi all
```

## Database Management

```bash
# Access PostgreSQL shell
docker compose exec postgres psql -U postgres -d fastapi_laravel

# Run database migrations
docker compose exec app python3 -c "from config.database import create_tables; create_tables()"

# Run seeders manually
docker compose exec app python3 -c "
from config.database import SessionLocal
from database.seeders.DatabaseSeeder import DatabaseSeeder
session = SessionLocal()
seeder = DatabaseSeeder(session)
result = seeder.run()
print(f'Seeded {result[\"records_created\"]} records')
session.close()
"
```

## Health Checks

All services include health checks:

- **App**: HTTP check on `/monitoring/health`
- **PostgreSQL**: `pg_isready` command
- **Redis**: `redis-cli ping`

```bash
# Check service health
docker compose ps
docker compose exec app curl -f http://localhost:8000/monitoring/health
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   sudo chown -R $USER:$USER storage/
   ```

2. **Port Already in Use**
   ```bash
   # Change ports in docker-compose.yml
   ports:
     - "8001:8000"  # Use different host port
   ```

3. **Database Connection Failed**
   ```bash
   # Check PostgreSQL logs
   docker compose logs postgres
   
   # Verify database is ready
   docker compose exec postgres pg_isready -U postgres
   ```

4. **Build Failures**
   ```bash
   # Clean rebuild
   docker compose down
   docker compose build --no-cache
   docker compose up
   ```

### Debugging

```bash
# Enter container shell
docker compose exec app bash

# Check application logs
docker compose logs -f app

# Monitor resource usage
docker stats

# Inspect container
docker compose exec app env  # Check environment variables
docker compose exec app ps aux  # Check running processes
```

## Security Notes

- Application runs as non-root user (`appuser`)
- Production configuration disables debug mode
- Secrets should be managed via environment variables
- PostgreSQL password should be changed in production
- Use proper firewall rules in production

## Performance Optimization

### Production Tuning

```yaml
# docker-compose.prod.yml includes:
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

### Scaling

```bash
# Scale application instances
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale app=4

# Use external load balancer for production scaling
```

## Monitoring

The application includes:
- Health check endpoints
- Structured logging
- Metrics endpoints (when enabled)
- Database connection monitoring

```bash
# Monitor in real-time
docker compose logs -f app | grep "ERROR\|WARN"
```