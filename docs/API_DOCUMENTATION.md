# Zoom Platform Microservice API Documentation

This document provides detailed information about the API endpoints available in the Zoom Platform Microservice.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication for development purposes. In production, authentication will be implemented.

## API Endpoints

### Health Check

#### GET /health

Check if the service is running.

**Response**:
```json
{
  "status": "healthy",
  "service": "zoom-platform-microservice"
}
```

### Transformation Endpoints

#### POST /api/transform/ssot-to-zoom

Transform SSOT data to Zoom format.

**Request Body**:
```json
{
  "entity_type": "user",
  "data": {
    "id": "123",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "role": "user",
    "status": "active",
    "timezone": "America/New_York"
  },
  "options": {
    "job_type_code": "users",
    "default_type": 1,
    "default_status": "active"
  }
}
```

**Response**:
```json
{
  "transformed_data": {
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "type": 1,
    "status": "active",
    "timezone": "America/New_York"
  },
  "source_platform": "ssot",
  "target_platform": "zoom",
  "entity_type": "user",
  "metadata": {
    "transformation_type": "ssot_to_zoom",
    "job_type_code": "users"
  }
}
```

#### POST /api/transform/raw-to-zoom

Transform raw platform data to Zoom format.

**Request Body**:
```json
{
  "entity_type": "user",
  "raw_platform": "ringcentral",
  "data": {
    "id": "123",
    "email": "test@example.com",
    "firstName": "Test",
    "lastName": "User",
    "status": "Active",
    "regionalSettings": {
      "timezone": {
        "id": "58",
        "name": "Eastern Time"
      }
    }
  },
  "options": {
    "job_type_code": "users",
    "site_id": "site-123"
  }
}
```

**Response**:
```json
{
  "transformed_data": {
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "type": 1,
    "status": "active",
    "timezone": "America/New_York",
    "site_id": "site-123"
  },
  "source_platform": "ringcentral",
  "target_platform": "zoom",
  "entity_type": "user",
  "metadata": {
    "transformation_type": "raw_to_zoom",
    "raw_platform": "ringcentral",
    "job_type_code": "users"
  }
}
```

#### POST /api/transform/zoom-to-ssot

Transform Zoom data to SSOT format.

**Request Body**:
```json
{
  "entity_type": "user",
  "data": {
    "id": "123",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "type": 1,
    "status": "active",
    "timezone": "America/New_York"
  },
  "options": {
    "job_type_code": "users"
  }
}
```

**Response**:
```json
{
  "transformed_data": {
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "role": "user",
    "status": "active",
    "timezone": "America/New_York",
    "source_platform": "zoom",
    "source_id": "123"
  },
  "source_platform": "zoom",
  "target_platform": "ssot",
  "entity_type": "user",
  "metadata": {
    "transformation_type": "zoom_to_ssot",
    "job_type_code": "users"
  }
}
```

#### POST /api/transform/{source_platform}/to/{target_platform}

Generic transformation endpoint that supports any source to target platform transformation.

**URL Parameters**:
- `source_platform`: Source platform (e.g., "ssot", "ringcentral", "zoom")
- `target_platform`: Target platform (e.g., "zoom", "ssot")

**Query Parameters**:
- `entity_type`: Type of entity to transform (e.g., "user", "call_queue", "site")

**Request Body**:
```json
{
  "data": {
    // Data to transform
  },
  "options": {
    "job_type_code": "users",
    // Other options
  }
}
```

**Response**:
```json
{
  "transformed_data": {
    // Transformed data
  },
  "source_platform": "source_platform",
  "target_platform": "target_platform",
  "entity_type": "entity_type",
  "metadata": {
    "transformation_type": "source_to_target",
    "job_type_code": "job_type_code"
  }
}
```

### MCP Protocol Endpoints

#### POST /api/mcp

Handle an MCP protocol request.

**Request Body**:
```json
{
  "tool": "transform",
  "parameters": {
    "method": "ssot_to_zoom",
    "entity_type": "user",
    "data": {
      "id": "123",
      "email": "test@example.com",
      "first_name": "Test",
      "last_name": "User",
      "role": "user",
      "status": "active"
    },
    "options": {
      "job_type_code": "users"
    }
  }
}
```

**Response**:
```json
{
  "status": "success",
  "result": {
    "transformed_data": {
      "email": "test@example.com",
      "first_name": "Test",
      "last_name": "User",
      "type": 1,
      "status": "active"
    },
    "metadata": {
      "transformation_type": "ssot_to_zoom",
      "job_type_code": "users"
    }
  }
}
```

#### POST /api/mcp/transform

Convenience endpoint for transformation using the MCP protocol.

**Request Body**:
```json
{
  "tool": "transform",
  "parameters": {
    "method": "raw_to_zoom",
    "entity_type": "user",
    "raw_platform": "ringcentral",
    "data": {
      "id": "123",
      "email": "test@example.com",
      "firstName": "Test",
      "lastName": "User"
    },
    "options": {
      "job_type_code": "users"
    }
  }
}
```

**Response**:
```json
{
  "status": "success",
  "result": {
    "transformed_data": {
      "email": "test@example.com",
      "first_name": "Test",
      "last_name": "User",
      "type": 1,
      "status": "inactive"
    },
    "metadata": {
      "transformation_type": "raw_to_zoom",
      "raw_platform": "ringcentral",
      "job_type_code": "users"
    }
  }
}
```

#### POST /api/mcp/list-tools

List available MCP tools.

**Request Body**:
```json
{
  "tool": "list_tools"
}
```

**Response**:
```json
{
  "status": "success",
  "result": [
    {
      "name": "transform",
      "description": "Transform data between different formats",
      "parameters": {
        "method": {
          "type": "string",
          "description": "Transformation method",
          "enum": ["ssot_to_zoom", "raw_to_zoom", "zoom_to_ssot"]
        },
        "data": {
          "type": "object",
          "description": "The data to transform"
        },
        "entity_type": {
          "type": "string",
          "description": "The type of entity to transform",
          "enum": ["user", "meeting", "recording", "contact", "account", "group"]
        },
        "options": {
          "type": "object",
          "description": "Optional parameters for the transformation"
        },
        "raw_platform": {
          "type": "string",
          "description": "The platform the raw data originated from (required for raw_to_zoom)",
          "enum": ["zoom", "dialpad", "ringcentral"]
        }
      }
    },
    {
      "name": "list_tools",
      "description": "List available MCP tools",
      "parameters": {}
    }
  ]
}
```

#### GET /api/mcp/tools

Get available MCP tools without requiring an MCP request.

**Response**:
```json
{
  "status": "success",
  "result": [
    {
      "name": "transform",
      "description": "Transform data between different formats",
      "parameters": {
        // Parameters as above
      }
    },
    {
      "name": "list_tools",
      "description": "List available MCP tools",
      "parameters": {}
    }
  ]
}
```

## Error Responses

### Validation Error (422)

```json
{
  "detail": "Invalid entity_type: invalid. Must be one of: user, meeting, recording, contact, account, group"
}
```

### Not Found Error (404)

```json
{
  "detail": "Resource not found"
}
```

### Internal Server Error (500)

```json
{
  "detail": "Internal server error"
}
```

### MCP Error Response

```json
{
  "status": "error",
  "error": "Error message"
}
```

## Supported Entity Types

- `user`: User accounts
- `meeting`: Meeting configurations
- `recording`: Recording settings
- `contact`: Contact information
- `account`: Account settings
- `group`: Group configurations
- `site`: Site locations
- `call_queue`: Call queue configurations
- `ivr`: IVR (Interactive Voice Response) systems
- `auto_receptionist`: Auto receptionist configurations

## Supported Platforms

- `ssot`: Single Source of Truth format
- `zoom`: Zoom platform format
- `raw`: Raw platform data (requires specifying the raw platform)
- `ringcentral`: RingCentral platform format
- `dialpad`: Dialpad platform format