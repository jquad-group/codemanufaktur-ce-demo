"""Supabase MCP Server.

A Model Context Protocol server for secure Supabase database integration.
Provides tools for querying, inserting, updating, and introspecting database structures
with built-in Row Level Security and comprehensive input validation.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

try:
    # Try relative import first (for package usage)
    from .database import (
        SupabaseManager,
        TableQueryRequest,
        RecordInsertRequest,
        RecordUpdateRequest,
        validate_table_name,
        validate_column_filters,
    )
except ImportError:
    # Fallback to absolute import (for direct execution)
    from src.database import (
        SupabaseManager,
        TableQueryRequest,
        RecordInsertRequest,
        RecordUpdateRequest,
        validate_table_name,
        validate_column_filters,
    )

# CRITICAL: Configure logging to stderr only (never stdout - corrupts MCP JSON-RPC)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("supabase-mcp")

# Load environment variables from .env file
load_dotenv()

def validate_environment() -> None:
    """Validate required environment variables."""
    required_vars = ["SUPABASE_URL", "SUPABASE_ANON_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        error_msg = f"Missing required environment variables: {missing_vars}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info("Environment variables validated successfully")

def get_config() -> Dict[str, Any]:
    """Get configuration from environment variables."""
    return {
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "server_name": os.getenv("MCP_SERVER_NAME", "supabase-mcp"),
        "max_query_limit": int(os.getenv("MCP_MAX_QUERY_LIMIT", "1000")),
        "debug": os.getenv("DEBUG", "false").lower() == "true",
    }

# Validate environment before proceeding
validate_environment()
config = get_config()

# Update logging level if specified
if config["log_level"]:
    logger.setLevel(getattr(logging, config["log_level"].upper()))

# Initialize FastMCP server
mcp = FastMCP(config["server_name"])

# Initialize Supabase manager with environment credentials
try:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
    
    supabase_manager = SupabaseManager(
        supabase_url=supabase_url,
        supabase_key=supabase_key
    )
    logger.info("Supabase manager initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase manager: {e}")
    raise

def create_error_response(message: str, details: Optional[Dict[str, Any]] = None) -> str:
    """Create standardized error response."""
    error_text = f"**Error**\n\n{message}"
    
    if details:
        error_text += f"\n\n**Details:**\n```json\n{json.dumps(details, indent=2, default=str)}\n```"
    
    return error_text

def create_success_response(message: str, data: Any = None) -> str:
    """Create standardized success response."""
    success_text = f"**Success**\n\n{message}"
    
    if data is not None:
        success_text += f"\n\n**Data:**\n```json\n{json.dumps(data, indent=2, default=str)}\n```"
    
    return success_text


@mcp.tool()
async def list_tables() -> str:
    """List all accessible tables in the Supabase database.
    
    Returns:
        Formatted string with list of available tables and their basic information
    """
    try:
        logger.info("Executing list_tables tool")
        client = supabase_manager.get_client()
        
        # Query information_schema to get user tables (not system tables)
        # Note: Supabase uses PostgreSQL, so we can use standard information_schema
        query = """
        SELECT 
            table_name,
            table_type,
            table_schema
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
        
        # Use a raw SQL query for information_schema access
        result = client.rpc('execute_sql', {'query': query}).execute()
        
        if not result.data:
            return "**No accessible tables found**\n\nThe database appears to be empty or you may not have permission to view tables."
        
        # Format the table information
        tables_info = []
        for table in result.data:
            tables_info.append({
                "name": table.get("table_name"),
                "type": table.get("table_type", "TABLE"), 
                "schema": table.get("table_schema", "public")
            })
        
        return create_success_response(
            f"Found {len(tables_info)} accessible table(s)",
            tables_info
        )
        
    except Exception as e:
        logger.error(f"list_tables failed: {e}")
        # Try fallback method using Supabase client directly
        try:
            logger.info("Attempting fallback table listing method")
            client = supabase_manager.get_client()
            
            # Alternative approach: try to access a common table to test connection
            # This is a simplified approach when information_schema access is limited
            connection_test = supabase_manager.test_connection()
            
            if connection_test["status"] == "connected":
                return create_error_response(
                    "Unable to list tables directly",
                    {
                        "reason": str(e),
                        "connection_status": "connected",
                        "suggestion": "Tables may exist but require specific permissions to list. Try accessing tables directly by name using query_table tool."
                    }
                )
            else:
                return create_error_response(
                    "Database connection failed",
                    {"error": str(e), "connection_test": connection_test}
                )
                
        except Exception as fallback_error:
            logger.error(f"Fallback method also failed: {fallback_error}")
            return create_error_response(
                "Unable to list tables", 
                {"error": str(e), "fallback_error": str(fallback_error)}
            )


@mcp.tool()
async def query_table(table_name: str, limit: Optional[int] = None, filters: Optional[Dict[str, Any]] = None) -> str:
    """Query a Supabase table with optional filters and pagination.
    
    Args:
        table_name: Name of the table to query
        limit: Maximum number of results (default: 100, max: 1000)
        filters: Optional filters as key-value pairs (e.g., {"status": "active", "age": 25})
    
    Returns:
        Formatted string with query results or error message
    """
    try:
        logger.info(f"Executing query_table tool for table: {table_name}")
        
        # Create and validate request using Pydantic model
        try:
            request = TableQueryRequest(
                table_name=table_name,
                limit=limit,
                filters=filters
            )
        except ValidationError as e:
            logger.error(f"Validation error in query_table: {e}")
            return create_error_response(
                "Input validation failed", 
                {"validation_errors": [str(err) for err in e.errors()]}
            )
        
        # Additional security validation for filters
        filter_validation = validate_column_filters(request.filters or {})
        if not filter_validation["is_valid"]:
            return create_error_response(
                "Filter validation failed",
                {"error": filter_validation["error"]}
            )
        
        # Set reasonable default and maximum limits
        query_limit = request.limit or 100
        query_limit = min(query_limit, config["max_query_limit"])
        
        # Execute query using SupabaseManager
        result = supabase_manager.execute_query(
            table_name=request.table_name,
            operation="select",
            filters=request.filters,
            limit=query_limit,
            columns="*"
        )
        
        if not result.data:
            return f"**No data found**\n\nTable '{request.table_name}' exists but no records match the given criteria.\n\n**Query Details:**\n- Limit: {query_limit}\n- Filters: {json.dumps(request.filters or {}, indent=2)}"
        
        # Format and return results
        record_count = len(result.data)
        response_message = f"Found {record_count} record(s) in table '{request.table_name}'"
        
        if request.filters:
            response_message += " (filtered)"
        
        return create_success_response(response_message, {
            "table": request.table_name,
            "record_count": record_count,
            "limit_applied": query_limit,
            "filters_applied": request.filters or {},
            "records": result.data
        })
        
    except ValueError as e:
        logger.error(f"Validation error in query_table: {e}")
        return create_error_response(
            "Query validation failed",
            {"error": str(e)}
        )
    except RuntimeError as e:
        logger.error(f"Database error in query_table: {e}")
        return create_error_response(
            "Database query failed",
            {"error": str(e), "table": table_name}
        )
    except Exception as e:
        logger.error(f"Unexpected error in query_table: {e}")
        return create_error_response(
            "Query execution failed",
            {"error": str(e), "table": table_name}
        )


@mcp.tool()
async def describe_table(table_name: str) -> str:
    """Get detailed schema information for a specific table.
    
    Args:
        table_name: Name of the table to describe
    
    Returns:
        Formatted string with table schema details including columns, types, and constraints
    """
    try:
        logger.info(f"Executing describe_table tool for table: {table_name}")
        
        # Validate table name
        validation = validate_table_name(table_name)
        if not validation["is_valid"]:
            return create_error_response(
                "Invalid table name", 
                {"error": validation["error"]}
            )
        
        client = supabase_manager.get_client()
        
        # Query information_schema for detailed column information
        column_query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length,
            numeric_precision,
            numeric_scale,
            ordinal_position
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = %s
        ORDER BY ordinal_position
        """
        
        # Query for constraints (primary keys, foreign keys, etc.)
        constraint_query = """
        SELECT 
            tc.constraint_type,
            tc.constraint_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints tc
        LEFT JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
        LEFT JOIN information_schema.constraint_column_usage ccu 
            ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_schema = 'public' 
        AND tc.table_name = %s
        """
        
        try:
            # Get column information
            columns_result = client.rpc('execute_sql', {
                'query': column_query,
                'params': [table_name]
            }).execute()
            
            # Get constraint information  
            constraints_result = client.rpc('execute_sql', {
                'query': constraint_query,
                'params': [table_name]
            }).execute()
            
        except Exception as e:
            logger.warning(f"RPC method failed, trying alternative approach: {e}")
            # Fallback: Try to query the table directly to at least get column info
            try:
                sample_result = client.table(table_name).select("*").limit(1).execute()
                
                if sample_result.data and len(sample_result.data) > 0:
                    columns_info = []
                    sample_record = sample_result.data[0]
                    for idx, (col_name, value) in enumerate(sample_record.items(), 1):
                        # Infer type from sample data
                        inferred_type = type(value).__name__ if value is not None else "unknown"
                        columns_info.append({
                            "column_name": col_name,
                            "data_type": inferred_type,
                            "is_nullable": "YES" if value is None else "UNKNOWN",
                            "ordinal_position": idx
                        })
                    
                    return create_success_response(
                        f"Table '{table_name}' schema (inferred from sample data)",
                        {
                            "table_name": table_name,
                            "columns": columns_info,
                            "note": "Schema information inferred from sample data. Full schema details may not be available due to permissions."
                        }
                    )
                else:
                    return create_error_response(
                        f"Table '{table_name}' appears to be empty or inaccessible",
                        {"suggestion": "Check if the table exists and you have appropriate permissions"}
                    )
                    
            except Exception as fallback_error:
                logger.error(f"Fallback method also failed: {fallback_error}")
                return create_error_response(
                    f"Unable to describe table '{table_name}'",
                    {
                        "primary_error": str(e),
                        "fallback_error": str(fallback_error),
                        "suggestion": "Check if the table exists and you have appropriate permissions"
                    }
                )
        
        # Process column information
        if not columns_result.data:
            return create_error_response(
                f"Table '{table_name}' not found",
                {"suggestion": "Use list_tables tool to see available tables"}
            )
        
        columns_info = []
        for col in columns_result.data:
            column_info = {
                "name": col.get("column_name"),
                "type": col.get("data_type"),
                "nullable": col.get("is_nullable", "UNKNOWN") == "YES",
                "default": col.get("column_default"),
                "position": col.get("ordinal_position", 0)
            }
            
            # Add length/precision info if available
            if col.get("character_maximum_length"):
                column_info["max_length"] = col.get("character_maximum_length")
            
            if col.get("numeric_precision"):
                column_info["precision"] = col.get("numeric_precision")
                if col.get("numeric_scale"):
                    column_info["scale"] = col.get("numeric_scale")
            
            columns_info.append(column_info)
        
        # Process constraint information
        constraints_info = []
        if constraints_result.data:
            for constraint in constraints_result.data:
                constraint_info = {
                    "type": constraint.get("constraint_type"),
                    "name": constraint.get("constraint_name"),
                    "column": constraint.get("column_name")
                }
                
                # Add foreign key information if available
                if constraint.get("foreign_table_name"):
                    constraint_info["references"] = {
                        "table": constraint.get("foreign_table_name"),
                        "column": constraint.get("foreign_column_name")
                    }
                
                constraints_info.append(constraint_info)
        
        # Build response
        schema_data = {
            "table_name": table_name,
            "column_count": len(columns_info),
            "columns": sorted(columns_info, key=lambda x: x["position"]),
            "constraints": constraints_info
        }
        
        return create_success_response(
            f"Schema for table '{table_name}' ({len(columns_info)} columns)",
            schema_data
        )
        
    except ValueError as e:
        logger.error(f"Validation error in describe_table: {e}")
        return create_error_response(
            "Table name validation failed",
            {"error": str(e)}
        )
    except Exception as e:
        logger.error(f"Unexpected error in describe_table: {e}")
        return create_error_response(
            f"Failed to describe table '{table_name}'",
            {"error": str(e)}
        )


@mcp.tool()
async def insert_record(table_name: str, data: Dict[str, Any]) -> str:
    """Insert a new record into a Supabase table with validation.
    
    Args:
        table_name: Name of the table to insert into
        data: Record data as key-value pairs (e.g., {"name": "John", "email": "john@example.com"})
    
    Returns:
        Formatted string with insertion result or error message
    """
    try:
        logger.info(f"Executing insert_record tool for table: {table_name}")
        
        # Create and validate request using Pydantic model
        try:
            request = RecordInsertRequest(
                table_name=table_name,
                data=data
            )
        except ValidationError as e:
            logger.error(f"Validation error in insert_record: {e}")
            return create_error_response(
                "Input validation failed", 
                {"validation_errors": [str(err) for err in e.errors()]}
            )
        
        # Validate data keys (column names) for security
        if not request.data:
            return create_error_response(
                "No data provided for insertion",
                {"example": {"name": "John Doe", "email": "john@example.com"}}
            )
        
        # Validate column names in data
        column_validation = validate_column_filters(request.data)
        if not column_validation["is_valid"]:
            return create_error_response(
                "Invalid column names in data",
                {"error": column_validation["error"]}
            )
        
        # Check for excessively large data values
        for key, value in request.data.items():
            if isinstance(value, str) and len(value) > 10000:
                return create_error_response(
                    f"Data value too large for column '{key}'",
                    {"max_length": 10000, "actual_length": len(value)}
                )
        
        # Execute insert using SupabaseManager
        result = supabase_manager.execute_query(
            table_name=request.table_name,
            operation="insert",
            data=request.data
        )
        
        if result.data:
            inserted_record = result.data[0] if isinstance(result.data, list) else result.data
            
            return create_success_response(
                f"Record inserted successfully into table '{request.table_name}'",
                {
                    "table": request.table_name,
                    "inserted_data": request.data,
                    "inserted_record": inserted_record,
                    "timestamp": "record created"
                }
            )
        else:
            # Insert succeeded but no data returned (which can happen with some DB configs)
            return create_success_response(
                f"Record inserted successfully into table '{request.table_name}'",
                {
                    "table": request.table_name,
                    "inserted_data": request.data,
                    "note": "Insert completed successfully. Record data not returned by database."
                }
            )
        
    except ValueError as e:
        logger.error(f"Validation error in insert_record: {e}")
        return create_error_response(
            "Data validation failed",
            {"error": str(e)}
        )
    except RuntimeError as e:
        logger.error(f"Database error in insert_record: {e}")
        error_msg = str(e).lower()
        
        # Provide more specific error messages for common issues
        if "duplicate" in error_msg or "unique" in error_msg:
            return create_error_response(
                "Record insertion failed due to duplicate key",
                {
                    "error": str(e),
                    "suggestion": "Check for unique constraints and existing records with the same key values"
                }
            )
        elif "foreign key" in error_msg:
            return create_error_response(
                "Record insertion failed due to foreign key constraint",
                {
                    "error": str(e),
                    "suggestion": "Ensure referenced records exist in related tables"
                }
            )
        elif "not null" in error_msg:
            return create_error_response(
                "Record insertion failed due to missing required fields",
                {
                    "error": str(e),
                    "suggestion": "Check for required (NOT NULL) columns and provide values"
                }
            )
        else:
            return create_error_response(
                "Database insertion failed",
                {"error": str(e), "table": table_name}
            )
    except Exception as e:
        logger.error(f"Unexpected error in insert_record: {e}")
        return create_error_response(
            "Record insertion failed",
            {"error": str(e), "table": table_name}
        )


@mcp.tool()
async def update_record(table_name: str, filters: Dict[str, Any], updates: Dict[str, Any]) -> str:
    """Update records in a Supabase table based on filters with comprehensive validation.
    
    Args:
        table_name: Name of the table to update
        filters: Conditions to identify records to update (e.g., {"id": 123, "status": "active"})
        updates: New values to set (e.g., {"name": "Updated Name", "status": "inactive"})
    
    Returns:
        Formatted string with update result or error message
    """
    try:
        logger.info(f"Executing update_record tool for table: {table_name}")
        
        # Create and validate request using Pydantic model
        try:
            request = RecordUpdateRequest(
                table_name=table_name,
                filters=filters,
                updates=updates
            )
        except ValidationError as e:
            logger.error(f"Validation error in update_record: {e}")
            return create_error_response(
                "Input validation failed", 
                {"validation_errors": [str(err) for err in e.errors()]}
            )
        
        # Validate that filters and updates are provided
        if not request.filters:
            return create_error_response(
                "No filter conditions provided",
                {
                    "error": "Filters are required to prevent accidental mass updates",
                    "example_filters": {"id": 123, "status": "active"}
                }
            )
        
        if not request.updates:
            return create_error_response(
                "No update values provided",
                {
                    "error": "Updates are required to specify what to change",
                    "example_updates": {"name": "New Name", "status": "inactive"}
                }
            )
        
        # Security validation for filters
        filter_validation = validate_column_filters(request.filters)
        if not filter_validation["is_valid"]:
            return create_error_response(
                "Invalid filter conditions",
                {"error": filter_validation["error"]}
            )
        
        # Security validation for updates
        update_validation = validate_column_filters(request.updates)
        if not update_validation["is_valid"]:
            return create_error_response(
                "Invalid update values",
                {"error": update_validation["error"]}
            )
        
        # Check for excessively large update values
        for key, value in request.updates.items():
            if isinstance(value, str) and len(value) > 10000:
                return create_error_response(
                    f"Update value too large for column '{key}'",
                    {"max_length": 10000, "actual_length": len(value)}
                )
        
        # Prevent updating primary key columns (common security practice)
        dangerous_update_columns = ["id", "created_at", "updated_at"]
        for col in dangerous_update_columns:
            if col in request.updates:
                logger.warning(f"Attempt to update protected column: {col}")
                return create_error_response(
                    f"Cannot update protected column '{col}'",
                    {
                        "protected_columns": dangerous_update_columns,
                        "suggestion": "Use different column names or exclude protected columns"
                    }
                )
        
        # Execute update using SupabaseManager
        result = supabase_manager.execute_query(
            table_name=request.table_name,
            operation="update",
            filters=request.filters,
            updates=request.updates
        )
        
        if result.data:
            updated_records = result.data if isinstance(result.data, list) else [result.data]
            record_count = len(updated_records)
            
            return create_success_response(
                f"Successfully updated {record_count} record(s) in table '{request.table_name}'",
                {
                    "table": request.table_name,
                    "updated_count": record_count,
                    "filters_applied": request.filters,
                    "updates_applied": request.updates,
                    "updated_records": updated_records
                }
            )
        else:
            # Update succeeded but no records were affected (no matches found)
            return create_success_response(
                f"Update operation completed for table '{request.table_name}'",
                {
                    "table": request.table_name,
                    "updated_count": 0,
                    "filters_applied": request.filters,
                    "updates_applied": request.updates,
                    "message": "No records matched the filter criteria"
                }
            )
        
    except ValueError as e:
        logger.error(f"Validation error in update_record: {e}")
        return create_error_response(
            "Update validation failed",
            {"error": str(e)}
        )
    except RuntimeError as e:
        logger.error(f"Database error in update_record: {e}")
        error_msg = str(e).lower()
        
        # Provide more specific error messages for common issues
        if "foreign key" in error_msg:
            return create_error_response(
                "Update failed due to foreign key constraint",
                {
                    "error": str(e),
                    "suggestion": "Ensure updated values reference existing records in related tables"
                }
            )
        elif "unique" in error_msg or "duplicate" in error_msg:
            return create_error_response(
                "Update failed due to unique constraint violation",
                {
                    "error": str(e),
                    "suggestion": "Check for unique constraints and ensure updated values don't create duplicates"
                }
            )
        elif "check constraint" in error_msg:
            return create_error_response(
                "Update failed due to check constraint violation",
                {
                    "error": str(e),
                    "suggestion": "Ensure updated values meet the table's validation rules"
                }
            )
        else:
            return create_error_response(
                "Database update failed",
                {"error": str(e), "table": table_name}
            )
    except Exception as e:
        logger.error(f"Unexpected error in update_record: {e}")
        return create_error_response(
            "Record update failed",
            {"error": str(e), "table": table_name}
        )


if __name__ == "__main__":
    logger.info(f"Starting {config['server_name']} MCP server...")
    mcp.run()