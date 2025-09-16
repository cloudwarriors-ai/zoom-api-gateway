"""
Unit tests for the RingCentralToZoomUsersTransformer.

This module contains unit tests for the RingCentralToZoomUsersTransformer class.
"""

import unittest
from unittest.mock import patch, MagicMock

from app.transformers.raw_to_zoom.ringcentral_to_zoom.users_transformer import RingCentralToZoomUsersTransformer


class TestRingCentralToZoomUsersTransformer(unittest.TestCase):
    """Test cases for the RingCentralToZoomUsersTransformer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.transformer = RingCentralToZoomUsersTransformer()
    
    def test_transform_single_basic_user(self):
        """Test transforming a basic RingCentral user to Zoom format."""
        # Arrange
        rc_user = {
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
        }
        
        # Act
        result = self.transformer.transform_single(rc_user)
        
        # Assert
        self.assertEqual(result["email"], "test@example.com")
        self.assertEqual(result["first_name"], "Test")
        self.assertEqual(result["last_name"], "User")
        self.assertEqual(result["type"], 1)  # Basic user
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["timezone"], "America/New_York")
    
    def test_transform_single_with_contact_info(self):
        """Test transforming a RingCentral user with contact info to Zoom format."""
        # Arrange
        rc_user = {
            "id": "456",
            "email": "contact@example.com",
            "firstName": "Contact",
            "lastName": "User",
            "status": "Active",
            "contact": {
                "department": "Engineering",
                "jobTitle": "Software Engineer",
                "company": "Example Corp"
            },
            "regionalSettings": {
                "timezone": {
                    "id": "61",
                    "name": "Pacific Time"
                }
            }
        }
        
        # Act
        result = self.transformer.transform_single(rc_user)
        
        # Assert
        self.assertEqual(result["email"], "contact@example.com")
        self.assertEqual(result["first_name"], "Contact")
        self.assertEqual(result["last_name"], "User")
        self.assertEqual(result["dept"], "Engineering")
        self.assertEqual(result["job_title"], "Software Engineer")
        self.assertEqual(result["company"], "Example Corp")
        self.assertEqual(result["timezone"], "America/Los_Angeles")
    
    def test_transform_single_with_missing_fields(self):
        """Test transforming a RingCentral user with missing fields."""
        # Arrange
        rc_user = {
            "id": "789",
            "email": "incomplete@example.com"
        }
        
        # Act
        result = self.transformer.transform_single(rc_user)
        
        # Assert
        self.assertEqual(result["email"], "incomplete@example.com")
        self.assertEqual(result["first_name"], "Unknown")  # Default value
        self.assertEqual(result["last_name"], "User")  # Default value
        self.assertEqual(result["type"], 1)  # Default type
        self.assertEqual(result["status"], "inactive")  # Default status
        self.assertEqual(result["timezone"], "America/New_York")  # Default timezone
    
    def test_transform_single_with_job_options(self):
        """Test transforming a RingCentral user with job options."""
        # Arrange
        rc_user = {
            "id": "123",
            "email": "test@example.com",
            "firstName": "Test",
            "lastName": "User",
            "status": "Active"
        }
        
        job = MagicMock()
        job.options = {
            "default_type": 2,  # Override to Admin
            "default_status": "pending",  # Override status
            "site_id": "site-123"  # Add site ID
        }
        
        # Act
        result = self.transformer.transform_single(rc_user, job)
        
        # Assert
        self.assertEqual(result["email"], "test@example.com")
        self.assertEqual(result["type"], 2)  # Overridden to Admin
        self.assertEqual(result["status"], "pending")  # Overridden status
        self.assertEqual(result["site_id"], "site-123")  # Added site ID


if __name__ == "__main__":
    unittest.main()