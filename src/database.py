"""Database management and validation for Supabase MCP Server.

This module provides secure database access through the SupabaseManager class,
input validation using Pydantic models, and security functions to prevent
SQL injection and unauthorized access.
"""

import re
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator
from supabase import create_client, Client
import logging
import sys

# Configure logging to stderr only (never stdout - corrupts MCP JSON-RPC)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("supabase-mcp.database")


class TableQueryRequest(BaseModel):
    """Request model for table query operations."""
    
    table_name: str = Field(..., min_length=1, description="Table name to query")
    limit: Optional[int] = Field(None, ge=1, le=1000, description="Maximum results (default: 100)")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters as key-value pairs")
    
    @field_validator('table_name')
    @classmethod
    def validate_table_name(cls, v: str) -> str:
        """Validate table name format for security."""
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError("Invalid table name format - only alphanumeric and underscores allowed")
        return v.strip()


class RecordInsertRequest(BaseModel):
    """Request model for record insertion operations."""
    
    table_name: str = Field(..., min_length=1, description="Table name for insertion")
    data: Dict[str, Any] = Field(..., description="Record data to insert")
    
    @field_validator('table_name')
    @classmethod
    def validate_table_name(cls, v: str) -> str:
        """Validate table name format for security."""
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError("Invalid table name format - only alphanumeric and underscores allowed")
        return v.strip()
    
    @field_validator('data')
    @classmethod
    def validate_data_not_empty(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that data is not empty."""
        if not v:
            raise ValueError("Data cannot be empty - at least one field is required")
        return v


class RecordUpdateRequest(BaseModel):
    """Request model for record update operations."""
    
    table_name: str = Field(..., min_length=1, description="Table name to update")
    filters: Dict[str, Any] = Field(..., description="Conditions to identify records")
    updates: Dict[str, Any] = Field(..., description="New values to set")
    
    @field_validator('table_name')
    @classmethod
    def validate_table_name(cls, v: str) -> str:
        """Validate table name format for security."""
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError("Invalid table name format - only alphanumeric and underscores allowed")
        return v.strip()


def validate_table_name(table_name: str) -> Dict[str, Any]:
    """Validate table name for security and format compliance.
    
    Args:
        table_name: The table name to validate
        
    Returns:
        Dict with 'is_valid' boolean and optional 'error' message
    """
    if not table_name or not table_name.strip():
        return {"is_valid": False, "error": "Table name cannot be empty"}
    
    # Only allow alphanumeric characters and underscores
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        return {
            "is_valid": False, 
            "error": "Invalid table name format - only alphanumeric characters and underscores allowed"
        }
    
    # Prevent access to system tables and schemas
    system_prefixes = [
        "pg_", "information_schema", "auth.", "storage.", 
        "realtime.", "extensions.", "vault.", "supabase_"
    ]
    
    table_lower = table_name.lower()
    for prefix in system_prefixes:
        if table_lower.startswith(prefix.lower()):
            return {
                "is_valid": False, 
                "error": f"Access to system tables/schemas not allowed: {prefix}"
            }
    
    return {"is_valid": True}


def validate_column_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Validate filter parameters for SQL injection protection.
    
    Args:
        filters: Dictionary of column filters
        
    Returns:
        Dict with 'is_valid' boolean and optional 'error' message
    """
    if not filters:
        return {"is_valid": True}
    
    # Check for dangerous SQL injection patterns
    dangerous_patterns = [
        r';\s*drop\s+',      # DROP statements
        r';\s*delete\s+',    # DELETE statements  
        r';\s*update\s+',    # UPDATE statements
        r';\s*insert\s+',    # INSERT statements
        r'--.*',             # SQL comments
        r'/\*.*\*/',         # Multi-line comments
        r'\bor\b.*\b1\s*=\s*1\b',  # Classic injection
        r'\bunion\b.*\bselect\b',   # UNION SELECT
        r'\bexec\b',         # EXEC statements
        r'\bsp_\w+',         # Stored procedures
        r'\bxp_\w+',         # Extended procedures
    ]
    
    for key, value in filters.items():
        # Validate column names
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
            return {
                "is_valid": False, 
                "error": f"Invalid column name format: {key}"
            }
        
        # Check filter values for dangerous patterns
        if isinstance(value, str):
            for pattern in dangerous_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    return {
                        "is_valid": False, 
                        "error": f"Potentially dangerous pattern detected in filter: {key}"
                    }
        
        # Check for excessively long values that might indicate an attack
        if isinstance(value, str) and len(value) > 1000:
            return {
                "is_valid": False,
                "error": f"Filter value too long for column: {key}"
            }
    
    return {"is_valid": True}


class SupabaseManager:
    """Manages Supabase client connections and database operations."""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        """Initialize Supabase manager.
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key (anon or service role)
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.client: Optional[Client] = None
        
        # Validate credentials
        self._validate_credentials()
        logger.info("SupabaseManager initialized successfully")
    
    def _validate_credentials(self) -> None:
        """Validate Supabase credentials."""
        if not self.supabase_url or not self.supabase_url.strip():
            raise ValueError("SUPABASE_URL is required")
        
        if not self.supabase_key or not self.supabase_key.strip():
            raise ValueError("SUPABASE_ANON_KEY is required")
        
        if not self.supabase_url.startswith("https://"):
            raise ValueError("SUPABASE_URL must be a valid HTTPS URL")
        
        if ".supabase.co" not in self.supabase_url:
            logger.warning("SUPABASE_URL does not appear to be a valid Supabase URL")
    
    def initialize(self) -> None:
        """Initialize Supabase client connection."""
        try:
            self.client = create_client(self.supabase_url, self.supabase_key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise RuntimeError(f"Supabase client initialization failed: {str(e)}")
    
    def get_client(self) -> Client:
        """Get Supabase client, initializing if needed.
        
        Returns:
            Supabase client instance
            
        Raises:
            RuntimeError: If client initialization fails
        """
        if not self.client:
            self.initialize()
        
        # After initialization, client should not be None
        if not self.client:
            raise RuntimeError("Failed to initialize Supabase client")
        
        return self.client
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Supabase connection health.
        
        Returns:
            Dict with connection status and details
        """
        try:
            client = self.get_client()
            # Simple query to test connection
            # Simple query to test connection - we don't need the result
            client.from_("information_schema.tables").select("count").limit(1).execute()
            logger.info("Connection test successful")
            return {
                "status": "connected",
                "message": "Supabase connection is healthy"
            }
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "status": "error", 
                "message": f"Connection failed: {str(e)}"
            }
    
    def execute_query(self, table_name: str, operation: str, **kwargs) -> Any:
        """Execute database operation with error handling.
        
        Args:
            table_name: Name of the table
            operation: Type of operation (select, insert, update, delete)
            **kwargs: Operation-specific parameters
            
        Returns:
            Query result
            
        Raises:
            ValueError: For invalid parameters
            RuntimeError: For database errors
        """
        # Validate table name
        validation = validate_table_name(table_name)
        if not validation["is_valid"]:
            raise ValueError(validation["error"])
        
        try:
            client = self.get_client()
            table = client.table(table_name)
            
            if operation == "select":
                return self._execute_select(table, **kwargs)
            elif operation == "insert":
                return self._execute_insert(table, **kwargs)
            elif operation == "update":
                return self._execute_update(table, **kwargs)
            elif operation == "delete":
                return self._execute_delete(table, **kwargs)
            else:
                raise ValueError(f"Unsupported operation: {operation}")
                
        except ValueError:
            # Re-raise ValueError as-is (validation errors should not be wrapped)
            raise
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError(f"Database operation failed: {str(e)}")
    
    def _execute_select(self, table, **kwargs) -> Any:
        """Execute SELECT operation."""
        query = table.select(kwargs.get("columns", "*"))
        
        # Apply filters
        filters = kwargs.get("filters", {})
        if filters:
            filter_validation = validate_column_filters(filters)
            if not filter_validation["is_valid"]:
                raise ValueError(filter_validation["error"])
            
            for key, value in filters.items():
                query = query.eq(key, value)
        
        # Apply limit
        limit = kwargs.get("limit", 100)
        if limit and isinstance(limit, int) and limit > 0:
            query = query.limit(min(limit, 1000))  # Cap at 1000
        
        # Apply ordering
        order_by = kwargs.get("order_by")
        if order_by:
            query = query.order(order_by)
        
        return query.execute()
    
    def _execute_insert(self, table, **kwargs) -> Any:
        """Execute INSERT operation."""
        data = kwargs.get("data")
        if not data:
            raise ValueError("Data is required for insert operation")
        
        return table.insert(data).execute()
    
    def _execute_update(self, table, **kwargs) -> Any:
        """Execute UPDATE operation."""
        filters = kwargs.get("filters", {})
        updates = kwargs.get("updates")
        
        if not filters:
            raise ValueError("Filters are required for update operation")
        if not updates:
            raise ValueError("Updates are required for update operation")
        
        # Validate filters
        filter_validation = validate_column_filters(filters)
        if not filter_validation["is_valid"]:
            raise ValueError(filter_validation["error"])
        
        # Validate updates
        update_validation = validate_column_filters(updates)
        if not update_validation["is_valid"]:
            raise ValueError(update_validation["error"])
        
        query = table.update(updates)
        for key, value in filters.items():
            query = query.eq(key, value)
        
        return query.execute()
    
    def _execute_delete(self, table, **kwargs) -> Any:
        """Execute DELETE operation."""
        filters = kwargs.get("filters", {})
        
        if not filters:
            raise ValueError("Filters are required for delete operation")
        
        # Validate filters
        filter_validation = validate_column_filters(filters)
        if not filter_validation["is_valid"]:
            raise ValueError(filter_validation["error"])
        
        query = table.delete()
        for key, value in filters.items():
            query = query.eq(key, value)
        
        return query.execute()