# Square-Combo Integration

A cloud-hosted service that automatically syncs daily revenue data from Square POS systems to Combo at the end of each day.

## Overview

This integration service:
- Extracts daily revenue data via Square API
- Pushes revenue data to Combo API 
- Runs automatically once daily via cron jobs
- Supports multiple clients and locations
- Provides comprehensive logging and error handling

## Architecture

```
square-combo/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── database/
│   ├── models.py          # SQLAlchemy database models
│   └── database.py        # Database connection setup
├── adapters/
│   ├── square/
│   │   └── client.py      # Square API client
│   └── combo/
│       └── client.py      # Combo API client
├── routes/
│   ├── auth.py           # OAuth and authentication routes
│   └── admin.py          # Client management routes
├── tasks/
│   └── sync_revenue.py   # Daily sync task (cron job)
├── services/
│   ├── client_service.py # Client CRUD operations
│   └── sync_service.py   # Revenue sync business logic
└── utils/
    ├── config.py         # Application configuration
    └── logging.py        # Logging setup
```

## Setup Instructions

### 1. Environment Setup

```bash
# Clone the repository
cd square-combo

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp env.example .env

# Edit .env with your API credentials
# - Square API credentials (Application ID, Access Token)
# - Combo API credentials (API Key, Base URL)
# - Database URL (SQLite by default)
```

### 3. Database Setup

```bash
# Initialize database tables
python -c "from database.database import init_db; init_db()"
```

### 4. Running the Application

```bash
# Development server
python main.py

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Setting up Cron Job

The daily sync task runs automatically via cron. To set it up:

```bash
# Run the sync task manually for testing
python tasks/sync_revenue.py

# The cron job will be configured automatically when the app starts
# Default schedule: Daily at 00:00 (midnight)
```

## API Endpoints

### Health Check
- `GET /health` - Service health status
- `GET /` - Root endpoint with service info

### Authentication (Planned)
- `GET /auth/oauth/square` - Square OAuth callback
- `POST /auth/clients` - Create new client

### Admin (Planned)
- `GET /admin/clients` - List all clients
- `GET /admin/clients/{id}/sync-status` - Get sync status
- `POST /admin/clients/{id}/sync` - Trigger manual sync

## Database Schema

### Clients Table
- Stores client information and API credentials
- Fields: id, name, square_access_token, square_application_id, combo_api_key, is_active

### Locations Table
- Stores Square location mappings to Combo locations
- Fields: id, client_id, square_location_id, combo_location_id, name, address, is_active

### Sync Logs Table
- Tracks all sync operations and results
- Fields: id, client_id, location_id, sync_date, revenue_amount, status, error_message

## Configuration Options

Environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `SQUARE_APPLICATION_ID` | Square application ID | - |
| `SQUARE_ACCESS_TOKEN` | Square access token | - |
| `SQUARE_ENVIRONMENT` | Square environment (sandbox/production) | sandbox |
| `COMBO_API_KEY` | Combo API key | - |
| `COMBO_BASE_URL` | Combo API base URL | https://api.combo.com |
| `DATABASE_URL` | Database connection string | sqlite:///./square_combo.db |
| `LOG_LEVEL` | Logging level | INFO |
| `SYNC_TIME` | Daily sync time (HH:MM) | 00:00 |
| `SYNC_DAYS_BACK` | Days back to fetch revenue | 1 |
| `HOST` | Server host | 0.0.0.0 |
| `PORT` | Server port | 8000 |

## Deployment

### Azure VM Deployment

1. **VM Setup**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Python 3.9+
   sudo apt install python3 python3-pip python3-venv -y
   
   # Clone repository
   git clone <repository-url>
   cd square-combo
   ```

2. **Application Setup**
   ```bash
   # Create virtual environment
   python3 -m venv .venv
   source .venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Configure environment
   cp env.example .env
   # Edit .env with production values
   
   # Initialize database
   python -c "from database.database import init_db; init_db()"
   ```

3. **Service Setup (Systemd)**
   ```bash
   # Create service file
   sudo nano /etc/systemd/system/square-combo.service
   
   # Enable and start service
   sudo systemctl enable square-combo
   sudo systemctl start square-combo
   ```

4. **Reverse Proxy (Nginx)**
   ```bash
   # Install and configure Nginx
   sudo apt install nginx -y
   # Configure proxy to FastAPI app
   ```

## Logging

Logs are written to:
- `logs/square_combo.log` - General application logs
- `logs/sync.log` - Sync operation logs
- Console output for development

Log rotation is configured with 10MB max file size and 5-10 backup files.

## Development Status

### ✅ Completed
- Project structure setup
- Database models design
- FastAPI application skeleton
- Configuration management
- Logging setup
- Basic health check endpoint

### 🚧 In Progress
- API adapter implementations
- Service layer business logic
- Authentication routes
- Admin management routes

### 📋 TODO
- Square API integration
- Combo API integration  
- OAuth flow implementation
- Cron job setup
- Error handling and retry logic
- Client onboarding flow
- Comprehensive testing
- Production deployment scripts

## Testing

```bash
# Run the application
python main.py

# Test health endpoint
curl http://localhost:8000/health

# Test root endpoint
curl http://localhost:8000/
```

## Support

For issues and questions, please refer to the project documentation or contact the development team.

## License

Private.
