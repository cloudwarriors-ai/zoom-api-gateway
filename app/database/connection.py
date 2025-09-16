from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

from app.core.config import settings
from app.core.exceptions import DatabaseException

# Configure logging
logger = logging.getLogger(__name__)

# Create database engine
try:
    engine = create_engine(
        str(settings.DATABASE_URL),
        pool_pre_ping=True,  # Test connections before using them
        pool_size=5,         # Maximum number of connections to keep open
        max_overflow=10,     # Maximum number of connections to create above pool_size
        pool_recycle=3600,   # Recycle connections after 1 hour
    )
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {str(e)}")
    raise DatabaseException(detail=f"Database connection error: {str(e)}")

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency function to get a database session.
    
    Yields:
        Session: A SQLAlchemy database session
    
    Example:
        @app.get("/users/")
        async def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def check_database_connection():
    """
    Check if the database connection is working.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        # Create a connection to test
        with engine.connect() as connection:
            # Execute a simple query
            connection.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return False