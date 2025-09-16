#!/usr/bin/env python3
"""
Script to import SSOT schemas from etl_prism_poc database to zoom-platform-microservice database.

This script:
1. Connects to the etl_prism_poc database using Django's ORM
2. Connects to the zoom-platform-microservice database using SQLAlchemy
3. Queries all SSOT schemas from the etl_prism_poc database
4. Inserts them into the zoom-platform-microservice database
5. Handles errors that might occur during the import process
"""

import os
import sys
import logging
import django
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Setup Django environment
sys.path.append('/Users/trentcharlton/Documents/CloudWarriors/etl_prism_poc/app/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etl_system.settings_development')
django.setup()

# Import Django models after setup
from api.models import SSOTSchema

# SQLAlchemy setup for the zoom-platform-microservice database
Base = declarative_base()

class ZoomSSOTSchema(Base):
    """SQLAlchemy model for SSOT schema in zoom-platform-microservice database."""
    __tablename__ = 'ssot_schemas'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(255), nullable=False, unique=True)
    description = sa.Column(sa.Text, nullable=True)
    schema_definition = sa.Column(sa.JSON, nullable=False)
    platform = sa.Column(sa.String(50), nullable=False)
    record_type = sa.Column(sa.String(50), nullable=False)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    updated_at = sa.Column(sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ZoomSSOTSchema(name='{self.name}', platform='{self.platform}', record_type='{self.record_type}')>"


def get_source_db_ssot_schemas():
    """
    Retrieve all SSOT schemas from the etl_prism_poc database.
    
    Returns:
        list: A list of SSOTSchema objects from Django's ORM
    """
    try:
        logger.info("Retrieving SSOT schemas from etl_prism_poc database...")
        schemas = SSOTSchema.objects.all()
        logger.info(f"Retrieved {len(schemas)} SSOT schemas from source database")
        return schemas
    except Exception as e:
        logger.error(f"Error retrieving SSOT schemas from source database: {str(e)}")
        raise


def connect_to_target_db():
    """
    Connect to the zoom-platform-microservice database using SQLAlchemy.
    
    Returns:
        tuple: (engine, session) - SQLAlchemy engine and session objects
    """
    try:
        logger.info("Connecting to zoom-platform-microservice database...")
        # Update these connection details as per your configuration
        db_url = "postgresql://postgres:postgres@localhost:5432/zoom_platform"
        engine = sa.create_engine(db_url)
        
        # Create tables if they don't exist
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        logger.info("Connected to target database successfully")
        return engine, session
    except Exception as e:
        logger.error(f"Error connecting to target database: {str(e)}")
        raise


def import_schemas(source_schemas, target_session):
    """
    Import schemas from source to target database.
    
    Args:
        source_schemas (list): List of Django SSOTSchema objects
        target_session (Session): SQLAlchemy session for target database
    
    Returns:
        dict: Statistics about the import process
    """
    stats = {
        'total': len(source_schemas),
        'inserted': 0,
        'updated': 0,
        'failed': 0,
        'skipped': 0
    }
    
    logger.info(f"Starting import of {stats['total']} schemas...")
    
    for schema in source_schemas:
        try:
            # Check if schema already exists
            existing_schema = target_session.query(ZoomSSOTSchema).filter_by(name=schema.name).first()
            
            if existing_schema:
                # Update existing schema
                existing_schema.description = schema.description
                existing_schema.schema_definition = schema.schema_definition
                existing_schema.platform = schema.platform
                existing_schema.record_type = schema.record_type
                existing_schema.updated_at = datetime.utcnow()
                stats['updated'] += 1
                logger.info(f"Updated schema: {schema.name}")
            else:
                # Create new schema
                new_schema = ZoomSSOTSchema(
                    name=schema.name,
                    description=schema.description,
                    schema_definition=schema.schema_definition,
                    platform=schema.platform,
                    record_type=schema.record_type
                )
                target_session.add(new_schema)
                stats['inserted'] += 1
                logger.info(f"Inserted new schema: {schema.name}")
                
        except Exception as e:
            stats['failed'] += 1
            logger.error(f"Error importing schema {schema.name}: {str(e)}")
    
    # Commit changes
    try:
        target_session.commit()
        logger.info("All changes committed successfully")
    except Exception as e:
        target_session.rollback()
        logger.error(f"Error committing changes to target database: {str(e)}")
        stats['failed'] = stats['total']
        stats['inserted'] = 0
        stats['updated'] = 0
    
    return stats


def main():
    """Main function to run the import process."""
    logger.info("Starting SSOT schema import process...")
    
    try:
        # Get source schemas
        source_schemas = get_source_db_ssot_schemas()
        
        if not source_schemas:
            logger.warning("No SSOT schemas found in source database. Nothing to import.")
            return
        
        # Connect to target database
        _, target_session = connect_to_target_db()
        
        # Import schemas
        stats = import_schemas(source_schemas, target_session)
        
        # Close session
        target_session.close()
        
        # Log results
        logger.info("Import process completed with the following results:")
        logger.info(f"Total schemas: {stats['total']}")
        logger.info(f"Inserted: {stats['inserted']}")
        logger.info(f"Updated: {stats['updated']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"Skipped: {stats['skipped']}")
        
    except Exception as e:
        logger.error(f"Import process failed: {str(e)}")
        sys.exit(1)
    
    logger.info("SSOT schema import process completed successfully")


if __name__ == "__main__":
    main()