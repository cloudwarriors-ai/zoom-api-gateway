from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

from app.core.config import settings
from app.database.connection import engine, SessionLocal
from app.core.exceptions import CustomException
from app.services import zoom_discovery

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Middleware for request timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        logger.error(f"Request error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

# Exception handler for custom exceptions
@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify the service is running."""
    return {"status": "healthy", "service": "zoom-platform-microservice"}

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize connections and resources on startup."""
    logger.info("Initializing service...")
    # Create database tables if they don't exist
    import app.database.models  # Import models to register them with SQLAlchemy
    app.database.models.Base.metadata.create_all(bind=engine)

    # Run database migrations
    try:
        from app.database.migrations.create_ssot_field_mappings import run_migration
        run_migration()
    except Exception as e:
        logger.error(f"Error running migrations: {str(e)}")

    # Initialize Zoom endpoint discovery
    logger.info("Initializing Zoom endpoint discovery...")
    zoom_discovery.initialize_discovery()

    logger.info("Service initialized successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down service...")
    # Clean up any resources here
    logger.info("Service shutdown complete")

# Import and include routers
from app.routers.auth import router as auth_router
from app.routers.mcp import router as mcp_router
from app.routers.transform import router as transform_router
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(mcp_router, prefix="/api/mcp", tags=["MCP"])
app.include_router(transform_router, prefix="/api/transform", tags=["Transform"])

# Also mount the MCP router at /mcp for backward compatibility
app.include_router(mcp_router, prefix="/mcp", tags=["MCP-Legacy"])

# Discovery endpoint
@app.get("/api/discovery/zoom-endpoints", tags=["Discovery"])
async def get_zoom_endpoints(category: str = None, limit: int = None):
    """
    Get discovered Zoom API endpoints from OpenAPI specification.

    Args:
        category: Optional category filter
        limit: Optional limit on number of results

    Returns:
        Dict containing endpoint metadata and list of endpoints
    """
    return zoom_discovery.get_endpoints_by_category(category=category, limit=limit)

# Custom OpenAPI schema with discovered endpoints injected
def custom_openapi():
    """
    Generate custom OpenAPI schema including discovered Zoom endpoints.
    """
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=settings.API_TITLE,
        version=settings.API_VERSION,
        description=settings.API_DESCRIPTION,
        routes=app.routes,
    )

    # Inject discovered Zoom endpoints into the OpenAPI schema
    try:
        discovered_data = zoom_discovery.fetch_zoom_endpoints()
        endpoints = discovered_data.get("endpoints", [])

        if endpoints:
            # Add each discovered endpoint to the paths
            if "paths" not in openapi_schema:
                openapi_schema["paths"] = {}

            for endpoint in endpoints:
                path = endpoint.get("path")
                method = endpoint.get("method", "GET").lower()

                if path not in openapi_schema["paths"]:
                    openapi_schema["paths"][path] = {}

                openapi_schema["paths"][path][method] = {
                    "summary": endpoint.get("summary", ""),
                    "description": endpoint.get("description", ""),
                    "operationId": endpoint.get("operationId", ""),
                    "tags": endpoint.get("tags", ["Zoom API"]),
                    "parameters": endpoint.get("parameters", []),
                    "responses": {
                        "200": {
                            "description": "Successful response"
                        }
                    }
                }

            logger.info(f"✅ Injected {len(endpoints)} Zoom endpoints into OpenAPI schema")
    except Exception as e:
        logger.error(f"Failed to inject discovered endpoints into OpenAPI schema: {e}")

    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Override the default OpenAPI schema
app.openapi = custom_openapi

# If this file is run directly, start the application with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)