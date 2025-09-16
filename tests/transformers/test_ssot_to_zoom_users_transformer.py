"""
Unit tests for the SSOTToZoomUsersTransformer.

This module contains unit tests for the SSOTToZoomUsersTransformer class.
"""

import unittest
from unittest.mock import patch, MagicMock

from app.transformers.ssot_to_zoom.users_transformer import SSOTToZoomUsersTransformer


class TestSSOTToZoomUsersTransformer(unittest.TestCase):
    """Test cases for the SSOTToZoomUsersTransformer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.transformer = SSOTToZoomUsersTransformer()
    
    def test_transform_single_basic_user(self):
        """Test transforming a basic SSOT user to Zoom format."""
        # Arrange
        ssot_user = {
            "id": "123",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "user",
            "status": "active",
            "timezone": "America/New_York"
        }
        
        # Act
        result = self.transformer.transform_single(ssot_user)
        
        # Assert
        self.assertEqual(result["email"], "test@example.com")
        self.assertEqual(result["first_name"], "Test")
        self.assertEqual(result["last_name"], "User")
        self.assertEqual(result["type"], 1)  # Basic user
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["timezone"], "America/New_York")
    
    def test_transform_single_admin_user(self):
        """Test transforming an admin SSOT user to Zoom format."""
        # Arrange
        ssot_user = {
            "id": "456",
            "email": "admin@example.com",
            "first_name": "Admin",
            "last_name": "User",
            "role": "admin",
            "status": "active",
            "timezone": "America/Los_Angeles"
        }
        
        # Act
        result = self.transformer.transform_single(ssot_user)
        
        # Assert
        self.assertEqual(result["email"], "admin@example.com")
        self.assertEqual(result["first_name"], "Admin")
        self.assertEqual(result["last_name"], "User")
        self.assertEqual(result["type"], 2)  # Admin user
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["timezone"], "America/Los_Angeles")
    
    def test_transform_single_with_missing_fields(self):
        """Test transforming a user with missing fields."""
        # Arrange
        ssot_user = {
            "id": "789",
            "email": "incomplete@example.com"
        }
        
        # Act
        result = self.transformer.transform_single(ssot_user)
        
        # Assert
        self.assertEqual(result["email"], "incomplete@example.com")
        self.assertEqual(result["first_name"], "Unknown")  # Default value
        self.assertEqual(result["last_name"], "User")  # Default value
        self.assertEqual(result["type"], 1)  # Default type
        self.assertEqual(result["status"], "inactive")  # Default status
        self.assertEqual(result["timezone"], "America/New_York")  # Default timezone
    
    def test_transform_single_with_job_options(self):
        """Test transforming a user with job options."""
        # Arrange
        ssot_user = {
            "id": "123",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "user",
            "status": "active"
        }
        
        job = MagicMock()
        job.options = {
            "default_type": 2,  # Override to Admin
            "default_status": "pending"  # Override status
        }
        
        # Act
        result = self.transformer.transform_single(ssot_user, job)
        
        # Assert
        self.assertEqual(result["email"], "test@example.com")
        self.assertEqual(result["type"], 2)  # Overridden to Admin
        self.assertEqual(result["status"], "pending")  # Overridden status


if __name__ == "__main__":
    unittest.main()