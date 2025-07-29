"""Abstract base class for MCP transport implementations.

This module provides a common interface for different transport mechanisms
(STDIO, HTTP) used by the MCP server, enabling clean separation of transport
logic from core server functionality.
"""

import asyncio
import logging
import sys
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable

# Configure logging to stderr only (never stdout - corrupts MCP JSON-RPC)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("supabase-mcp.transport")


class TransportBase(ABC):
    """Abstract base class for MCP transport implementations.
    
    Provides a common interface for different transport mechanisms while
    maintaining proper error handling and lifecycle management.
    """
    
    def __init__(self, mcp_server: Any):
        """Initialize transport with MCP server instance.
        
        Args:
            mcp_server: FastMCP server instance with registered tools
        """
        self.mcp_server = mcp_server
        self._running = False
        self._shutdown_event = asyncio.Event()
        logger.info(f"Initialized {self.__class__.__name__}")
    
    @abstractmethod
    async def start(self) -> None:
        """Start the transport server.
        
        This method should initialize and start the transport mechanism,
        making it ready to receive and handle MCP requests.
        
        Raises:
            RuntimeError: If the transport fails to start
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the transport server.
        
        This method should gracefully shutdown the transport mechanism,
        closing connections and cleaning up resources.
        """
        pass
    
    async def run(self) -> None:
        """Run the transport server with proper lifecycle management.
        
        This method provides common lifecycle management for all transport
        implementations, including startup, shutdown handling, and error recovery.
        """
        try:
            logger.info(f"Starting {self.__class__.__name__}")
            self._running = True
            await self.start()
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
        except Exception as e:
            logger.error(f"Transport error: {e}")
            raise RuntimeError(f"Transport failed: {str(e)}") from e
        finally:
            await self._graceful_shutdown()
    
    async def _graceful_shutdown(self) -> None:
        """Perform graceful shutdown with proper resource cleanup."""
        if self._running:
            logger.info(f"Shutting down {self.__class__.__name__}")
            try:
                await self.stop()
            except Exception as e:
                logger.error(f"Error during transport shutdown: {e}")
            finally:
                self._running = False
                logger.info("Transport shutdown completed")
    
    def shutdown(self) -> None:
        """Signal the transport to shutdown.
        
        This method can be called from signal handlers or other contexts
        to initiate a graceful shutdown.
        """
        logger.info("Shutdown requested")
        self._shutdown_event.set()
    
    @property
    def is_running(self) -> bool:
        """Check if the transport is currently running."""
        return self._running
    
    def get_available_tools(self) -> Dict[str, Callable]:
        """Get available MCP tools from the server.
        
        Returns:
            Dict mapping tool names to their implementation functions
        """
        # FastMCP stores tools in _tools attribute
        if hasattr(self.mcp_server, '_tools'):
            return self.mcp_server._tools
        
        # Fallback: try to extract tools from server
        tools = {}
        for attr_name in dir(self.mcp_server):
            # Skip attributes that might trigger lazy initialization
            if attr_name in ['session_manager']:
                continue
            
            try:
                attr = getattr(self.mcp_server, attr_name)
                if callable(attr) and hasattr(attr, '_mcp_tool'):
                    tools[attr_name] = attr
            except RuntimeError:
                # Skip attributes that can't be accessed yet
                continue
        
        return tools
    
    async def invoke_tool(self, method: str, params: Dict[str, Any]) -> Any:
        """Invoke an MCP tool with given parameters.
        
        Args:
            method: Tool method name
            params: Tool parameters
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool method is not found
            Exception: If tool execution fails
        """
        tools = self.get_available_tools()
        
        if method not in tools:
            available = list(tools.keys())
            raise ValueError(f"Tool '{method}' not found. Available tools: {available}")
        
        try:
            logger.debug(f"Invoking tool: {method} with params: {params}")
            result = await tools[method](**params)
            logger.debug(f"Tool {method} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Tool {method} failed: {e}")
            raise


class TransportError(Exception):
    """Base exception for transport-related errors."""
    
    def __init__(self, message: str, transport_type: str, details: Optional[Dict[str, Any]] = None):
        """Initialize transport error.
        
        Args:
            message: Error message
            transport_type: Type of transport that failed
            details: Additional error details
        """
        super().__init__(message)
        self.transport_type = transport_type
        self.details = details or {}
        logger.error(f"Transport error in {transport_type}: {message}")