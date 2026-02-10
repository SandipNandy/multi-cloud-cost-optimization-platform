#!/bin/bash
# Cloud Cost Anomaly Detection MVP - One-Click Deployment
set -e

echo "🚀 Multi-Cloud Cost Anomaly Detection MVP"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

check_command() {
    if ! command -v $1 >/dev/null 2>&1; then
        print_error "$1 is required but not installed."
        return 1
    fi
    print_success "$1 found"
}

check_command docker
check_command docker-compose

# Check for .env file
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from template..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_status "Created .env file. Please edit it with your credentials."
        print_status "At minimum, you need AWS credentials for the MVP."
        echo ""
        print_status "Required in .env:"
        echo "  AWS_ACCESS_KEY=your_access_key"
        echo "  AWS_SECRET_KEY=your_secret_key"
        echo ""
        read -p "Open .env file for editing now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if command -v nano >/dev/null 2>&1; then
                nano .env
            elif command -v vim >/dev/null 2>&1; then
                vim .env
            else
                vi .env
            fi
        fi
    else
        print_error ".env.example not found. Cannot create .env file."
        exit 1
    fi
fi

# Build and start containers
print_status "Building Docker images..."
docker-compose build

print_status "Starting containers..."
docker-compose up -d

# Wait for services to be ready
print_status "Waiting for services to start (30 seconds)..."
sleep 30

# Check if services are running
print_status "Checking service status..."
if docker-compose ps | grep -q "Up"; then
    print_success "All services are running!"
else
    print_error "Some services failed to start. Check logs with: docker-compose logs"
    exit 1
fi

# Initialize database
print_status "Initializing database..."
sleep 5

# Test database connection
if docker-compose exec postgres pg_isready -U postgres; then
    print_success "Database is ready"
else
    print_error "Database is not responding"
    docker-compose logs postgres
    exit 1
fi

# Run initial detection
print_status "Running initial AWS detection (this may take a minute)..."
curl -X POST "http://localhost:8000/api/v1/detect?cloud=aws" > /dev/null 2>&1 || true

# Wait for detection to complete
print_status "Waiting for detection to complete..."
sleep 20

# Display deployment info
echo ""
echo "🎉 ${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "${YELLOW}📊 Dashboard:${NC} http://localhost:8501"
echo "${YELLOW}🔧 API:${NC} http://localhost:8000"
echo "${YELLOW}📚 API Documentation:${NC} http://localhost:8000/docs"
echo "${YELLOW}🐘 Database:${NC} localhost:5432 (user: postgres, db: cloud_cost)"
echo ""
echo "${BLUE}🚀 Quick Start Commands:${NC}"
echo "  View logs:              docker-compose logs -f"
echo "  Stop services:          docker-compose down"
echo "  Restart services:       docker-compose restart"
echo "  Trigger detection:      curl -X POST http://localhost:8000/api/v1/detect"
echo "  View anomalies:         curl http://localhost:8000/api/v1/anomalies"
echo ""
echo "${GREEN}✅ Your real-time cost anomaly detection is now running!${NC}"
echo "   The system will automatically scan for wasteful resources every 5 minutes."
echo ""
echo "⚠️  ${YELLOW}Note: Make sure your AWS credentials in .env have these permissions:${NC}"
echo "   - ce:GetCostAndUsage"
echo "   - ec2:DescribeInstances"
echo "   - ec2:DescribeVolumes"
echo "   - rds:DescribeDBInstances"
echo "   - cloudwatch:GetMetricStatistics"
