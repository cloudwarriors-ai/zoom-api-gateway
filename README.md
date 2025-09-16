# Zoom Platform Microservice

## Overview

This microservice is part of the CloudWarriors ETL system, focused specifically on integrating with the Zoom API. It provides a standardized interface for extracting, transforming, and loading data from Zoom into other target platforms.

## Purpose

The Zoom Platform Microservice serves as a dedicated connector between the CloudWarriors ETL system and Zoom's API services. Its primary responsibilities include:

- **Authentication**: Managing OAuth2 access tokens for Zoom API
- **Data Extraction**: Retrieving meetings, recordings, users, and other data from Zoom
- **Transformation**: Converting Zoom's data format to the system's standardized schema
- **MCP Protocol Support**: Implementing Machine Communication Protocol for AI-assisted operations

## Architecture

This service follows a modular, file-based architecture:

- `app/core`: Core configuration and shared utilities
- `app/database`: Database models and connection management
- `app/routers`: API route definitions and endpoint handlers
- `app/schemas`: Pydantic models for request/response validation

## Getting Started

### Prerequisites

- Python 3.9+
- FastAPI
- SQLAlchemy
- PostgreSQL

### Installation

```bash
# Clone the repository
git clone https://github.com/cloudwarriors/zoom-platform-microservice.git
cd zoom-platform-microservice

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn app.main:app --reload
```

### Configuration

Set the following environment variables or update the `.env` file:

- `ZOOM_CLIENT_ID`: Your Zoom OAuth client ID
- `ZOOM_CLIENT_SECRET`: Your Zoom OAuth client secret
- `ZOOM_REDIRECT_URI`: OAuth redirect URI
- `DATABASE_URL`: PostgreSQL connection string

## API Documentation

When the service is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Local Development Setup with Tesseract ETL

This microservice is designed to work with the Tesseract ETL system (`etl_prism_poc`). Follow these steps to set up the full development environment:

### Prerequisites

- Docker and docker-compose
- Tesseract ETL system running locally
- PostgreSQL (included in docker-compose)

### Quick Setup

1. **Start the microservice:**
   ```bash
   cd zoom-platform-microservice
   docker-compose up -d
   ```

2. **Verify the microservice is running:**
   ```bash
   curl http://localhost:3555/health
   ```

3. **Configure Tesseract to use the microservice:**
   
   In the Tesseract admin panel:
   - Navigate to PhonePlatform settings
   - Set `integration_mode = 'microservice'`
   - Set `mcp_server_url = 'http://host.docker.internal:3555'`
   - Set `use_ssot_transformation = False` for raw transformations

### Network Configuration

The microservice runs on port `3555` and connects to Tesseract via Docker networking:

- **Microservice URL**: `http://localhost:3555`
- **From Tesseract**: `http://host.docker.internal:3555`
- **Database**: PostgreSQL on port `5433` (separate from Tesseract)

### Testing the Integration

Run the consistency test to verify all transformers are working:

```bash
# From the Tesseract backend container
cd /Users/trentcharlton/Documents/CloudWarriors/etl_prism_poc
docker-compose exec backend python3 test_exact_consistency.py
```

This will test all 5 job types:
- Sites (JobType 33)
- Users (JobType 39)  
- Call Queues (JobType 45)
- Auto Receptionists (JobType 77)
- IVR (JobType 78)

### Available Transformations

The microservice currently supports RingCentral-to-Zoom transformations via MCP endpoints:

- `rc_zoom_sites`: Site/location transformation with emergency address mapping
- `rc_zoom_users`: User transformation with contact info mapping
- `rc_zoom_call_queues`: Business hours to custom hours settings
- `rc_zoom_ars`: Auto receptionist with site ID mapping
- `rc_zoom_ivr`: IVR action mapping and key transformation

### Development Workflow

1. **Make changes** to transformer files in `app/transformers/`
2. **Test changes** using the consistency test framework
3. **Verify integration** with Tesseract ETL job execution
4. **Check logs** in both systems for debugging

### Troubleshooting

**Microservice not reachable from Tesseract:**
- Ensure Docker networks are properly configured
- Use `host.docker.internal:3555` not `localhost:3555` from containers

**Database connection issues:**
- Check PostgreSQL is running on port 5433
- Verify DATABASE_URL environment variable

**Transformation errors:**
- Check microservice logs: `docker-compose logs microservice`
- Verify input data format matches expected schema
- Use the test framework to isolate issues

## License

Copyright © 2023 CloudWarriors. All rights reserved.