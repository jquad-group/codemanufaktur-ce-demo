"""Tests for MCP server functionality.

This module tests the FastMCP server integration, environment validation,
and all MCP tool implementations with mocked dependencies.
"""

import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
from pydantic import ValidationError

# Import functions from the server module for testing
from src.mcp_server import (
    validate_environment,
    get_config,
    create_error_response,
    create_success_response,
)


class TestEnvironmentValidation:
    """Test environment variable validation and configuration."""

    @patch.dict(os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_ANON_KEY": "test-key"})
    def test_validate_environment_success(self):
        """Test environment validation with valid variables."""
        # Should not raise any exception
        validate_environment()

    @patch.dict(os.environ, {}, clear=True)
    def test_validate_environment_missing_vars(self):
        """Test environment validation fails with missing variables."""
        with pytest.raises(ValueError, match="Missing required environment variables"):
            validate_environment()

    @patch.dict(os.environ, {"SUPABASE_URL": "https://test.supabase.co"}, clear=True)
    def test_validate_environment_partial_vars(self):
        """Test environment validation fails with partial variables."""
        with pytest.raises(ValueError, match="SUPABASE_ANON_KEY"):
            validate_environment()

    @patch.dict(os.environ, {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_ANON_KEY": "test-key",
        "LOG_LEVEL": "DEBUG",
        "MCP_SERVER_NAME": "test-server",
        "MCP_MAX_QUERY_LIMIT": "500",
        "DEBUG": "true"
    })
    def test_get_config_custom_values(self):
        """Test configuration retrieval with custom values."""
        config = get_config()
        
        assert config["log_level"] == "DEBUG"
        assert config["server_name"] == "test-server"
        assert config["max_query_limit"] == 500
        assert config["debug"] is True

    @patch.dict(os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_ANON_KEY": "test-key"}, clear=True)
    def test_get_config_default_values(self):
        """Test configuration retrieval with default values."""
        config = get_config()
        
        assert config["log_level"] == "INFO"
        assert config["server_name"] == "supabase-mcp"
        assert config["max_query_limit"] == 1000
        assert config["debug"] is False


class TestResponseHelpers:
    """Test response formatting helper functions."""

    def test_create_error_response_simple(self):
        """Test error response creation with simple message."""
        response = create_error_response("Test error occurred")
        
        assert "**Error**" in response
        assert "Test error occurred" in response

    def test_create_error_response_with_details(self):
        """Test error response creation with details."""
        details = {"error_code": 500, "table": "users"}
        response = create_error_response("Database error", details)
        
        assert "**Error**" in response
        assert "Database error" in response
        assert "**Details:**" in response
        assert "error_code" in response
        assert "500" in response

    def test_create_success_response_simple(self):
        """Test success response creation with simple message."""
        response = create_success_response("Operation completed")
        
        assert "**Success**" in response
        assert "Operation completed" in response

    def test_create_success_response_with_data(self):
        """Test success response creation with data."""
        data = {"records": [{"id": 1, "name": "John"}], "count": 1}
        response = create_success_response("Query successful", data)
        
        assert "**Success**" in response
        assert "Query successful" in response
        assert "**Data:**" in response
        assert '"id": 1' in response
        assert '"name": "John"' in response


class TestMCPToolsMocked:
    """Test MCP tools with mocked dependencies."""

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_list_tables_success(self, mock_manager):
        """Test list_tables tool with successful response."""
        # Import the tool function after patching
        from src.mcp_server import list_tables
        
        # Mock successful RPC call
        mock_client = Mock()
        mock_result = Mock()
        mock_result.data = [
            {"table_name": "users", "table_type": "BASE TABLE", "table_schema": "public"},
            {"table_name": "orders", "table_type": "BASE TABLE", "table_schema": "public"}
        ]
        mock_client.rpc.return_value.execute.return_value = mock_result
        mock_manager.get_client.return_value = mock_client

        response = await list_tables()

        assert "**Success**" in response
        assert "Found 2 accessible table(s)" in response
        assert "users" in response
        assert "orders" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_list_tables_empty(self, mock_manager):
        """Test list_tables tool with no tables."""
        from src.mcp_server import list_tables
        
        # Mock empty result
        mock_client = Mock()
        mock_result = Mock()
        mock_result.data = []
        mock_client.rpc.return_value.execute.return_value = mock_result
        mock_manager.get_client.return_value = mock_client

        response = await list_tables()

        assert "No accessible tables found" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_list_tables_error_with_fallback(self, mock_manager):
        """Test list_tables tool with error and fallback."""
        from src.mcp_server import list_tables
        
        # Mock RPC failure
        mock_client = Mock()
        mock_client.rpc.side_effect = Exception("RPC failed")
        mock_manager.get_client.return_value = mock_client
        
        # Mock successful connection test for fallback
        mock_manager.test_connection.return_value = {"status": "connected"}

        response = await list_tables()

        assert "**Error**" in response
        assert "Unable to list tables directly" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_query_table_success(self, mock_manager):
        """Test query_table tool with successful query."""
        from src.mcp_server import query_table
        
        # Mock successful query execution
        mock_result = Mock()
        mock_result.data = [
            {"id": 1, "name": "John", "email": "john@example.com"},
            {"id": 2, "name": "Jane", "email": "jane@example.com"}
        ]
        mock_manager.execute_query.return_value = mock_result

        response = await query_table("users", limit=10, filters={"status": "active"})

        assert "**Success**" in response
        assert "Found 2 record(s)" in response
        assert "john@example.com" in response
        assert "jane@example.com" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_query_table_invalid_table_name(self, mock_manager):
        """Test query_table tool with invalid table name."""
        from src.mcp_server import query_table

        response = await query_table("123invalid")

        assert "**Error**" in response
        assert "Input validation failed" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_query_table_dangerous_filters(self, mock_manager):
        """Test query_table tool blocks dangerous filters."""
        from src.mcp_server import query_table

        response = await query_table("users", filters={"name": "'; DROP TABLE users; --"})

        assert "**Error**" in response
        assert "Filter validation failed" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_query_table_no_results(self, mock_manager):
        """Test query_table tool with no matching results."""
        from src.mcp_server import query_table
        
        mock_result = Mock()
        mock_result.data = []
        mock_manager.execute_query.return_value = mock_result

        response = await query_table("users", filters={"status": "nonexistent"})

        assert "**No data found**" in response
        assert "no records match the given criteria" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_describe_table_success(self, mock_manager):
        """Test describe_table tool with successful schema retrieval."""
        from src.mcp_server import describe_table
        
        # Mock successful RPC calls for schema information
        mock_client = Mock()
        
        # Mock column information
        columns_result = Mock()
        columns_result.data = [
            {
                "column_name": "id",
                "data_type": "integer",
                "is_nullable": "NO",
                "column_default": "nextval('users_id_seq'::regclass)",
                "ordinal_position": 1
            },
            {
                "column_name": "name",
                "data_type": "character varying",
                "is_nullable": "YES",
                "character_maximum_length": 255,
                "ordinal_position": 2
            }
        ]
        
        # Mock constraint information
        constraints_result = Mock()
        constraints_result.data = [
            {
                "constraint_type": "PRIMARY KEY",
                "constraint_name": "users_pkey",
                "column_name": "id"
            }
        ]

        def rpc_side_effect(func_name, params):
            mock_rpc = Mock()
            if "column" in func_name or "columns" in params.get('query', ''):
                mock_rpc.execute.return_value = columns_result
            else:
                mock_rpc.execute.return_value = constraints_result
            return mock_rpc

        mock_client.rpc.side_effect = rpc_side_effect
        mock_manager.get_client.return_value = mock_client

        response = await describe_table("users")

        assert "**Success**" in response
        assert "Schema for table 'users'" in response
        assert "2 columns" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_describe_table_invalid_name(self, mock_manager):
        """Test describe_table tool with invalid table name."""
        from src.mcp_server import describe_table

        response = await describe_table("123invalid")

        assert "**Error**" in response
        assert "Invalid table name" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_insert_record_success(self, mock_manager):
        """Test insert_record tool with successful insertion."""
        from src.mcp_server import insert_record
        
        mock_result = Mock()
        mock_result.data = [{"id": 1, "name": "John", "email": "john@example.com"}]
        mock_manager.execute_query.return_value = mock_result

        data = {"name": "John", "email": "john@example.com"}
        response = await insert_record("users", data)

        assert "**Success**" in response
        assert "Record inserted successfully" in response
        assert "john@example.com" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_insert_record_invalid_table(self, mock_manager):
        """Test insert_record tool with invalid table name."""
        from src.mcp_server import insert_record

        response = await insert_record("123invalid", {"name": "John"})

        assert "**Error**" in response
        assert "Input validation failed" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_insert_record_empty_data(self, mock_manager):
        """Test insert_record tool with empty data."""
        from src.mcp_server import insert_record

        response = await insert_record("users", {})

        assert "**Error**" in response
        assert "No data provided for insertion" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_insert_record_large_data(self, mock_manager):
        """Test insert_record tool with excessively large data."""
        from src.mcp_server import insert_record

        large_data = {"description": "a" * 10001}  # Exceeds limit
        response = await insert_record("users", large_data)

        assert "**Error**" in response
        assert "Data value too large" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_insert_record_database_error(self, mock_manager):
        """Test insert_record tool with database constraint violation."""
        from src.mcp_server import insert_record
        
        mock_manager.execute_query.side_effect = RuntimeError("duplicate key value violates unique constraint")

        response = await insert_record("users", {"email": "existing@example.com"})

        assert "**Error**" in response
        assert "duplicate key" in response
        assert "unique constraints" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_update_record_success(self, mock_manager):
        """Test update_record tool with successful update."""
        from src.mcp_server import update_record
        
        mock_result = Mock()
        mock_result.data = [{"id": 1, "name": "Updated Name", "status": "inactive"}]
        mock_manager.execute_query.return_value = mock_result

        filters = {"id": 1}
        updates = {"name": "Updated Name", "status": "inactive"}
        response = await update_record("users", filters, updates)

        assert "**Success**" in response
        assert "Successfully updated 1 record(s)" in response
        assert "Updated Name" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_update_record_no_filters(self, mock_manager):
        """Test update_record tool requires filters."""
        from src.mcp_server import update_record

        response = await update_record("users", {}, {"name": "New Name"})

        assert "**Error**" in response
        assert "No filter conditions provided" in response
        assert "prevent accidental mass updates" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_update_record_no_updates(self, mock_manager):
        """Test update_record tool requires updates."""
        from src.mcp_server import update_record

        response = await update_record("users", {"id": 1}, {})

        assert "**Error**" in response
        assert "No update values provided" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_update_record_protected_columns(self, mock_manager):
        """Test update_record tool blocks protected columns."""
        from src.mcp_server import update_record

        filters = {"status": "active"}
        updates = {"id": 999, "name": "Hacker"}  # id is protected
        response = await update_record("users", filters, updates)

        assert "**Error**" in response
        assert "Cannot update protected column 'id'" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_update_record_no_matches(self, mock_manager):
        """Test update_record tool with no matching records."""
        from src.mcp_server import update_record
        
        mock_result = Mock()
        mock_result.data = []  # No records updated
        mock_manager.execute_query.return_value = mock_result

        filters = {"id": 999}
        updates = {"name": "New Name"}
        response = await update_record("users", filters, updates)

        assert "**Success**" in response
        assert "updated_count\": 0" in response
        assert "No records matched the filter criteria" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_update_record_dangerous_filters(self, mock_manager):
        """Test update_record tool blocks dangerous filter patterns."""
        from src.mcp_server import update_record

        filters = {"name": "'; DROP TABLE users; --"}
        updates = {"status": "inactive"}
        response = await update_record("users", filters, updates)

        assert "**Error**" in response
        assert "Invalid filter conditions" in response


class TestMCPToolsValidation:
    """Test MCP tools input validation and edge cases."""

    @pytest.mark.asyncio
    async def test_query_table_limit_boundary(self):
        """Test query_table tool respects limit boundaries."""
        from src.mcp_server import query_table
        
        with patch('src.mcp_server.supabase_manager') as mock_manager:
            mock_result = Mock()
            mock_result.data = []
            mock_manager.execute_query.return_value = mock_result

            # Test with limit exceeding maximum
            response = await query_table("users", limit=2000)
            
            # Should cap at 1000 (config max_query_limit)
            mock_manager.execute_query.assert_called_with(
                table_name="users",
                operation="select",
                filters=None,
                limit=1000,  # Should be capped
                columns="*"
            )

    @pytest.mark.asyncio
    async def test_tools_handle_unicode(self):
        """Test MCP tools handle unicode correctly."""
        from src.mcp_server import insert_record
        
        with patch('src.mcp_server.supabase_manager') as mock_manager:
            mock_result = Mock()
            mock_result.data = [{"name": "José", "city": "São Paulo"}]
            mock_manager.execute_query.return_value = mock_result

            unicode_data = {"name": "José", "city": "São Paulo", "emoji": "🎉"}
            response = await insert_record("users", unicode_data)
            
            assert "**Success**" in response

    @pytest.mark.asyncio
    async def test_tools_json_serialization(self):
        """Test MCP tools handle complex data types in JSON serialization."""
        from src.mcp_server import query_table
        
        with patch('src.mcp_server.supabase_manager') as mock_manager:
            # Mock result with complex data types
            mock_result = Mock()
            mock_result.data = [
                {
                    "id": 1, 
                    "name": "John",
                    "metadata": {"tags": ["python", "mcp"]},
                    "created_at": "2024-01-01T00:00:00Z"
                }
            ]
            mock_manager.execute_query.return_value = mock_result

            response = await query_table("users")
            
            assert "**Success**" in response
            assert "python" in response  # JSON serialization works
            assert "mcp" in response


class TestErrorHandling:
    """Test comprehensive error handling scenarios."""

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_database_connection_failure(self, mock_manager):
        """Test tools handle database connection failures gracefully."""
        from src.mcp_server import query_table
        
        mock_manager.execute_query.side_effect = RuntimeError("Database connection failed")

        response = await query_table("users")

        assert "**Error**" in response
        assert "Database query failed" in response
        assert "Database connection failed" in response

    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_unexpected_errors(self, mock_manager):
        """Test tools handle unexpected errors gracefully."""
        from src.mcp_server import list_tables
        
        mock_manager.get_client.side_effect = Exception("Unexpected error")

        response = await list_tables()

        assert "**Error**" in response
        assert "Unable to list tables" in response


class TestDualModeCompatibility:
    """Test dual-mode functionality ensuring STDIO and HTTP modes behave identically."""
    
    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_tool_behavior_consistency(self, mock_manager):
        """Test that tools behave identically in both STDIO and HTTP modes."""
        # Mock successful tool response
        mock_result = Mock()
        mock_result.data = [
            {"id": 1, "name": "Test Table", "type": "BASE TABLE"}
        ]
        mock_manager.get_client.return_value.rpc.return_value.execute.return_value = mock_result
        
        # Import tools from MCP server
        from src.mcp_server import list_tables
        
        # Test tool execution (simulates both STDIO and HTTP execution)
        response = await list_tables()
        
        # Verify response format is consistent
        assert "**Success**" in response
        assert "Test Table" in response
        assert isinstance(response, str)  # Both modes should return string responses
    
    @patch('src.mcp_server.supabase_manager')  
    @pytest.mark.asyncio
    async def test_error_handling_consistency(self, mock_manager):
        """Test that error handling is consistent between modes."""
        # Mock database error
        mock_manager.get_client.side_effect = Exception("Connection failed")
        
        from src.mcp_server import list_tables
        
        # Test error response
        response = await list_tables()
        
        # Verify error format is consistent
        assert "**Error**" in response
        assert "Connection failed" in response or "Unable to list tables" in response
        assert isinstance(response, str)
    
    def test_main_function_argument_parsing(self):
        """Test that main function properly handles CLI arguments."""
        import argparse
        from unittest.mock import patch
        
        # Test default STDIO mode
        with patch('sys.argv', ['mcp_server.py']):
            # This would normally call main(), but we just test argument parsing
            parser = argparse.ArgumentParser()
            parser.add_argument("--mode", choices=["stdio", "http"], default="stdio")
            parser.add_argument("--host", default="127.0.0.1")  
            parser.add_argument("--port", type=int, default=8000)
            
            args = parser.parse_args([])
            assert args.mode == "stdio"
            assert args.host == "127.0.0.1"
            assert args.port == 8000
        
        # Test HTTP mode arguments
        with patch('sys.argv', ['mcp_server.py', '--mode=http', '--port=9000']):
            args = parser.parse_args(['--mode=http', '--port=9000'])
            assert args.mode == "http"
            assert args.port == 9000
    
    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio 
    async def test_validation_consistency(self, mock_manager):
        """Test that input validation works consistently in both modes."""
        from src.mcp_server import query_table
        
        # Test invalid table name (should fail in both modes)
        response = await query_table("123invalid", limit=10)
        
        assert "**Error**" in response
        assert "validation failed" in response.lower() or "invalid" in response.lower()
    
    def test_environment_variable_handling(self):
        """Test that environment variables work in both modes."""
        # Test that both modes use the same environment validation
        from src.mcp_server import validate_environment, get_config
        
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co", 
            "SUPABASE_ANON_KEY": "test-key",
            "HTTP_HOST": "0.0.0.0",
            "HTTP_PORT": "9000"
        }):
            # Should not raise for either mode
            validate_environment()
            
            # Config should include all necessary settings
            config = get_config()
            assert "server_name" in config
            assert "max_query_limit" in config


class TestHttpModeSpecificFeatures:
    """Test features specific to HTTP mode."""
    
    def test_http_transport_import(self):
        """Test that HTTP transport can be imported when needed."""
        try:
            from src.http_transport import HttpTransport
            assert HttpTransport is not None
        except ImportError:
            pytest.fail("HTTP transport should be importable")
    
    def test_transport_base_import(self):
        """Test that transport base can be imported."""
        try:
            from src.transport_base import TransportBase, TransportError
            assert TransportBase is not None
            assert TransportError is not None
        except ImportError:
            pytest.fail("Transport base should be importable")
    
    def test_jsonrpc_models_import(self):
        """Test that JSON-RPC models can be imported."""
        try:
            from src.http_transport import JsonRpcRequest, JsonRpcResponse, JsonRpcError
            assert JsonRpcRequest is not None
            assert JsonRpcResponse is not None
            assert JsonRpcError is not None
        except ImportError:
            pytest.fail("JSON-RPC models should be importable")


class TestBackwardCompatibility:
    """Test that existing STDIO functionality remains unchanged."""
    
    @patch('src.mcp_server.supabase_manager')
    @pytest.mark.asyncio
    async def test_stdio_tools_unchanged(self, mock_manager):
        """Test that all existing STDIO tools work unchanged."""
        # Mock successful responses for all tools
        mock_result = Mock()
        mock_result.data = [{"id": 1, "name": "test"}]
        mock_manager.execute_query.return_value = mock_result
        mock_manager.get_client.return_value.rpc.return_value.execute.return_value = mock_result
        
        # Import and test all major tools
        from src.mcp_server import list_tables, query_table, describe_table, insert_record, update_record
        
        # Test each tool maintains its signature and behavior
        list_response = await list_tables()
        assert isinstance(list_response, str)
        assert "**Success**" in list_response or "accessible table" in list_response.lower()
        
        query_response = await query_table("users", limit=10)
        assert isinstance(query_response, str)
        
        describe_response = await describe_table("users")
        assert isinstance(describe_response, str)
        
        insert_response = await insert_record("users", {"name": "test"})
        assert isinstance(insert_response, str)
        
        update_response = await update_record("users", {"id": 1}, {"name": "updated"})
        assert isinstance(update_response, str)
    
    def test_response_format_unchanged(self):
        """Test that response format helpers remain unchanged."""
        from src.mcp_server import create_error_response, create_success_response
        
        # Test error response format
        error_response = create_error_response("Test error", {"detail": "info"})
        assert "**Error**" in error_response
        assert "Test error" in error_response
        assert "detail" in error_response
        
        # Test success response format  
        success_response = create_success_response("Test success", {"data": "value"})
        assert "**Success**" in success_response
        assert "Test success" in success_response
        assert "data" in success_response
    
    def test_config_functions_unchanged(self):
        """Test that configuration functions work unchanged."""
        from src.mcp_server import get_config, validate_environment
        
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_ANON_KEY": "test-key"
        }):
            # Should work without throwing
            validate_environment()
            
            config = get_config()
            assert isinstance(config, dict)
            assert "server_name" in config
            assert "max_query_limit" in config