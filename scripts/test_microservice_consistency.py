#!/usr/bin/env python3
"""
Automated Integration Test Framework for Microservice Consistency

This script provides one-button testing to ensure the external microservice
produces identical outputs to the existing zoom_transformer_helper.py logic.

Features:
- Automated setup and cleanup
- Path A vs Path B comparison
- Deep diff analysis with field-by-field reporting
- Iterative fix loop until perfect consistency
- Support for job IDs 1297-1301 (job types 33,39,45,77,78)
"""

import os
import sys
import json
import logging
import argparse
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from deepdiff import DeepDiff
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'test_consistency_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TestJobConfig:
    """Configuration for a single test job."""
    job_id: int
    job_type_id: int
    job_type_name: str
    description: str
    ssot_schema_id: int
    loader_id: int

@dataclass
class ComparisonResult:
    """Result of comparing two transformation outputs."""
    job_id: int
    job_type: str
    identical: bool
    differences: Dict[str, Any]
    path_a_count: int
    path_b_count: int
    error_message: Optional[str] = None

class MicroserviceConsistencyTester:
    """Main test framework for microservice consistency validation."""
    
    def __init__(self):
        self.main_etl_url = "http://127.0.0.1:8030"
        self.microservice_url = "http://localhost:3555"
        self.test_jobs = self._get_test_job_configs()
        self.superuser_token = None
        self.results = []
        
    def _get_test_job_configs(self) -> List[TestJobConfig]:
        """Get test job configurations for the 5 target job types."""
        return [
            TestJobConfig(
                job_id=1297,
                job_type_id=33,
                job_type_name="Sites",
                description="RingCentral → Zoom Sites (rc_zoom_sites)",
                ssot_schema_id=67,  # Will be updated dynamically
                loader_id=16
            ),
            TestJobConfig(
                job_id=1298,
                job_type_id=39,
                job_type_name="Users",
                description="RingCentral → Zoom Users (ringcentral_zoom_users)",
                ssot_schema_id=68,  # Will be updated dynamically
                loader_id=17
            ),
            TestJobConfig(
                job_id=1299,
                job_type_id=45,
                job_type_name="Call Queues",
                description="RingCentral → Zoom Call Queues (call_queue_members_optimized)",
                ssot_schema_id=69,  # Will be updated dynamically
                loader_id=18
            ),
            TestJobConfig(
                job_id=1300,
                job_type_id=77,
                job_type_name="Auto Receptionists",
                description="RingCentral → Zoom ARs (ringcentral_zoom_ars)",
                ssot_schema_id=70,  # Will be updated dynamically
                loader_id=19
            ),
            TestJobConfig(
                job_id=1301,
                job_type_id=78,
                job_type_name="IVR",
                description="RingCentral → Zoom IVR (ringcentral_zoom_ivr)",
                ssot_schema_id=71,  # Will be updated dynamically
                loader_id=20
            )
        ]
    
    def setup_superuser_auth(self):
        """Create superuser and get authentication token."""
        logger.info("Setting up superuser authentication...")
        
        # Use existing superuser credentials
        login_data = {
            "email": "admin@test.com",
            "password": "admin123"
        }
        
        try:
            response = requests.post(
                f"{self.main_etl_url}/api/auth/login/",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.superuser_token = data.get("access_token")
                logger.info("✅ Successfully authenticated as superuser")
                return True
            else:
                logger.error(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Authentication error: {str(e)}")
            return False
    
    def get_dynamic_ids(self, job_type_id: int) -> Tuple[Optional[int], Optional[int]]:
        """Get SSOT schema ID and loader ID for a job type dynamically."""
        try:
            # Connect to main ETL database
            conn = psycopg2.connect(
                host="127.0.0.1",
                port=5432,
                database="etl_db",
                user="postgres",
                password="password"
            )
            
            cursor = conn.cursor()
            
            # Get SSOT schema ID
            cursor.execute(
                "SELECT id FROM api_ssotschema WHERE job_type_id = %s AND is_default = true LIMIT 1",
                (job_type_id,)
            )
            ssot_result = cursor.fetchone()
            ssot_schema_id = ssot_result[0] if ssot_result else None
            
            # Get loader ID  
            cursor.execute(
                "SELECT id FROM api_loaderregistry WHERE job_type_id = %s AND is_default = true LIMIT 1",
                (job_type_id,)
            )
            loader_result = cursor.fetchone()
            loader_id = loader_result[0] if loader_result else None
            
            cursor.close()
            conn.close()
            
            logger.info(f"Job Type {job_type_id}: SSOT Schema ID = {ssot_schema_id}, Loader ID = {loader_id}")
            return ssot_schema_id, loader_id
            
        except Exception as e:
            logger.warning(f"Could not get dynamic IDs for job type {job_type_id}: {str(e)}")
            return None, None
    
    def reset_job_status(self, job_id: int) -> bool:
        """Reset job status to 'failed' before testing."""
        logger.info(f"Resetting job {job_id} status to 'failed'...")
        
        reset_data = {
            "job_id": job_id,
            "status": "failed"
        }
        
        try:
            response = requests.post(
                f"{self.main_etl_url}/api/etl/reset-job/",
                json=reset_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.superuser_token}"
                }
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Job {job_id} status reset successfully")
                return True
            else:
                logger.error(f"❌ Failed to reset job {job_id}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error resetting job {job_id}: {str(e)}")
            return False
    
    def clear_previous_data(self, job_id: int) -> bool:
        """Clear previous transformed and loaded stage records."""
        logger.info(f"Clearing previous test data for job {job_id}...")
        
        try:
            # Connect to main ETL database
            conn = psycopg2.connect(
                host="127.0.0.1",
                port=5432,
                database="etl_db", 
                user="postgres",
                password="password"
            )
            
            cursor = conn.cursor()
            
            # Delete previous test data
            cursor.execute(
                "DELETE FROM api_datarecord WHERE job_id = %s AND stage IN ('transformed', 'loaded')",
                (job_id,)
            )
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Cleared {deleted_count} previous records for job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error clearing data for job {job_id}: {str(e)}")
            return False
    
    def set_platform_integration_mode(self, platform_ids: List[int], mode: str) -> bool:
        """Set platform integration mode (internal vs microservice)."""
        logger.info(f"Setting platform integration mode to '{mode}' for platforms: {platform_ids}")
        
        try:
            # Connect to main ETL database
            conn = psycopg2.connect(
                host="127.0.0.1",
                port=5432,
                database="etl_db",
                user="postgres", 
                password="password"
            )
            
            cursor = conn.cursor()
            
            if mode == "microservice":
                # Set to microservice mode
                cursor.execute(
                    """UPDATE api_phoneplatform 
                       SET integration_mode = 'microservice', mcp_server_url = 'http://localhost:3555'
                       WHERE id IN %s""",
                    (tuple(platform_ids),)
                )
            else:
                # Set to internal mode
                cursor.execute(
                    """UPDATE api_phoneplatform 
                       SET integration_mode = 'internal', mcp_server_url = NULL
                       WHERE id IN %s""",
                    (tuple(platform_ids),)
                )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Platform integration mode set to '{mode}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting platform integration mode: {str(e)}")
            return False
    
    def run_transformation_path_a(self, job_config: TestJobConfig) -> Optional[List[Dict[str, Any]]]:
        """Run transformation using original internal path (zoom_transformer_helper.py)."""
        logger.info(f"🔄 Running Path A (Internal) for job {job_config.job_id}...")
        
        # Set platform to internal mode
        if not self.set_platform_integration_mode([2, 3], "internal"):
            return None
        
        transform_data = {
            "job_id": job_config.job_id,
            "source_platform_id": 4,  # RingCentral
            "job_type": job_config.job_type_id,
            "ssot_schema_id": job_config.ssot_schema_id
        }
        
        try:
            response = requests.post(
                f"{self.main_etl_url}/api/etl/transform-data/",
                json=transform_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.superuser_token}"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Path A completed for job {job_config.job_id}")
                return result.get("transformed_records", [])
            else:
                logger.error(f"❌ Path A failed for job {job_config.job_id}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Path A error for job {job_config.job_id}: {str(e)}")
            return None
    
    def run_transformation_path_b(self, job_config: TestJobConfig) -> Optional[List[Dict[str, Any]]]:
        """Run transformation using external microservice path."""
        logger.info(f"🔄 Running Path B (Microservice) for job {job_config.job_id}...")
        
        # Set platform to microservice mode
        if not self.set_platform_integration_mode([2, 3], "microservice"):
            return None
        
        transform_data = {
            "job_id": job_config.job_id,
            "source_platform_id": 4,  # RingCentral
            "job_type": job_config.job_type_id,
            "ssot_schema_id": job_config.ssot_schema_id
        }
        
        try:
            response = requests.post(
                f"{self.main_etl_url}/api/etl/transform-data/",
                json=transform_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.superuser_token}"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Path B completed for job {job_config.job_id}")
                return result.get("transformed_records", [])
            else:
                logger.error(f"❌ Path B failed for job {job_config.job_id}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Path B error for job {job_config.job_id}: {str(e)}")
            return None
    
    def compare_outputs(self, job_config: TestJobConfig, path_a_data: List[Dict], path_b_data: List[Dict]) -> ComparisonResult:
        """Compare outputs from both transformation paths."""
        logger.info(f"🔍 Comparing outputs for job {job_config.job_id} ({job_config.job_type_name})...")
        
        # Basic count comparison
        path_a_count = len(path_a_data) if path_a_data else 0
        path_b_count = len(path_b_data) if path_b_data else 0
        
        if path_a_count != path_b_count:
            logger.warning(f"⚠️ Record count mismatch: Path A = {path_a_count}, Path B = {path_b_count}")
        
        # Deep diff comparison
        try:
            # Sort both datasets for consistent comparison
            path_a_sorted = sorted(path_a_data, key=lambda x: json.dumps(x, sort_keys=True))
            path_b_sorted = sorted(path_b_data, key=lambda x: json.dumps(x, sort_keys=True))
            
            diff = DeepDiff(
                path_a_sorted,
                path_b_sorted,
                ignore_order=True,
                exclude_paths=["root[*]['id']", "root[*]['uuid]", "root[*]['created_at']", "root[*]['updated_at']"],
                view='text'
            )
            
            identical = len(diff) == 0
            
            if identical:
                logger.info(f"✅ Outputs are identical for job {job_config.job_id}")
            else:
                logger.warning(f"❌ Outputs differ for job {job_config.job_id}")
                logger.warning(f"Differences: {json.dumps(dict(diff), indent=2)}")
            
            return ComparisonResult(
                job_id=job_config.job_id,
                job_type=job_config.job_type_name,
                identical=identical,
                differences=dict(diff),
                path_a_count=path_a_count,
                path_b_count=path_b_count
            )
            
        except Exception as e:
            logger.error(f"❌ Error comparing outputs for job {job_config.job_id}: {str(e)}")
            return ComparisonResult(
                job_id=job_config.job_id,
                job_type=job_config.job_type_name,
                identical=False,
                differences={},
                path_a_count=path_a_count,
                path_b_count=path_b_count,
                error_message=str(e)
            )
    
    def generate_detailed_report(self):
        """Generate detailed test results report."""
        logger.info("\n" + "="*80)
        logger.info("MICROSERVICE CONSISTENCY TEST RESULTS")
        logger.info("="*80)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r.identical])
        failed_tests = total_tests - passed_tests
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        logger.info("\nDetailed Results:")
        logger.info("-" * 80)
        
        for result in self.results:
            status = "✅ PASS" if result.identical else "❌ FAIL"
            logger.info(f"{status} | Job {result.job_id} | {result.job_type} | A:{result.path_a_count} B:{result.path_b_count}")
            
            if not result.identical:
                logger.info(f"  Differences: {len(result.differences)} categories")
                for diff_type, details in result.differences.items():
                    logger.info(f"    - {diff_type}: {len(details) if isinstance(details, (list, dict)) else 1} items")
        
        logger.info("="*80)
        
        # Save detailed report to file
        report_file = f"consistency_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            report_data = {
                "test_timestamp": datetime.now().isoformat(),
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": (passed_tests/total_tests)*100,
                "results": [
                    {
                        "job_id": r.job_id,
                        "job_type": r.job_type,
                        "identical": r.identical,
                        "path_a_count": r.path_a_count,
                        "path_b_count": r.path_b_count,
                        "differences": r.differences,
                        "error_message": r.error_message
                    }
                    for r in self.results
                ]
            }
            json.dump(report_data, f, indent=2)
        
        logger.info(f"📄 Detailed report saved to: {report_file}")
        
        return failed_tests == 0
    
    def test_single_job(self, job_config: TestJobConfig) -> ComparisonResult:
        """Test a single job with both transformation paths."""
        logger.info(f"\n{'='*60}")
        logger.info(f"TESTING JOB {job_config.job_id}: {job_config.job_type_name}")
        logger.info(f"{'='*60}")
        
        # Update dynamic IDs
        ssot_schema_id, loader_id = self.get_dynamic_ids(job_config.job_type_id)
        if ssot_schema_id:
            job_config.ssot_schema_id = ssot_schema_id
        if loader_id:
            job_config.loader_id = loader_id
        
        # Setup phase
        if not self.reset_job_status(job_config.job_id):
            return ComparisonResult(
                job_id=job_config.job_id,
                job_type=job_config.job_type_name,
                identical=False,
                differences={},
                path_a_count=0,
                path_b_count=0,
                error_message="Failed to reset job status"
            )
        
        if not self.clear_previous_data(job_config.job_id):
            return ComparisonResult(
                job_id=job_config.job_id,
                job_type=job_config.job_type_name,
                identical=False,
                differences={},
                path_a_count=0,
                path_b_count=0,
                error_message="Failed to clear previous data"
            )
        
        # Run Path A (Internal)
        path_a_data = self.run_transformation_path_a(job_config)
        if path_a_data is None:
            return ComparisonResult(
                job_id=job_config.job_id,
                job_type=job_config.job_type_name,
                identical=False,
                differences={},
                path_a_count=0,
                path_b_count=0,
                error_message="Path A transformation failed"
            )
        
        # Clear data between tests
        self.clear_previous_data(job_config.job_id)
        
        # Run Path B (Microservice)
        path_b_data = self.run_transformation_path_b(job_config)
        if path_b_data is None:
            return ComparisonResult(
                job_id=job_config.job_id,
                job_type=job_config.job_type_name,
                identical=False,
                differences={},
                path_a_count=len(path_a_data),
                path_b_count=0,
                error_message="Path B transformation failed"
            )
        
        # Compare results
        result = self.compare_outputs(job_config, path_a_data, path_b_data)
        return result
    
    def run_all_tests(self, job_ids: Optional[List[int]] = None) -> bool:
        """Run tests for all jobs or specified job IDs."""
        logger.info("Starting microservice consistency tests...")
        
        # Filter jobs if specific IDs provided
        if job_ids:
            test_jobs = [job for job in self.test_jobs if job.job_id in job_ids]
        else:
            test_jobs = self.test_jobs
        
        if not test_jobs:
            logger.error("No test jobs found!")
            return False
        
        # Setup authentication
        if not self.setup_superuser_auth():
            logger.error("Failed to setup authentication")
            return False
        
        # Run tests
        self.results = []
        for job_config in test_jobs:
            result = self.test_single_job(job_config)
            self.results.append(result)
            
            # Brief status update
            status = "✅" if result.identical else "❌"
            logger.info(f"{status} Job {result.job_id} ({result.job_type}): {'IDENTICAL' if result.identical else 'DIFFERENT'}")
        
        # Generate final report
        success = self.generate_detailed_report()
        
        # Reset platform to internal mode for cleanup
        self.set_platform_integration_mode([2, 3], "internal")
        
        return success
    
    def interactive_fix_loop(self, job_ids: Optional[List[int]] = None) -> bool:
        """Interactive loop for fixing differences until consistency achieved."""
        logger.info("Starting interactive fix loop...")
        
        iteration = 1
        max_iterations = 10
        
        while iteration <= max_iterations:
            logger.info(f"\n🔄 ITERATION {iteration}/{max_iterations}")
            logger.info("="*50)
            
            success = self.run_all_tests(job_ids)
            
            if success:
                logger.info("🎉 All tests passed! Microservice is consistent with internal implementation.")
                return True
            
            failed_jobs = [r for r in self.results if not r.identical]
            logger.info(f"\n❌ {len(failed_jobs)} job(s) still have differences:")
            for job in failed_jobs:
                logger.info(f"  - Job {job.job_id} ({job.job_type})")
            
            if iteration < max_iterations:
                logger.info(f"\n⏳ Waiting for fixes... (Iteration {iteration+1} will start in 30 seconds)")
                logger.info("Please fix the microservice code and press Enter to continue, or Ctrl+C to exit...")
                
                try:
                    input()  # Wait for user input
                except KeyboardInterrupt:
                    logger.info("\n🛑 Test loop interrupted by user")
                    return False
            
            iteration += 1
        
        logger.error(f"❌ Maximum iterations ({max_iterations}) reached without achieving consistency")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test microservice consistency with internal implementation")
    parser.add_argument(
        "--job-ids",
        type=str,
        help="Comma-separated list of job IDs to test (e.g., 1297,1298,1299)"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive fix loop mode"
    )
    parser.add_argument(
        "--single-run",
        action="store_true", 
        help="Run tests once without interactive loop (default)"
    )
    
    args = parser.parse_args()
    
    # Parse job IDs if provided
    job_ids = None
    if args.job_ids:
        try:
            job_ids = [int(id.strip()) for id in args.job_ids.split(',')]
            logger.info(f"Testing specific job IDs: {job_ids}")
        except ValueError:
            logger.error("Invalid job IDs format. Use comma-separated integers.")
            sys.exit(1)
    
    # Create tester instance
    tester = MicroserviceConsistencyTester()
    
    # Run tests
    if args.interactive:
        success = tester.interactive_fix_loop(job_ids)
    else:
        success = tester.run_all_tests(job_ids)
    
    # Exit with appropriate code
    if success:
        logger.info("🎉 All tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()