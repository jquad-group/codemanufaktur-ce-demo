"""Tests for database module components.

This module tests all database-related functionality including validation functions,
Pydantic models, and the SupabaseManager class with various scenarios.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pydantic import ValidationError

from src.database import (
    SupabaseManager,
    TableQueryRequest,
    RecordInsertRequest,
    RecordUpdateRequest,
    validate_table_name,
    validate_column_filters,
)


class TestValidationFunctions:
    """Test validation functions for security and input validation."""

    def test_validate_table_name_valid_names(self):
        """Test table name validation with valid names."""
        valid_names = ["users", "user_profiles", "orders123", "_private_table", "a_very_long_table_name"]
        
        for name in valid_names:
            result = validate_table_name(name)
            assert result["is_valid"] is True

    def test_validate_table_name_invalid_format(self):
        """Test table name validation with invalid formats."""
        invalid_names = [
            "123users",       # starts with number
            "user-profiles",  # contains hyphen
            "user profiles",  # contains space
            "user@table",     # contains special character
            "user.table",     # contains dot
            "",               # empty string
            "   ",            # whitespace only
        ]
        
        for name in invalid_names:
            result = validate_table_name(name)
            assert result["is_valid"] is False
            assert "error" in result

    def test_validate_table_name_system_tables(self):
        """Test table name validation blocks system tables."""
        system_names = [
            "pg_user",                # starts with "pg_"
            "information_schema",     # exact match
            "supabase_auth_users",   # starts with "supabase_"  
        ]
        
        for name in system_names:
            result = validate_table_name(name)
            assert result["is_valid"] is False
            assert ("system" in result["error"].lower() or 
                    "access" in result["error"].lower() or
                    "not allowed" in result["error"].lower())

    def test_validate_column_filters_valid_filters(self):
        """Test column filter validation with valid filters."""
        valid_filters = [
            {},  # empty filters
            {"name": "John", "age": 25, "active": True},
            {"id": 123, "status": "active"},
            {"created_at": "2024-01-01"},
        ]
        
        for filters in valid_filters:
            result = validate_column_filters(filters)
            assert result["is_valid"] is True

    def test_validate_column_filters_sql_injection(self):
        """Test column filter validation blocks SQL injection attempts."""
        dangerous_filters = [
            {"name": "'; DROP TABLE users; --"},
            {"id": "1 OR 1=1"},
            {"status": "/* comment */ active"},
            {"query": "UNION SELECT * FROM users"},
            {"exec": "xp_cmdshell 'ls'"},
            {"name": "admin' --"},
        ]
        
        for filters in dangerous_filters:
            result = validate_column_filters(filters)
            assert result["is_valid"] is False
            assert "dangerous pattern" in result["error"].lower() or "invalid" in result["error"].lower()

    def test_validate_column_filters_invalid_column_names(self):
        """Test column filter validation with invalid column names."""
        invalid_filters = [
            {"123column": "value"},      # starts with number
            {"user-name": "John"},       # contains hyphen
            {"user name": "John"},       # contains space
            {"user@domain": "value"},    # contains special character
        ]
        
        for filters in invalid_filters:
            result = validate_column_filters(filters)
            assert result["is_valid"] is False
            assert "column name" in result["error"].lower()

    def test_validate_column_filters_large_values(self):
        """Test column filter validation with excessively large values."""
        large_value = "a" * 1001  # exceed 1000 char limit
        filters = {"name": large_value}
        
        result = validate_column_filters(filters)
        assert result["is_valid"] is False
        assert "too long" in result["error"].lower()


class TestPydanticModels:
    """Test Pydantic models for data validation."""

    def test_table_query_request_valid(self):
        """Test TableQueryRequest with valid data."""
        # Valid request with all fields
        request = TableQueryRequest(
            table_name="users",
            limit=50,
            filters={"status": "active", "age": 25}
        )
        assert request.table_name == "users"
        assert request.limit == 50
        assert request.filters == {"status": "active", "age": 25}

        # Valid request with minimal fields
        request = TableQueryRequest(table_name="orders")
        assert request.table_name == "orders"
        assert request.limit is None
        assert request.filters is None

    def test_table_query_request_invalid_table_name(self):
        """Test TableQueryRequest validation fails with invalid table names."""
        with pytest.raises(ValidationError):
            TableQueryRequest(table_name="123invalid")

        with pytest.raises(ValidationError):
            TableQueryRequest(table_name="user-table")

        with pytest.raises(ValidationError):
            TableQueryRequest(table_name="")

    def test_table_query_request_invalid_limit(self):
        """Test TableQueryRequest validation fails with invalid limits."""
        with pytest.raises(ValidationError):
            TableQueryRequest(table_name="users", limit=0)  # below minimum

        with pytest.raises(ValidationError):
            TableQueryRequest(table_name="users", limit=1001)  # above maximum

        with pytest.raises(ValidationError):
            TableQueryRequest(table_name="users", limit=-5)  # negative

    def test_record_insert_request_valid(self):
        """Test RecordInsertRequest with valid data."""
        request = RecordInsertRequest(
            table_name="users",
            data={"name": "John Doe", "email": "john@example.com", "age": 30}
        )
        assert request.table_name == "users"
        assert request.data["name"] == "John Doe"
        assert request.data["email"] == "john@example.com"
        assert request.data["age"] == 30

    def test_record_insert_request_invalid(self):
        """Test RecordInsertRequest validation fails with invalid data."""
        with pytest.raises(ValidationError):
            RecordInsertRequest(table_name="123invalid", data={"name": "John"})

        # Empty data should fail validation - at least one field is required
        with pytest.raises(ValidationError):
            RecordInsertRequest(table_name="users", data={})

    def test_record_update_request_valid(self):
        """Test RecordUpdateRequest with valid data."""
        request = RecordUpdateRequest(
            table_name="users",
            filters={"id": 123},
            updates={"name": "Updated Name", "status": "inactive"}
        )
        assert request.table_name == "users"
        assert request.filters == {"id": 123}
        assert request.updates["name"] == "Updated Name"

    def test_record_update_request_invalid(self):
        """Test RecordUpdateRequest validation fails with invalid data."""
        with pytest.raises(ValidationError):
            RecordUpdateRequest(
                table_name="123invalid", 
                filters={"id": 1}, 
                updates={"name": "test"}
            )


class TestSupabaseManager:
    """Test SupabaseManager class functionality."""

    def test_init_valid_credentials(self):
        """Test SupabaseManager initialization with valid credentials."""
        manager = SupabaseManager(
            "https://test.supabase.co",
            "test-key-123"
        )
        assert manager.supabase_url == "https://test.supabase.co"
        assert manager.supabase_key == "test-key-123"
        assert manager.client is None  # Not initialized yet

    def test_init_invalid_credentials(self):
        """Test SupabaseManager initialization fails with invalid credentials."""
        # Missing URL
        with pytest.raises(ValueError, match="SUPABASE_URL is required"):
            SupabaseManager("", "test-key")

        # Missing key
        with pytest.raises(ValueError, match="SUPABASE_ANON_KEY is required"):
            SupabaseManager("https://test.supabase.co", "")

        # Invalid URL format
        with pytest.raises(ValueError, match="must be a valid HTTPS URL"):
            SupabaseManager("http://test.com", "test-key")

    @patch('src.database.create_client')
    def test_initialize_client_success(self, mock_create_client):
        """Test successful client initialization."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        manager = SupabaseManager("https://test.supabase.co", "test-key")
        manager.initialize()

        assert manager.client == mock_client
        mock_create_client.assert_called_once_with("https://test.supabase.co", "test-key")

    @patch('src.database.create_client')
    def test_initialize_client_failure(self, mock_create_client):
        """Test client initialization failure."""
        mock_create_client.side_effect = Exception("Connection failed")

        manager = SupabaseManager("https://test.supabase.co", "test-key")
        
        with pytest.raises(RuntimeError, match="Supabase client initialization failed"):
            manager.initialize()

    @patch('src.database.create_client')
    def test_get_client_lazy_initialization(self, mock_create_client):
        """Test get_client performs lazy initialization."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        manager = SupabaseManager("https://test.supabase.co", "test-key")
        
        # First call should initialize
        client = manager.get_client()
        assert client == mock_client
        assert manager.client == mock_client

        # Second call should return existing client
        client2 = manager.get_client()
        assert client2 == mock_client
        mock_create_client.assert_called_once()  # Only called once

    @patch('src.database.create_client')
    def test_test_connection_success(self, mock_create_client):
        """Test connection health check success."""
        mock_client = Mock()
        mock_result = Mock()
        mock_result.data = [{"count": 5}]
        mock_client.from_.return_value.select.return_value.limit.return_value.execute.return_value = mock_result
        mock_create_client.return_value = mock_client

        manager = SupabaseManager("https://test.supabase.co", "test-key")
        result = manager.test_connection()

        assert result["status"] == "connected"
        assert "healthy" in result["message"].lower()

    @patch('src.database.create_client')
    def test_test_connection_failure(self, mock_create_client):
        """Test connection health check failure."""
        mock_client = Mock()
        mock_client.from_.side_effect = Exception("Connection timeout")
        mock_create_client.return_value = mock_client

        manager = SupabaseManager("https://test.supabase.co", "test-key")
        result = manager.test_connection()

        assert result["status"] == "error"
        assert "Connection failed" in result["message"]

    @patch('src.database.create_client')
    def test_execute_query_invalid_table_name(self, mock_create_client):
        """Test execute_query fails with invalid table name."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        manager = SupabaseManager("https://test.supabase.co", "test-key")

        with pytest.raises(ValueError, match="Invalid table name"):
            manager.execute_query("123invalid", "select")

    @patch('src.database.create_client')
    def test_execute_query_unsupported_operation(self, mock_create_client):
        """Test execute_query fails with unsupported operation."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        manager = SupabaseManager("https://test.supabase.co", "test-key")

        with pytest.raises(ValueError, match="Unsupported operation"):
            manager.execute_query("users", "unsupported_op")

    @patch('src.database.create_client')
    def test_execute_select_query(self, mock_create_client):
        """Test execute_query with SELECT operation."""
        mock_client = Mock()
        mock_table = Mock()
        mock_query = Mock()
        mock_result = Mock()
        mock_result.data = [{"id": 1, "name": "John"}]

        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = mock_result
        mock_create_client.return_value = mock_client

        manager = SupabaseManager("https://test.supabase.co", "test-key")
        result = manager.execute_query(
            "users", 
            "select",
            filters={"status": "active"},
            limit=10
        )

        assert result.data == [{"id": 1, "name": "John"}]
        mock_table.select.assert_called_once_with("*")
        mock_query.eq.assert_called_once_with("status", "active")
        mock_query.limit.assert_called_once_with(10)

    @patch('src.database.create_client')
    def test_execute_insert_query(self, mock_create_client):
        """Test execute_query with INSERT operation."""
        mock_client = Mock()
        mock_table = Mock()
        mock_result = Mock()
        mock_result.data = [{"id": 1, "name": "John", "email": "john@example.com"}]

        mock_client.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value = mock_result
        mock_create_client.return_value = mock_client

        manager = SupabaseManager("https://test.supabase.co", "test-key")
        result = manager.execute_query(
            "users",
            "insert",
            data={"name": "John", "email": "john@example.com"}
        )

        assert result.data == [{"id": 1, "name": "John", "email": "john@example.com"}]
        mock_table.insert.assert_called_once_with({"name": "John", "email": "john@example.com"})

    @patch('src.database.create_client')
    def test_execute_update_query(self, mock_create_client):
        """Test execute_query with UPDATE operation."""
        mock_client = Mock()
        mock_table = Mock()
        mock_query = Mock()
        mock_result = Mock()
        mock_result.data = [{"id": 1, "name": "Updated Name"}]

        mock_client.table.return_value = mock_table
        mock_table.update.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value = mock_result
        mock_create_client.return_value = mock_client

        manager = SupabaseManager("https://test.supabase.co", "test-key")
        result = manager.execute_query(
            "users",
            "update",
            filters={"id": 1},
            updates={"name": "Updated Name"}
        )

        assert result.data == [{"id": 1, "name": "Updated Name"}]
        mock_table.update.assert_called_once_with({"name": "Updated Name"})
        mock_query.eq.assert_called_once_with("id", 1)

    @patch('src.database.create_client')
    def test_execute_query_database_error(self, mock_create_client):
        """Test execute_query handles database errors."""
        mock_client = Mock()
        mock_table = Mock()
        mock_table.select.side_effect = Exception("Database connection lost")
        mock_client.table.return_value = mock_table
        mock_create_client.return_value = mock_client

        manager = SupabaseManager("https://test.supabase.co", "test-key")

        with pytest.raises(RuntimeError, match="Database operation failed"):
            manager.execute_query("users", "select")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_table_name(self):
        """Test validation with very long table names."""
        long_name = "a" * 100  # Very long but valid name
        result = validate_table_name(long_name)
        assert result["is_valid"] is True

    def test_unicode_in_filters(self):
        """Test validation with unicode characters in filters."""
        unicode_filters = {
            "name": "José",
            "city": "São Paulo", 
            "description": "Testing with émojis 🎉"
        }
        result = validate_column_filters(unicode_filters)
        assert result["is_valid"] is True

    def test_none_values_in_data(self):
        """Test Pydantic models handle None values correctly."""
        request = RecordInsertRequest(
            table_name="users",
            data={"name": "John", "middle_name": None, "age": 30}
        )
        assert request.data["middle_name"] is None
        assert request.data["name"] == "John"

    def test_empty_strings_in_validation(self):
        """Test validation handles empty strings correctly."""
        result = validate_column_filters({"name": "", "status": "active"})
        assert result["is_valid"] is True  # Empty string is valid value

    def test_numeric_limits_in_request(self):
        """Test numeric boundary conditions in requests."""
        # Test maximum limit
        request = TableQueryRequest(table_name="users", limit=1000)
        assert request.limit == 1000

        # Test minimum limit
        request = TableQueryRequest(table_name="users", limit=1)
        assert request.limit == 1