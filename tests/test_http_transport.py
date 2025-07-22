"""Tests for HTTP transport implementation.

This module tests the FastAPI-based HTTP transport, JSON-RPC 2.0 compliance,
Server-Sent Events streaming, session management, and security features.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient
import httpx

# Import the HTTP transport and related components
from src.http_transport import HttpTransport, JsonRpcRequest, JsonRpcResponse, JsonRpcError
from src.transport_base import TransportError


class TestHttpTransportInitialization:
    """Test HTTP transport initialization and configuration."""
    
    def test_http_transport_init_defaults(self):
        """Test HTTP transport initialization with default values."""
        mock_mcp_server = Mock()
        mock_mcp_server._tools = {"list_tables": Mock()}
        
        transport = HttpTransport(mock_mcp_server)
        
        assert transport.host == "127.0.0.1"
        assert transport.port == 8000
        assert transport.cors_origins == ["http://localhost:3000"]
        assert transport.mcp_server == mock_mcp_server
        assert isinstance(transport._sessions, dict)
    
    def test_http_transport_init_custom_values(self):
        """Test HTTP transport initialization with custom values."""
        mock_mcp_server = Mock()
        cors_origins = ["http://example.com", "https://app.example.com"]
        
        transport = HttpTransport(
            mock_mcp_server,
            host="0.0.0.0",
            port=9000,
            cors_origins=cors_origins
        )
        
        assert transport.host == "0.0.0.0"
        assert transport.port == 9000
        assert transport.cors_origins == cors_origins
    
    def test_fastapi_app_configuration(self):
        """Test FastAPI app is properly configured."""
        mock_mcp_server = Mock()
        transport = HttpTransport(mock_mcp_server)
        
        assert transport.app.title == "Supabase MCP Server"
        assert transport.app.docs_url is None  # Security - docs disabled
        assert transport.app.redoc_url is None  # Security - redoc disabled


class TestJsonRpcModels:
    """Test JSON-RPC 2.0 Pydantic models."""
    
    def test_jsonrpc_request_valid(self):
        """Test valid JSON-RPC request model."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "list_tables",
            "params": {"limit": 10},
            "id": 1
        }
        
        request = JsonRpcRequest(**request_data)
        
        assert request.jsonrpc == "2.0"
        assert request.method == "list_tables"
        assert request.params == {"limit": 10}
        assert request.id == 1
    
    def test_jsonrpc_request_minimal(self):
        """Test minimal JSON-RPC request (notification)."""
        request_data = {
            "method": "list_tables"
        }
        
        request = JsonRpcRequest(**request_data)
        
        assert request.jsonrpc == "2.0"  # Default value
        assert request.method == "list_tables"
        assert request.params is None
        assert request.id is None
    
    def test_jsonrpc_response_success(self):
        """Test successful JSON-RPC response model."""
        response_data = {
            "id": 1,
            "result": {"tables": ["users", "orders"]}
        }
        
        response = JsonRpcResponse(**response_data)
        
        assert response.jsonrpc == "2.0"
        assert response.id == 1
        assert response.result == {"tables": ["users", "orders"]}
        assert response.error is None
    
    def test_jsonrpc_response_error(self):
        """Test error JSON-RPC response model."""
        error_data = {
            "code": -32603,
            "message": "Internal error"
        }
        response_data = {
            "id": 1,
            "error": error_data
        }
        
        response = JsonRpcResponse(**response_data)
        
        assert response.jsonrpc == "2.0"
        assert response.id == 1
        assert response.result is None
        assert response.error == error_data


class TestMcpEndpoint:
    """Test the main /mcp endpoint functionality."""
    
    @pytest.fixture
    def mock_mcp_server(self):
        """Create mock MCP server with tools."""
        server = Mock()
        server._tools = {
            "list_tables": AsyncMock(return_value="**Success**\n\nTables: users, orders"),
            "query_table": AsyncMock(return_value="**Success**\n\nData: [...]")
        }
        return server
    
    @pytest.fixture
    def transport(self, mock_mcp_server):
        """Create HTTP transport instance."""
        return HttpTransport(mock_mcp_server)
    
    @pytest.fixture
    def client(self, transport):
        """Create FastAPI test client."""
        return TestClient(transport.app)
    
    def test_mcp_endpoint_get_info(self, client):
        """Test GET /mcp returns server information."""
        response = client.get("/mcp")
        
        assert response.status_code == 200
        data = response.json()
        assert data["server"] == "Supabase MCP Server"
        assert data["transport"] == "streamable-http"
        assert data["protocol"] == "2025-03-26"
        assert "tools" in data
        assert "endpoints" in data
    
    def test_mcp_endpoint_valid_tool_call(self, client, mock_mcp_server):
        """Test successful tool call via POST /mcp."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "list_tables",
            "params": {},
            "id": 1
        }
        
        response = client.post("/mcp", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert "result" in data
        assert "**Success**" in data["result"]
        
        # Verify tool was called
        mock_mcp_server._tools["list_tables"].assert_called_once_with()
    
    def test_mcp_endpoint_tool_not_found(self, client):
        """Test tool not found error."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "nonexistent_tool",
            "params": {},
            "id": 1
        }
        
        response = client.post("/mcp", json=request_data)
        
        assert response.status_code == 404
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert "error" in data
        assert data["error"]["code"] == -32601  # Method not found
    
    def test_mcp_endpoint_tool_execution_error(self, client, mock_mcp_server):
        """Test tool execution error handling."""
        # Mock tool to raise exception
        mock_mcp_server._tools["list_tables"].side_effect = Exception("Database error")
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "list_tables",
            "params": {},
            "id": 1
        }
        
        response = client.post("/mcp", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert "error" in data
        assert data["error"]["code"] == -32603  # Internal error
        assert "Database error" in data["error"]["message"]
    
    def test_mcp_endpoint_invalid_json(self, client):
        """Test invalid JSON request."""
        response = client.post(
            "/mcp",
            data="invalid json{",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "error" in data
        assert data["error"]["code"] == -32700  # Parse error
    
    def test_mcp_endpoint_invalid_jsonrpc(self, client):
        """Test invalid JSON-RPC structure."""
        request_data = {
            "jsonrpc": "1.0",  # Wrong version
            "method": 123,     # Method should be string
        }
        
        response = client.post("/mcp", json=request_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "error" in data
        assert data["error"]["code"] == -32600  # Invalid Request


class TestSessionManagement:
    """Test session management functionality."""
    
    @pytest.fixture
    def mock_mcp_server(self):
        """Create mock MCP server."""
        server = Mock()
        server._tools = {"list_tables": AsyncMock(return_value="Success")}
        return server
    
    @pytest.fixture
    def transport(self, mock_mcp_server):
        """Create HTTP transport instance."""
        return HttpTransport(mock_mcp_server)
    
    @pytest.fixture
    def client(self, transport):
        """Create FastAPI test client."""
        return TestClient(transport.app)
    
    def test_new_session_creation(self, client):
        """Test new session is created automatically."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "list_tables",
            "id": 1
        }
        
        response = client.post("/mcp", json=request_data)
        
        assert response.status_code == 200
        assert "Mcp-Session-Id" in response.headers
        session_id = response.headers["Mcp-Session-Id"]
        assert len(session_id) > 0
    
    def test_existing_session_validation(self, client, transport):
        """Test existing session header validation."""
        # First request creates session
        response1 = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "list_tables",
            "id": 1
        })
        session_id = response1.headers["Mcp-Session-Id"]
        
        # Second request with valid session ID
        response2 = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "list_tables",
            "id": 2
        }, headers={"mcp-session-id": session_id})
        
        assert response2.status_code == 200
        assert response2.headers.get("Mcp-Session-Id") == session_id
    
    def test_invalid_session_handling(self, client):
        """Test handling of invalid session ID."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "list_tables",
            "id": 1
        }
        
        # Request with invalid session ID
        response = client.post("/mcp", json=request_data, 
                             headers={"mcp-session-id": "invalid-session-id"})
        
        assert response.status_code == 200
        # Should create new session when invalid one is provided
        assert "Mcp-Session-Id" not in response.headers or response.headers.get("Mcp-Session-Id") != "invalid-session-id"


class TestServerSentEvents:
    """Test Server-Sent Events streaming functionality."""
    
    @pytest.fixture
    def mock_mcp_server(self):
        """Create mock MCP server with streaming tool."""
        server = Mock()
        # Return large result that should trigger streaming
        large_result = "**Success**\n\n" + "Large data result. " * 500  # > 5000 chars
        server._tools = {"query_table": AsyncMock(return_value=large_result)}
        return server
    
    @pytest.fixture
    def transport(self, mock_mcp_server):
        """Create HTTP transport instance."""
        return HttpTransport(mock_mcp_server)
    
    def test_should_stream_large_result(self, transport):
        """Test _should_stream returns True for large results."""
        large_result = "Large result " * 500  # > 5000 chars
        assert transport._should_stream("query_table", large_result) is True
    
    def test_should_stream_small_result(self, transport):
        """Test _should_stream returns False for small results."""
        small_result = "Small result"
        assert transport._should_stream("insert_record", small_result) is False
    
    def test_should_stream_specific_methods(self, transport):
        """Test _should_stream returns True for specific methods."""
        result = "Normal result"
        assert transport._should_stream("query_table", result) is True
        assert transport._should_stream("list_tables", result) is True
        assert transport._should_stream("describe_table", result) is True
    
    @pytest.mark.asyncio
    async def test_sse_response_format(self, transport):
        """Test SSE response format."""
        result = "Test result"
        request_id = 123
        
        sse_response = transport._create_sse_response(result, request_id)
        
        assert sse_response.media_type == "text/event-stream"
        assert sse_response.headers["Cache-Control"] == "no-cache"
        assert sse_response.headers["Connection"] == "keep-alive"
    
    def test_streaming_endpoint_with_large_result(self, mock_mcp_server):
        """Test endpoint returns SSE for large results."""
        # This test would require more complex async testing setup
        # For now, we verify the _should_stream logic works correctly
        transport = HttpTransport(mock_mcp_server)
        
        large_result = "**Success**\n\n" + "Large data " * 1000
        should_stream = transport._should_stream("query_table", large_result)
        assert should_stream is True


class TestSecurityFeatures:
    """Test security features like CORS and Origin validation."""
    
    @pytest.fixture
    def transport(self):
        """Create HTTP transport with specific CORS origins."""
        mock_mcp_server = Mock()
        mock_mcp_server._tools = {"list_tables": AsyncMock(return_value="Success")}
        return HttpTransport(
            mock_mcp_server,
            cors_origins=["https://example.com", "https://app.example.com"]
        )
    
    def test_valid_origin_localhost(self, transport):
        """Test localhost origins are always valid."""
        assert transport._is_valid_origin("http://localhost:3000") is True
        assert transport._is_valid_origin("http://127.0.0.1:8080") is True
    
    def test_valid_origin_configured(self, transport):
        """Test configured CORS origins are valid."""
        assert transport._is_valid_origin("https://example.com") is True
        assert transport._is_valid_origin("https://app.example.com") is True
    
    def test_invalid_origin(self, transport):
        """Test invalid origins are rejected."""
        assert transport._is_valid_origin("https://malicious.com") is False
        assert transport._is_valid_origin("http://evil.example.com") is False
    
    def test_no_origin_header(self, transport):
        """Test missing origin header is acceptable."""
        assert transport._is_valid_origin(None) is True
        assert transport._is_valid_origin("") is True
    
    def test_malformed_origin(self, transport):
        """Test malformed origin URLs are rejected."""
        assert transport._is_valid_origin("not-a-url") is False
        assert transport._is_valid_origin("://invalid") is False


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        mock_mcp_server = Mock()
        transport = HttpTransport(mock_mcp_server)
        return TestClient(transport.app)
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["transport"] == "http"


class TestTransportLifecycle:
    """Test transport lifecycle management."""
    
    @pytest.fixture
    def mock_mcp_server(self):
        """Create mock MCP server."""
        server = Mock()
        server._tools = {}
        return server
    
    def test_transport_initialization(self, mock_mcp_server):
        """Test transport initializes correctly."""
        transport = HttpTransport(mock_mcp_server)
        
        assert transport.is_running is False
        assert len(transport._sessions) == 0
    
    @pytest.mark.asyncio
    async def test_session_cleanup(self, mock_mcp_server):
        """Test session cleanup functionality."""
        transport = HttpTransport(mock_mcp_server)
        
        # Add a session
        transport._sessions["test-session"] = {
            "created_at": 0,  # Very old timestamp
            "last_seen": 0,
            "requests": 1
        }
        
        # Run cleanup
        transport._cleanup_sessions()
        
        # Session should be cleaned up
        assert "test-session" not in transport._sessions


class TestErrorHandling:
    """Test comprehensive error handling scenarios."""
    
    @pytest.fixture
    def client(self):
        """Create test client with error-prone server."""
        mock_mcp_server = Mock()
        mock_mcp_server._tools = {
            "error_tool": AsyncMock(side_effect=Exception("Tool error")),
            "timeout_tool": AsyncMock(side_effect=asyncio.TimeoutError("Timeout"))
        }
        transport = HttpTransport(mock_mcp_server)
        return TestClient(transport.app)
    
    def test_tool_exception_handling(self, client):
        """Test tool exceptions are properly handled."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "error_tool",
            "id": 1
        }
        
        response = client.post("/mcp", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32603
        assert "Tool error" in data["error"]["message"]
    
    def test_async_timeout_handling(self, client):
        """Test async timeout handling."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "timeout_tool",
            "id": 1
        }
        
        response = client.post("/mcp", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32603


@pytest.mark.asyncio
async def test_transport_error_exception():
    """Test TransportError exception."""
    error = TransportError(
        message="Test transport error",
        transport_type="http",
        details={"host": "localhost", "port": 8000}
    )
    
    assert str(error) == "Test transport error"
    assert error.transport_type == "http"
    assert error.details["host"] == "localhost"
    assert error.details["port"] == 8000