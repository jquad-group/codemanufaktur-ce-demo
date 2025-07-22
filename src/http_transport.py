"""FastAPI-based HTTP transport for MCP server following 2025-03-26 specification.

This module implements the streamable HTTP transport protocol for MCP,
providing a single /mcp endpoint with JSON-RPC 2.0 support, Server-Sent Events
for streaming responses, and session management capabilities.
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ValidationError

from .transport_base import TransportBase, TransportError

# Configure logging to stderr only (never stdout - corrupts MCP JSON-RPC)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("supabase-mcp.http_transport")


class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 request model."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


class JsonRpcResponse(BaseModel):
    """JSON-RPC 2.0 response model."""
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class JsonRpcError(BaseModel):
    """JSON-RPC 2.0 error model."""
    code: int
    message: str
    data: Optional[Any] = None


class HttpTransport(TransportBase):
    """FastAPI-based HTTP transport implementing MCP streamable HTTP protocol.
    
    Follows MCP specification 2025-03-26 for streamable HTTP transport:
    - Single /mcp endpoint for all interactions
    - JSON-RPC 2.0 message format
    - Server-Sent Events for streaming responses
    - Optional session management with Mcp-Session-Id header
    - Origin validation and CORS support
    """
    
    def __init__(
        self, 
        mcp_server: Any,
        host: str = "127.0.0.1",
        port: int = 8000,
        cors_origins: Optional[List[str]] = None
    ):
        """Initialize HTTP transport.
        
        Args:
            mcp_server: FastMCP server instance with registered tools
            host: Host to bind to (default: 127.0.0.1 for security)
            port: Port to listen on
            cors_origins: Allowed CORS origins for web-based clients
        """
        super().__init__(mcp_server)
        self.host = host
        self.port = port
        self.cors_origins = cors_origins or ["http://localhost:3000"]
        
        # Session management
        self._sessions: Dict[str, Dict[str, Any]] = {}
        
        # FastAPI app
        self.app = FastAPI(
            title="Supabase MCP Server",
            description="Model Context Protocol server with streamable HTTP transport",
            version="0.1.0",
            docs_url=None,  # Disable docs for security
            redoc_url=None  # Disable redoc for security
        )
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )
        
        # Setup routes
        self._setup_routes()
        
        logger.info(f"HTTP transport initialized on {host}:{port}")
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes following MCP streamable HTTP specification."""
        
        @self.app.post("/mcp")
        async def mcp_endpoint(request: Request) -> Response:
            """Main MCP endpoint following JSON-RPC 2.0 specification.
            
            Handles all MCP tool invocations and supports both immediate
            responses and streaming via Server-Sent Events.
            """
            # Security: Validate Origin header
            origin = request.headers.get("origin")
            if origin and not self._is_valid_origin(origin):
                logger.warning(f"Invalid origin rejected: {origin}")
                raise HTTPException(status_code=403, detail="Invalid origin")
            
            try:
                # Parse JSON-RPC request
                body = await request.json()
                rpc_request = JsonRpcRequest(**body)
                
                logger.debug(f"MCP request: {rpc_request.method}")
                
                # Handle session management
                session_id = self._handle_session(request)
                
                # Route to MCP tool
                try:
                    result = await self.invoke_tool(
                        rpc_request.method,
                        rpc_request.params or {}
                    )
                    
                    # Check if response should be streamed
                    if self._should_stream(rpc_request.method, result):
                        return self._create_sse_response(result, rpc_request.id, session_id)
                    else:
                        # Standard JSON-RPC response
                        response = JsonRpcResponse(
                            id=rpc_request.id,
                            result=result
                        )
                        json_response = JSONResponse(response.model_dump())
                        
                        # Add session header if session exists
                        if session_id:
                            json_response.headers["Mcp-Session-Id"] = session_id
                        
                        return json_response
                        
                except ValueError as e:
                    # Tool not found or validation error
                    error = JsonRpcError(
                        code=-32601,  # Method not found
                        message=str(e)
                    )
                    response = JsonRpcResponse(
                        id=rpc_request.id,
                        error=error.model_dump()
                    )
                    return JSONResponse(
                        response.model_dump(),
                        status_code=404
                    )
                    
                except Exception as e:
                    # Internal error
                    logger.error(f"Tool execution failed: {e}")
                    error = JsonRpcError(
                        code=-32603,  # Internal error
                        message=f"Tool execution failed: {str(e)}"
                    )
                    response = JsonRpcResponse(
                        id=rpc_request.id,
                        error=error.model_dump()
                    )
                    return JSONResponse(
                        response.model_dump(),
                        status_code=500
                    )
                    
            except ValidationError as e:
                # Invalid JSON-RPC request
                logger.warning(f"Invalid JSON-RPC request: {e}")
                error = JsonRpcError(
                    code=-32600,  # Invalid Request
                    message="Invalid JSON-RPC request",
                    data=e.errors()
                )
                response = JsonRpcResponse(error=error.model_dump())
                return JSONResponse(
                    response.model_dump(),
                    status_code=400
                )
                
            except json.JSONDecodeError:
                # Invalid JSON
                error = JsonRpcError(
                    code=-32700,  # Parse error
                    message="Invalid JSON"
                )
                response = JsonRpcResponse(error=error.model_dump())
                return JSONResponse(
                    response.model_dump(),
                    status_code=400
                )
        
        @self.app.get("/mcp")
        async def mcp_info() -> Dict[str, Any]:
            """Provide basic server information for GET requests."""
            tools = self.get_available_tools()
            return {
                "server": "Supabase MCP Server",
                "transport": "streamable-http",
                "protocol": "2025-03-26",
                "tools": list(tools.keys()),
                "endpoints": {
                    "mcp": "/mcp (POST for JSON-RPC, GET for info)"
                }
            }
        
        @self.app.get("/health")
        async def health_check() -> Dict[str, str]:
            """Health check endpoint."""
            return {"status": "healthy", "transport": "http"}
    
    def _handle_session(self, request: Request) -> Optional[str]:
        """Handle session management via Mcp-Session-Id header.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Session ID if session management is enabled
        """
        session_id = request.headers.get("mcp-session-id")
        
        if session_id:
            # Validate existing session
            if session_id not in self._sessions:
                logger.warning(f"Invalid session ID: {session_id}")
                return None
            logger.debug(f"Using existing session: {session_id}")
        else:
            # Create new session (optional for MCP compatibility)
            session_id = str(uuid.uuid4())
            self._sessions[session_id] = {
                "created_at": asyncio.get_event_loop().time(),
                "requests": 0
            }
            logger.debug(f"Created new session: {session_id}")
        
        # Update session stats
        if session_id in self._sessions:
            self._sessions[session_id]["requests"] += 1
            self._sessions[session_id]["last_seen"] = asyncio.get_event_loop().time()
        
        return session_id
    
    def _is_valid_origin(self, origin: str) -> bool:
        """Validate request origin for security.
        
        Args:
            origin: Origin header value
            
        Returns:
            True if origin is allowed, False otherwise
        """
        if not origin:
            return True  # No origin header is okay
        
        try:
            parsed = urlparse(origin)
            
            # Allow localhost for development
            if parsed.hostname in ["localhost", "127.0.0.1"]:
                return True
            
            # Check configured CORS origins
            return origin in self.cors_origins
            
        except Exception:
            logger.warning(f"Failed to parse origin: {origin}")
            return False
    
    def _should_stream(self, method: str, result: Any) -> bool:
        """Determine if response should be streamed via SSE.
        
        Args:
            method: MCP tool method name
            result: Tool execution result
            
        Returns:
            True if response should be streamed
        """
        # Stream for large results or specific methods
        if isinstance(result, str) and len(result) > 5000:
            return True
        
        # Stream for specific methods that might return large datasets
        streaming_methods = {"query_table", "list_tables", "describe_table"}
        if method in streaming_methods:
            return True
        
        return False
    
    def _create_sse_response(
        self, 
        result: Any, 
        request_id: Any, 
        session_id: Optional[str] = None
    ) -> StreamingResponse:
        """Create Server-Sent Events response for streaming.
        
        Args:
            result: Tool execution result
            request_id: JSON-RPC request ID
            session_id: Optional session ID
            
        Returns:
            StreamingResponse with SSE format
        """
        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                # Send result as SSE event
                response_data = JsonRpcResponse(
                    id=request_id,
                    result=result
                ).model_dump()
                
                # Format as SSE event
                event_data = json.dumps(response_data)
                yield f"data: {event_data}\n\n"
                
                logger.debug(f"SSE response sent for request ID: {request_id}")
                
            except Exception as e:
                # Send error as SSE event
                logger.error(f"SSE streaming error: {e}")
                error_response = JsonRpcResponse(
                    id=request_id,
                    error=JsonRpcError(
                        code=-32603,
                        message=f"Streaming error: {str(e)}"
                    ).model_dump()
                ).model_dump()
                
                error_data = json.dumps(error_response)
                yield f"data: {error_data}\n\n"
        
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type"
        }
        
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers=headers
        )
    
    def _cleanup_sessions(self) -> None:
        """Clean up expired sessions."""
        current_time = asyncio.get_event_loop().time()
        session_timeout = 3600  # 1 hour
        
        expired_sessions = [
            session_id for session_id, session_data in self._sessions.items()
            if current_time - session_data.get("last_seen", 0) > session_timeout
        ]
        
        for session_id in expired_sessions:
            del self._sessions[session_id]
            logger.debug(f"Expired session cleaned up: {session_id}")
    
    async def start(self) -> None:
        """Start the HTTP transport server."""
        try:
            # Get configuration from environment
            host = os.getenv("HTTP_HOST", self.host)
            port = int(os.getenv("HTTP_PORT", self.port))
            
            logger.info(f"Starting HTTP server on {host}:{port}")
            
            # Configure uvicorn
            config = uvicorn.Config(
                app=self.app,
                host=host,
                port=port,
                log_level="info",
                access_log=False,  # Reduce noise
                server_header=False,  # Security
                date_header=False  # Security
            )
            
            self.server = uvicorn.Server(config)
            
            # Start server in background task
            self._server_task = asyncio.create_task(self.server.serve())
            
            # Start session cleanup task
            self._cleanup_task = asyncio.create_task(self._session_cleanup_loop())
            
            logger.info("HTTP transport started successfully")
            
            # Wait for server to be ready
            while not self.server.started:
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Failed to start HTTP transport: {e}")
            raise TransportError(
                f"HTTP transport startup failed: {str(e)}", 
                "http",
                {"host": host, "port": port}
            ) from e
    
    async def stop(self) -> None:
        """Stop the HTTP transport server."""
        logger.info("Stopping HTTP transport...")
        
        try:
            # Cancel cleanup task
            if hasattr(self, '_cleanup_task') and not self._cleanup_task.done():
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Stop uvicorn server
            if hasattr(self, 'server') and self.server:
                self.server.should_exit = True
                if hasattr(self, '_server_task') and not self._server_task.done():
                    await self._server_task
            
            # Clean up sessions
            self._sessions.clear()
            
            logger.info("HTTP transport stopped")
            
        except Exception as e:
            logger.error(f"Error stopping HTTP transport: {e}")
    
    async def _session_cleanup_loop(self) -> None:
        """Background task to clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                self._cleanup_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
                await asyncio.sleep(60)  # Wait before retry