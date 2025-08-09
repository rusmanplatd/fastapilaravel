#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting FastAPI Laravel Application...${NC}"

# Function to wait for database
wait_for_db() {
    echo -e "${YELLOW}⏳ Waiting for database to be ready...${NC}"
    
    if [[ "${DATABASE_URL}" == *"postgresql"* ]] || [[ "${DB_CONNECTION}" == "postgresql" ]]; then
        # Extract PostgreSQL connection details
        DB_HOST=${DB_HOST:-localhost}
        DB_PORT=${DB_PORT:-5432}
        DB_USER=${DB_USERNAME:-postgres}
        
        echo -e "${BLUE}📡 Checking PostgreSQL connection to ${DB_HOST}:${DB_PORT}...${NC}"
        
        until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" 2>/dev/null; do
            echo -e "${YELLOW}⏳ PostgreSQL is unavailable - sleeping for 2 seconds...${NC}"
            sleep 2
        done
        
        echo -e "${GREEN}✅ PostgreSQL is ready!${NC}"
    else
        echo -e "${GREEN}✅ Using SQLite database - no wait required${NC}"
    fi
}

# Function to run database migrations/setup
setup_database() {
    echo -e "${BLUE}🗄️  Setting up database...${NC}"
    
    # Create tables if they don't exist
    python3 -c "
from config.database import create_tables
try:
    create_tables()
    print('✅ Database tables created successfully')
except Exception as e:
    print(f'⚠️  Database setup: {e}')
"
}

# Function to run database seeders
run_seeders() {
    if [[ "${DB_SEED_ON_STARTUP}" == "true" ]]; then
        echo -e "${BLUE}🌱 Running database seeders...${NC}"
        
        python3 -c "
import os
from config.database import SessionLocal
from database.seeders.DatabaseSeeder import DatabaseSeeder

try:
    session = SessionLocal()
    seeder = DatabaseSeeder(session)
    
    # Only seed if database is empty or in development
    if os.getenv('APP_ENV') in ['development', 'testing']:
        result = seeder.run()
        if result['success']:
            print(f'✅ Database seeded successfully: {result[\"records_created\"]} records')
        else:
            print(f'⚠️  Database seeding failed: {result[\"error\"]}')
    else:
        print('ℹ️  Skipping seeders in production environment')
    
    session.close()
except Exception as e:
    print(f'⚠️  Seeder error: {e}')
"
    else
        echo -e "${YELLOW}⏭️  Skipping database seeders (DB_SEED_ON_STARTUP not set to true)${NC}"
    fi
}

# Function to validate environment
validate_environment() {
    echo -e "${BLUE}🔍 Validating environment...${NC}"
    
    # Check required environment variables
    REQUIRED_VARS=("APP_SECRET_KEY")
    
    for var in "${REQUIRED_VARS[@]}"; do
        if [[ -z "${!var}" ]]; then
            echo -e "${RED}❌ Missing required environment variable: $var${NC}"
            exit 1
        fi
    done
    
    # Check if running as non-root user
    if [[ $(id -u) -eq 0 ]]; then
        echo -e "${YELLOW}⚠️  Running as root user - this is not recommended for production${NC}"
    fi
    
    echo -e "${GREEN}✅ Environment validation passed${NC}"
}

# Function to show application info
show_app_info() {
    echo -e "${BLUE}📋 Application Information:${NC}"
    echo -e "   🏷️  App Environment: ${APP_ENV:-production}"
    echo -e "   🌐 Host: ${HOST:-0.0.0.0}"
    echo -e "   🔌 Port: ${PORT:-8000}"
    echo -e "   🗄️  Database: ${DB_CONNECTION:-sqlite}"
    echo -e "   🐍 Python: $(python3 --version)"
    echo -e "   👤 User: $(whoami)"
    echo ""
}

# Main execution
main() {
    show_app_info
    validate_environment
    wait_for_db
    setup_database
    run_seeders
    
    echo -e "${GREEN}🎉 Initialization complete! Starting application...${NC}"
    echo ""
    
    # Execute the command passed to the script
    exec "$@"
}

# Handle SIGTERM gracefully
_term() {
    echo -e "${YELLOW}📴 Received SIGTERM, shutting down gracefully...${NC}"
    kill -TERM "$child" 2>/dev/null
}

trap _term SIGTERM

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@" &
    child=$!
    wait "$child"
fi