#!/usr/bin/env python3
"""
Data Migration Script: Migrate Specific Job Types to Microservice Database

This script migrates data for job types 33,39,45,77,78 from the main ETL system
to the microservice database, ensuring exact compatibility.

Job Types:
- 33: Sites (rc_zoom_sites)
- 39: Users (ringcentral_zoom_users)
- 45: Call Queues (call_queue_members_optimized)
- 77: Auto Receptionists (ringcentral_zoom_ars)
- 78: IVR (ringcentral_zoom_ivr)
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

import django
from django.conf import settings
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configure Django settings to access the main ETL database
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etl_system.settings_development')
sys.path.append('/Users/trentcharlton/Documents/CloudWarriors/etl_prism_poc/backend')
django.setup()

# Import Django models from main system
from api.models import (
    ExtractorRegistry, LoaderRegistry, SSOTSchema, JobType, PhonePlatform
)

# Import microservice models
from database.models import (
    ExtractorConfig, LoaderConfig, TransformerConfig, JobTypeConfig, Base
)
from core.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TARGET_JOB_TYPE_IDS = [33, 39, 45, 77, 78]
ZOOM_PLATFORM_IDS = [2, 3]  # zoom_users, zoom_phone


def get_microservice_db_session():
    """Create database session for microservice database."""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def migrate_job_types():
    """Migrate JobType records for target job types."""
    logger.info(f"Migrating JobType records for IDs: {TARGET_JOB_TYPE_IDS}")
    
    # Query main system
    job_types = JobType.objects.filter(id__in=TARGET_JOB_TYPE_IDS)
    
    # Get microservice session
    db_session = get_microservice_db_session()
    
    migrated_count = 0
    
    try:
        for job_type in job_types:
            # Check if already exists
            existing = db_session.query(JobTypeConfig).filter(
                JobTypeConfig.uuid == str(job_type.uuid)
            ).first()
            
            if existing:
                logger.info(f"JobType {job_type.id} ({job_type.code}) already exists, updating...")
                # Update existing record
                existing.code = job_type.code
                existing.name = job_type.name
                existing.description = job_type.description
                existing.source_platform_id = job_type.source_platform_id
                existing.target_platform_id = job_type.target_platform_id
                existing.prompt = job_type.prompt
                existing.is_extraction_only = job_type.is_extraction_only
                existing.jobtype_dependencies = job_type.jobtype_dependencies
            else:
                # Create new record
                logger.info(f"Migrating JobType {job_type.id} ({job_type.code}) -> {job_type.name}")
                
                job_config = JobTypeConfig(
                    id=job_type.id,
                    uuid=str(job_type.uuid),
                    code=job_type.code,
                    name=job_type.name,
                    description=job_type.description,
                    source_platform_id=job_type.source_platform_id,
                    target_platform_id=job_type.target_platform_id,
                    prompt=job_type.prompt,
                    is_extraction_only=job_type.is_extraction_only,
                    jobtype_dependencies=job_type.jobtype_dependencies
                )
                db_session.add(job_config)
            
            migrated_count += 1
        
        db_session.commit()
        logger.info(f"Successfully migrated {migrated_count} JobType records")
        
    except Exception as e:
        logger.error(f"Error migrating JobType records: {str(e)}")
        db_session.rollback()
        raise
    finally:
        db_session.close()


def migrate_extractor_registry():
    """Migrate ExtractorRegistry records for target job types."""
    logger.info(f"Migrating ExtractorRegistry records for job types: {TARGET_JOB_TYPE_IDS}")
    
    # Query main system
    extractors = ExtractorRegistry.objects.filter(job_type_id__in=TARGET_JOB_TYPE_IDS)
    
    # Get microservice session
    db_session = get_microservice_db_session()
    
    migrated_count = 0
    
    try:
        for extractor in extractors:
            # Check if already exists
            existing = db_session.query(ExtractorConfig).filter(
                ExtractorConfig.uuid == str(extractor.uuid)
            ).first()
            
            if existing:
                logger.info(f"ExtractorRegistry {extractor.id} already exists, updating...")
                # Update existing record
                existing.job_type_id = extractor.job_type_id
                existing.platform_id = extractor.platform_id
                existing.extraction_plan = extractor.extraction_plan
                existing.group_id = extractor.group_id
                existing.is_default = extractor.is_default
            else:
                # Create new record
                logger.info(f"Migrating ExtractorRegistry {extractor.id} (JobType {extractor.job_type_id}, Platform {extractor.platform_id})")
                
                extractor_config = ExtractorConfig(
                    id=extractor.id,
                    uuid=str(extractor.uuid),
                    job_type_id=extractor.job_type_id,
                    platform_id=extractor.platform_id,
                    extraction_plan=extractor.extraction_plan,
                    group_id=extractor.group_id,
                    is_default=extractor.is_default
                )
                db_session.add(extractor_config)
            
            migrated_count += 1
        
        db_session.commit()
        logger.info(f"Successfully migrated {migrated_count} ExtractorRegistry records")
        
    except Exception as e:
        logger.error(f"Error migrating ExtractorRegistry records: {str(e)}")
        db_session.rollback()
        raise
    finally:
        db_session.close()


def migrate_loader_registry():
    """Migrate LoaderRegistry records for target job types."""
    logger.info(f"Migrating LoaderRegistry records for job types: {TARGET_JOB_TYPE_IDS}")
    
    # Query main system
    loaders = LoaderRegistry.objects.filter(job_type_id__in=TARGET_JOB_TYPE_IDS)
    
    # Get microservice session
    db_session = get_microservice_db_session()
    
    migrated_count = 0
    
    try:
        for loader in loaders:
            # Check if already exists
            existing = db_session.query(LoaderConfig).filter(
                LoaderConfig.uuid == str(loader.uuid)
            ).first()
            
            if existing:
                logger.info(f"LoaderRegistry {loader.id} already exists, updating...")
                # Update existing record
                existing.job_type_id = loader.job_type_id
                existing.platform_id = loader.platform_id
                existing.loading_plan = loader.loading_plan
                existing.group_id = loader.group_id
                existing.is_default = loader.is_default
            else:
                # Create new record
                logger.info(f"Migrating LoaderRegistry {loader.id} (JobType {loader.job_type_id}, Platform {loader.platform_id})")
                
                loader_config = LoaderConfig(
                    id=loader.id,
                    uuid=str(loader.uuid),
                    job_type_id=loader.job_type_id,
                    platform_id=loader.platform_id,
                    loading_plan=loader.loading_plan,
                    group_id=loader.group_id,
                    is_default=loader.is_default
                )
                db_session.add(loader_config)
            
            migrated_count += 1
        
        db_session.commit()
        logger.info(f"Successfully migrated {migrated_count} LoaderRegistry records")
        
    except Exception as e:
        logger.error(f"Error migrating LoaderRegistry records: {str(e)}")
        db_session.rollback()
        raise
    finally:
        db_session.close()


def migrate_transformer_registry():
    """Migrate SSOTSchema records (renamed to TransformerConfig) for target job types."""
    logger.info(f"Migrating SSOTSchema records (as TransformerConfig) for job types: {TARGET_JOB_TYPE_IDS}")
    
    # Query main system
    schemas = SSOTSchema.objects.filter(job_type_id__in=TARGET_JOB_TYPE_IDS)
    
    # Get microservice session
    db_session = get_microservice_db_session()
    
    migrated_count = 0
    
    try:
        for schema in schemas:
            # Check if already exists
            existing = db_session.query(TransformerConfig).filter(
                TransformerConfig.uuid == str(schema.uuid)
            ).first()
            
            if existing:
                logger.info(f"SSOTSchema {schema.id} already exists as TransformerConfig, updating...")
                # Update existing record
                existing.name = schema.name
                existing.description = schema.description
                existing.job_type_id = schema.job_type_id
                existing.transformation_config = schema.schema_yaml  # Rename field
                existing.is_active = schema.is_active
                existing.is_default = schema.is_default
                existing.group_id = schema.group_id
            else:
                # Create new record
                logger.info(f"Migrating SSOTSchema {schema.id} -> TransformerConfig (JobType {schema.job_type_id})")
                
                transformer_registry = TransformerConfig(
                    id=schema.id,
                    uuid=str(schema.uuid),
                    name=schema.name,
                    description=schema.description,
                    job_type_id=schema.job_type_id,
                    transformation_config=schema.schema_yaml,  # Rename field
                    is_active=schema.is_active,
                    is_default=schema.is_default,
                    group_id=schema.group_id
                )
                db_session.add(transformer_registry)
            
            migrated_count += 1
        
        db_session.commit()
        logger.info(f"Successfully migrated {migrated_count} SSOTSchema -> TransformerConfig records")
        
    except Exception as e:
        logger.error(f"Error migrating SSOTSchema -> TransformerConfig records: {str(e)}")
        db_session.rollback()
        raise
    finally:
        db_session.close()


def verify_migration():
    """Verify that migration completed successfully."""
    logger.info("Verifying migration...")
    
    db_session = get_microservice_db_session()
    
    try:
        # Count records in each table
        job_types_count = db_session.query(JobTypeConfig).filter(
            JobTypeConfig.id.in_(TARGET_JOB_TYPE_IDS)
        ).count()
        
        extractors_count = db_session.query(ExtractorConfig).filter(
            ExtractorConfig.job_type_id.in_(TARGET_JOB_TYPE_IDS)
        ).count()
        
        loaders_count = db_session.query(LoaderConfig).filter(
            LoaderConfig.job_type_id.in_(TARGET_JOB_TYPE_IDS)
        ).count()
        
        transformers_count = db_session.query(TransformerConfig).filter(
            TransformerConfig.job_type_id.in_(TARGET_JOB_TYPE_IDS)
        ).count()
        
        logger.info("Migration Verification Results:")
        logger.info(f"  JobTypeConfig records: {job_types_count}")
        logger.info(f"  ExtractorConfig records: {extractors_count}")
        logger.info(f"  LoaderConfig records: {loaders_count}")
        logger.info(f"  TransformerConfig records: {transformers_count}")
        
        # Verify specific job types exist
        logger.info("\nJob Types migrated:")
        for job_type_id in TARGET_JOB_TYPE_IDS:
            job_config = db_session.query(JobTypeConfig).filter(
                JobTypeConfig.id == job_type_id
            ).first()
            if job_config:
                logger.info(f"  {job_type_id}: {job_config.code} - {job_config.name}")
            else:
                logger.warning(f"  {job_type_id}: NOT FOUND")
        
    except Exception as e:
        logger.error(f"Error during verification: {str(e)}")
        raise
    finally:
        db_session.close()


def main():
    """Main migration function."""
    logger.info("Starting data migration for zoom platform microservice...")
    logger.info(f"Target job types: {TARGET_JOB_TYPE_IDS}")
    logger.info(f"Target zoom platforms: {ZOOM_PLATFORM_IDS}")
    
    try:
        # Run migrations
        migrate_job_types()
        migrate_extractor_registry()
        migrate_loader_registry()
        migrate_transformer_registry()
        
        # Verify results
        verify_migration()
        
        logger.info("✅ Data migration completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()