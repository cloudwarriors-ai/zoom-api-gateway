#!/usr/bin/env python3
"""
API-Based Data Migration Script

This script runs from the backend container and migrates data to the microservice
via API calls, mimicking the real production flow where backend never has direct
database access to the microservice.

Job Types to migrate: 33,39,45,77,78 (Sites, Users, Call Queues, ARs, IVR)
"""

import os
import sys
import json
import logging
import requests
from typing import Dict, List, Any, Optional

# Add Django to path and setup
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etl_system.settings_development')
import django
django.setup()

# Import Django models
from api.models import (
    ExtractorRegistry, LoaderRegistry, SSOTSchema, JobType, PhonePlatform
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TARGET_JOB_TYPE_IDS = [33, 39, 45, 77, 78]
MICROSERVICE_URL = "http://zoom-microservice:8000"  # Internal Docker network

class MicroserviceAPI:
    """API client for microservice communication."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
    def post_data(self, endpoint: str, data: Dict[str, Any]) -> bool:
        """Post data to microservice endpoint."""
        try:
            url = f"{self.base_url}{endpoint}"
            logger.info(f"Posting to {url}")
            
            response = self.session.post(url, json=data)
            response.raise_for_status()
            
            logger.info(f"✅ Successfully posted to {endpoint}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to post to {endpoint}: {str(e)}")
            return False
    
    def health_check(self) -> bool:
        """Check if microservice is healthy."""
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            logger.info("✅ Microservice is healthy")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Microservice health check failed: {str(e)}")
            return False

def migrate_job_types(api_client: MicroserviceAPI) -> bool:
    """Migrate JobType records via API."""
    logger.info(f"Migrating JobType records for IDs: {TARGET_JOB_TYPE_IDS}")
    
    job_types = JobType.objects.filter(id__in=TARGET_JOB_TYPE_IDS)
    success_count = 0
    
    for job_type in job_types:
        job_data = {
            "id": job_type.id,
            "uuid": str(job_type.uuid),
            "code": job_type.code,
            "name": job_type.name,
            "description": job_type.description,
            "source_platform_id": job_type.source_platform_id,
            "target_platform_id": job_type.target_platform_id,
            "prompt": job_type.prompt,
            "is_extraction_only": job_type.is_extraction_only,
            "jobtype_dependencies": job_type.jobtype_dependencies,
        }
        
        logger.info(f"Migrating JobType {job_type.id} ({job_type.code}) -> {job_type.name}")
        
        if api_client.post_data("/api/mcp/job-types", job_data):
            success_count += 1
        else:
            logger.error(f"Failed to migrate JobType {job_type.id}")
    
    logger.info(f"Successfully migrated {success_count}/{len(job_types)} JobType records")
    return success_count == len(job_types)

def migrate_extractor_registry(api_client: MicroserviceAPI) -> bool:
    """Migrate ExtractorRegistry records via API."""
    logger.info(f"Migrating ExtractorRegistry records for job types: {TARGET_JOB_TYPE_IDS}")
    
    extractors = ExtractorRegistry.objects.filter(job_type_id__in=TARGET_JOB_TYPE_IDS)
    success_count = 0
    
    for extractor in extractors:
        # Parse extraction_plan from JSON string to dict
        extraction_plan = extractor.extraction_plan
        if isinstance(extraction_plan, str):
            try:
                extraction_plan = json.loads(extraction_plan)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse extraction_plan JSON for ExtractorRegistry {extractor.id}")
                continue
        elif extraction_plan is None:
            extraction_plan = {}
        
        extractor_data = {
            "id": extractor.id,
            "uuid": str(extractor.uuid),
            "job_type_id": extractor.job_type_id,
            "platform_id": extractor.platform_id,
            "extraction_plan": extraction_plan,
            "group_id": extractor.group_id,
            "is_default": extractor.is_default,
        }
        
        logger.info(f"Migrating ExtractorRegistry {extractor.id} (JobType {extractor.job_type_id}, Platform {extractor.platform_id})")
        
        if api_client.post_data("/api/mcp/extractors", extractor_data):
            success_count += 1
        else:
            logger.error(f"Failed to migrate ExtractorRegistry {extractor.id}")
    
    logger.info(f"Successfully migrated {success_count}/{len(extractors)} ExtractorRegistry records")
    return success_count == len(extractors)

def migrate_loader_registry(api_client: MicroserviceAPI) -> bool:
    """Migrate LoaderRegistry records via API."""
    logger.info(f"Migrating LoaderRegistry records for job types: {TARGET_JOB_TYPE_IDS}")
    
    loaders = LoaderRegistry.objects.filter(job_type_id__in=TARGET_JOB_TYPE_IDS)
    success_count = 0
    
    for loader in loaders:
        # Parse loading_plan from JSON string to dict
        loading_plan = loader.loading_plan
        if isinstance(loading_plan, str):
            try:
                loading_plan = json.loads(loading_plan)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse loading_plan JSON for LoaderRegistry {loader.id}")
                continue
        elif loading_plan is None:
            loading_plan = {}
        
        loader_data = {
            "id": loader.id,
            "uuid": str(loader.uuid),
            "job_type_id": loader.job_type_id,
            "platform_id": loader.platform_id,
            "loading_plan": loading_plan,
            "group_id": loader.group_id,
            "is_default": loader.is_default,
        }
        
        logger.info(f"Migrating LoaderRegistry {loader.id} (JobType {loader.job_type_id}, Platform {loader.platform_id})")
        
        if api_client.post_data("/api/mcp/loaders", loader_data):
            success_count += 1
        else:
            logger.error(f"Failed to migrate LoaderRegistry {loader.id}")
    
    logger.info(f"Successfully migrated {success_count}/{len(loaders)} LoaderRegistry records")
    return success_count == len(loaders)

def migrate_transformer_registry(api_client: MicroserviceAPI) -> bool:
    """Migrate SSOTSchema records (as TransformerConfig) via API."""
    logger.info(f"Migrating SSOTSchema records (as TransformerConfig) for job types: {TARGET_JOB_TYPE_IDS}")
    
    schemas = SSOTSchema.objects.filter(job_type_id__in=TARGET_JOB_TYPE_IDS).exclude(id=39)  # Exclude duplicate schema 39
    success_count = 0
    
    for schema in schemas:
        transformer_data = {
            "id": schema.id,
            "uuid": str(schema.uuid),
            "name": schema.name,
            "description": schema.description,
            "job_type_id": schema.job_type_id,
            "transformation_config": schema.schema_yaml,  # Rename field
            "is_active": schema.is_active,
            "is_default": schema.is_default,
            "group_id": schema.group_id,
        }
        
        logger.info(f"Migrating SSOTSchema {schema.id} -> TransformerConfig (JobType {schema.job_type_id})")
        
        if api_client.post_data("/api/mcp/transformers", transformer_data):
            success_count += 1
        else:
            logger.error(f"Failed to migrate SSOTSchema {schema.id}")
    
    logger.info(f"Successfully migrated {success_count}/{len(schemas)} SSOTSchema -> TransformerConfig records")
    return success_count == len(schemas)

def verify_migration(api_client: MicroserviceAPI) -> bool:
    """Verify migration via API calls."""
    logger.info("Verifying migration...")
    
    try:
        # Check each endpoint for data
        endpoints = [
            "/api/mcp/job-types/count",
            "/api/mcp/extractors/count", 
            "/api/mcp/loaders/count",
            "/api/mcp/transformers/count"
        ]
        
        for endpoint in endpoints:
            try:
                response = api_client.session.get(f"{api_client.base_url}{endpoint}")
                if response.status_code == 200:
                    count_data = response.json()
                    logger.info(f"✅ {endpoint}: {count_data.get('count', 'unknown')} records")
                else:
                    logger.warning(f"⚠️ {endpoint}: endpoint not available (status {response.status_code})")
            except Exception as e:
                logger.warning(f"⚠️ {endpoint}: {str(e)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during verification: {str(e)}")
        return False

def main():
    """Main migration function."""
    logger.info("Starting API-based data migration for zoom platform microservice...")
    logger.info(f"Target job types: {TARGET_JOB_TYPE_IDS}")
    
    # Initialize API client
    api_client = MicroserviceAPI(MICROSERVICE_URL)
    
    # Health check
    if not api_client.health_check():
        logger.error("❌ Microservice is not healthy. Cannot proceed with migration.")
        sys.exit(1)
    
    try:
        # Run migrations (these will create MCP endpoints if they don't exist)
        results = []
        results.append(migrate_job_types(api_client))
        results.append(migrate_extractor_registry(api_client))
        results.append(migrate_loader_registry(api_client))
        results.append(migrate_transformer_registry(api_client))
        
        # Verify results
        verify_migration(api_client)
        
        if all(results):
            logger.info("✅ Data migration completed successfully!")
            return True
        else:
            logger.error(f"❌ Migration partially failed. Results: {results}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)