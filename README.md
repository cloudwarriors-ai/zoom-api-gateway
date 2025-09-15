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

## License

Copyright © 2023 CloudWarriors. All rights reserved.