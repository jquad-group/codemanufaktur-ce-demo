### PostgreSQL MCP Server Implementation Guide

This guide provides implementation patterns and standards for building MCP (Model Context Protocol) server for PostgreSQL compatible databases. For WHAT to build, see the PRP (Product Requirement Prompt) documents.

## Core Principles

**IMPORTANT: You MUST follow these principles in all code changes and PRP generations:**

### KISS (Keep It Simple, Stupid)

- Simplicity should be a key goal in design
- Choose straightforward solutions over complex ones whenever possible
- Simple solutions are easier to understand, maintain, and debug

### YAGNI (You Aren't Gonna Need It)

- Avoid building functionality on speculation
- Implement features only when they are needed, not when you anticipate they might be useful in the future

### Open/Closed Principle

- Software entities should be open for extension but closed for modification
- Design systems so that new functionality can be added with minimal changes to existing code

### 🧱 Code Structure & Modularity
- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- **Organize code into clearly separated modules**, grouped by feature or responsibility.
  For agents this looks like:
    - `agent.py` - Main agent definition and execution logic 
    - `tools.py` - Tool functions used by the agent 
    - `prompts.py` - System prompts
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use python_dotenv and load_env()** for environment variables.

### 🧪 Testing & Reliability
- **Always create Pytest unit tests for new features** (functions, classes, routes, etc).
- **After updating any logic**, check whether existing unit tests need to be updated. If so, do it.
- **Tests should live in a `/tests` folder** mirroring the main app structure.
  - Include at least:
    - 1 test for expected use
    - 1 edge case
    - 1 failure case

## Package Management & Tooling

**IMPORTANT: This project uses uv for package management .**

### Essential uv Commands

```bash
# Install dependencies from pyproject.toml
uv sync

# Add a dependency
uv add package-name

# Add a development dependency
uv add --dev package-name

# Remove a package
uv remove package-name

# Update dependencies
uv lock --upgrade && uv sync

# Run scripts/commands with uv
uv run python -m module_name
uv run pytest
uv run ruff check
```

### 📎 Style & Conventions
- **Use Python** as the primary language.
- **Follow PEP8**, use type hints, and format with `black`.
- **Use `pydantic` for data validation**.
- Use `FastAPI` for APIs and `SQLAlchemy` or `SQLModel` for ORM if applicable.
- Write **docstrings for every function** using the Google style:
  ```python
  def example():
      """
      Brief summary.

      Args:
          param1 (type): Description.

      Returns:
          type: Description.
      """
  ```

## Project Architecture

**IMPORTANT: This is a local Python MCP server for PostgreSQL database access demonstration.**

### Current Project Structure

```
/
├── src/                          # Python source code
│   ├── mcp_server.py             # Main MCP server 
│   ├── database.py              # PostgreSQL connection & utilities
│   └── __init__.py              # Package initialization
├── PRPs/                        # Product Requirement Prompts
│   ├── README.md
│   └── templates/
│       └── prp_base.md
├── pyproject.toml              # Python dependencies
├── .env                        # Local configuration variables
└── CLAUDE.md                   # This implementation guide
```

### Key File Purposes (ALWAYS ADD NEW FILES HERE)

**Main Implementation Files:**

- `src/mcp_server.py` - Main MCP server implementation for Supabase
- `src/database.py` - Supabase client management and query helpers

**Configuration Files:**

- `.env` - Local environment variables (SUPABASE_URL, SUPABASE_ANON_KEY, etc.)
- `pyproject.toml` - Python dependencies and project metadata

### Supabase Environment Setup

**Required Environment Variables (.env file):**

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here

# Optional: For authenticated operations
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

**Getting Your Supabase Credentials:**

1. Create a project at [supabase.com](https://supabase.com)
2. Go to Settings → API 
3. Copy your Project URL and anon (public) key
4. For admin operations, copy the service_role key (keep this secure!)

### Environment Variables Implementation

**Code Implementation for Environment Variables:**

```python
# In src/mcp_server.py
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

# Validate required environment variables
required_env_vars = ["SUPABASE_URL", "SUPABASE_ANON_KEY"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]

if missing_vars:
    raise ValueError(f"Missing required environment variables: {missing_vars}")

# Initialize Supabase client with environment variables
supabase: Client = create_client(
    supabase_url=os.getenv("SUPABASE_URL"),
    supabase_key=os.getenv("SUPABASE_ANON_KEY")
)

# Optional: Initialize with service role for admin operations
def get_admin_client() -> Client:
    """Get Supabase client with service role for admin operations."""
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not service_key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY required for admin operations")
    
    return create_client(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=service_key
    )

# Optional: Environment-based configuration
def get_config() -> dict:
    """Get configuration from environment variables."""
    return {
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "server_name": os.getenv("MCP_SERVER_NAME", "supabase-mcp"),
        "max_query_limit": int(os.getenv("MCP_MAX_QUERY_LIMIT", "1000")),
        "enable_debug": os.getenv("DEBUG", "false").lower() == "true"
    }
```

## MCP Development Context

**IMPORTANT: This project builds a local MCP server for Supabase Database using Python 3.13.**

- Use `FastMCP` class instead of custom server classes
- Use `@mcp.tool()` decorators for tool registration 
- Return simple strings/objects instead of `TextContent` lists
- Use `uv run mcp dev` and `uv run mcp install` for testing
- Simplified Claude Desktop integration
- **Supabase client for enhanced database operations with built-in auth, real-time, and storage**

### Supabase-Specific Features

**This implementation leverages Supabase's enhanced capabilities:**

- **Row Level Security (RLS)** - Automatic data access control based on user context
- **Real-time subscriptions** - Live data updates via WebSocket connections
- **Authentication** - Built-in user management and JWT token handling
- **Storage** - File upload and management capabilities
- **Edge Functions** - Server-side functions for complex operations
- **PostgREST API** - Automatic REST API generation from database schema

### MCP Technology Stack

**Core Technologies:**

- **mcp** - Official MCP Python SDK for building servers (v1.2.0+)
- **asyncio** - Python async/await for handling MCP requests
- **supabase** - Supabase Python client for database, auth, storage, and real-time
- **python-dotenv** - Environment variable management
- **pydantic** - Data validation and type hints

**Local Development:**

- **Python 3.13** - Latest Python runtime with enhanced performance
- **PostgreSQL** - Local or remote PostgreSQL database instance
- **uv** - Fast Python package and dependency manager

### MCP Server Architecture

This project implements a local Python MCP server using FastMCP:

**Database MCP Server (`src/mcp_server.py`):**

```python
import asyncio
from mcp.server.fastmcp import FastMCP
from typing import Any, Optional, Dict, List
from supabase import create_client, Client
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Create FastMCP server
mcp = FastMCP("supabase-mcp")

# Initialize Supabase client
supabase: Client = create_client(
    supabase_url=os.getenv("SUPABASE_URL"),
    supabase_key=os.getenv("SUPABASE_ANON_KEY")
)

@mcp.tool()
async def list_tables() -> str:
    """Show available tables in the database."""
    # Implementation here
    pass

@mcp.tool() 
async def query_table(table_name: str, limit: Optional[int] = None, filters: Optional[Dict[str, Any]] = None) -> str:
    """Query a specific table with optional filters."""
    # Implementation here
    pass
        
@mcp.tool()
async def describe_table(table_name: str) -> str:
    """Get table schema and information."""
    # Implementation here
    pass

@mcp.tool()
async def insert_record(table_name: str, data: Dict[str, Any]) -> str:
    """Insert a new record into a table."""
    # Implementation here
    pass

if __name__ == "__main__":
    mcp.run()
```

### MCP Development Commands

**Local Development & Testing:**

```bash
# Install dependencies
uv add "mcp[cli]" supabase python-dotenv pydantic

# Start the MCP server
uv run python src/mcp_server.py

# Test with MCP Inspector
uv run mcp dev src/mcp_server.py

# Install in Claude Desktop
uv run mcp install src/mcp_server.py --name "Supabase Database"
```

### Claude Desktop Integration

**For Local Development:**

```json
{
  "mcpServers": {
    "supabase-database": {
      "command": "uv",
      "args": [
        "--directory", 
        "/absolute/path/to/your/project",
        "run",
        "python",
        "src/mcp_server.py"
      ],
      "env": {
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_ANON_KEY": "your-anon-key-here"
      }
    }
  }
}
```

### MCP Key Concepts for This Project

- **Tools**: Database operations (list_tables, query_database, describe_table)
- **Transport**: Standard MCP stdio protocol for local development
- **Security**: SQL injection protection, query validation, error handling
- **Async Operations**: Python asyncio for non-blocking database operations

## Database Integration & Security

**CRITICAL: This project provides secure PostgreSQL database access through MCP tools with proper validation.**

### Database Architecture

**Connection Management (`src/database.py`):**

```python
import os
from typing import Any, Dict, List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseManager:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.client: Optional[Client] = None
    
    def initialize(self):
        """Initialize Supabase client"""
        self.client = create_client(self.supabase_url, self.supabase_key)
    
    def get_client(self) -> Client:
        """Get Supabase client"""
        if not self.client:
            self.initialize()
        return self.client
    
    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute raw SQL query (for complex operations)"""
        client = self.get_client()
        try:
            result = client.rpc('execute_sql', {'query': query}).execute()
            return result.data if result.data else []
        except Exception as e:
            raise Exception(f"Query execution failed: {str(e)}")
    
    def get_table(self, table_name: str):
        """Get table interface for operations"""
        client = self.get_client()
        return client.table(table_name)
```

### Security Implementation

**Supabase Security with Row Level Security (RLS):**

```python
import re
from typing import Dict, List, Any

def validate_table_name(table_name: str) -> Dict[str, Any]:
    """Validate table name for security"""
    # Only allow alphanumeric characters and underscores
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        return {
            "is_valid": False, 
            "error": "Invalid table name format"
        }
    
    # Prevent access to system tables
    system_tables = [
        "pg_", "information_schema", "auth.", "storage.", 
        "realtime.", "extensions.", "vault."
    ]
    
    if any(table_name.startswith(prefix) for prefix in system_tables):
        return {
            "is_valid": False, 
            "error": "Access to system tables not allowed"
        }
    
    return {"is_valid": True}

def validate_column_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Validate filter parameters for security"""
    if not filters:
        return {"is_valid": True}
    
    # Check for SQL injection in filter values
    dangerous_patterns = [
        r';\s*drop\s+',
        r';\s*delete\s+',
        r';\s*update\s+',
        r'--.*',
        r'/\*.*\*/',
        r'\bor\b.*\b1\s*=\s*1\b',
        r'\bunion\b.*\bselect\b'
    ]
    
    for key, value in filters.items():
        if isinstance(value, str):
            for pattern in dangerous_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    return {
                        "is_valid": False, 
                        "error": f"Potentially dangerous pattern in filter: {key}"
                    }
    
    return {"is_valid": True}

def is_safe_operation(operation: str, allowed_operations: List[str]) -> bool:
    """Check if operation is in allowed list"""
    return operation.lower() in [op.lower() for op in allowed_operations]
```

### MCP Tools Implementation

**Available Supabase Tools:**

1. **`list_tables`** - Schema discovery and table listing
2. **`query_table`** - Query tables with filters and pagination
3. **`describe_table`** - Get detailed table schema information
4. **`insert_record`** - Insert new records with validation
5. **`update_record`** - Update records with filtering
6. **`delete_record`** - Delete records (with RLS protection)
7. **`get_table_stats`** - Get table statistics and row counts
8. **`manage_rls`** - View Row Level Security policies (admin only)

**Tool Implementation Pattern:**

```python
from mcp.server.fastmcp import FastMCP
import json
import os
from typing import Optional, Dict, Any, List
from supabase import create_client, Client

# Create Supabase manager instance
supabase_manager = SupabaseManager(
    os.getenv("SUPABASE_URL"), 
    os.getenv("SUPABASE_ANON_KEY")
)

# Create FastMCP server
mcp = FastMCP("supabase-mcp")

@mcp.tool()
async def query_table(table_name: str, limit: Optional[int] = None, filters: Optional[Dict[str, Any]] = None) -> str:
    """Query a specific table with optional filters.
    
    Args:
        table_name: Name of the table to query
        limit: Optional limit on number of results (default: 100, max: 1000)
        filters: Optional filters as key-value pairs (e.g., {"status": "active", "age": 25})
    """
    try:
        # Validate table name
        table_validation = validate_table_name(table_name)
        if not table_validation["is_valid"]:
            return f"Invalid table name: {table_validation['error']}"
        
        # Validate filters
        filter_validation = validate_column_filters(filters or {})
        if not filter_validation["is_valid"]:
            return f"Invalid filters: {filter_validation['error']}"
        
        # Set reasonable limits
        if limit is None:
            limit = 100
        elif limit > 1000:
            limit = 1000
        
        # Query the table
        client = supabase_manager.get_client()
        query = client.table(table_name).select("*")
        
        # Apply filters if provided
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        
        # Apply limit
        query = query.limit(limit)
        
        # Execute query
        result = query.execute()
        
        if not result.data:
            return f"No data found in table '{table_name}' with the given criteria."
        
        return f"**Query Results from '{table_name}':**\n```json\n{json.dumps(result.data, indent=2, default=str)}\n```"
                
    except Exception as error:
        return f"Database error: {str(error)}"

@mcp.tool()
async def list_tables() -> str:
    """List all accessible tables in the database."""
    try:
        # Use Supabase introspection
        client = supabase_manager.get_client()
        
        # Query information_schema to get table list
        result = client.rpc('get_schema_tables').execute()
        
        if not result.data:
            return "No accessible tables found."
        
        return f"**Available Tables:**\n```json\n{json.dumps(result.data, indent=2)}\n```"
        
    except Exception as error:
        return f"Error listing tables: {str(error)}"

@mcp.tool()
async def describe_table(table_name: str) -> str:
    """Get detailed schema information for a specific table.
    
    Args:
        table_name: Name of the table to describe
    """
    try:
        # Validate table name
        validation = validate_table_name(table_name)
        if not validation["is_valid"]:
            return f"Invalid table name: {validation['error']}"
        
        # Get table schema using Supabase
        client = supabase_manager.get_client()
        result = client.rpc('describe_table', {'table_name': table_name}).execute()
        
        if not result.data:
            return f"Table '{table_name}' not found or not accessible."
        
        return f"**Schema for table '{table_name}':**\n```json\n{json.dumps(result.data, indent=2, default=str)}\n```"
        
    except Exception as error:
        return f"Error describing table: {str(error)}"

@mcp.tool()
async def insert_record(table_name: str, data: Dict[str, Any]) -> str:
    """Insert a new record into a table.
    
    Args:
        table_name: Name of the table to insert into
        data: Record data as key-value pairs
    """
    try:
        # Validate table name
        validation = validate_table_name(table_name)
        if not validation["is_valid"]:
            return f"Invalid table name: {validation['error']}"
        
        if not data:
            return "No data provided for insertion."
        
        # Insert record using Supabase
        client = supabase_manager.get_client()
        result = client.table(table_name).insert(data).execute()
        
        if result.data:
            return f"**Record inserted successfully:**\n```json\n{json.dumps(result.data, indent=2, default=str)}\n```"
        else:
            return "Record insertion completed (no data returned)."
        
    except Exception as error:
        return f"Error inserting record: {str(error)}"

@mcp.tool()
async def update_record(table_name: str, filters: Dict[str, Any], updates: Dict[str, Any]) -> str:
    """Update records in a table based on filters.
    
    Args:
        table_name: Name of the table to update
        filters: Conditions to identify records to update
        updates: New values to set
    """
    try:
        # Validate inputs
        validation = validate_table_name(table_name)
        if not validation["is_valid"]:
            return f"Invalid table name: {validation['error']}"
        
        filter_validation = validate_column_filters(filters)
        if not filter_validation["is_valid"]:
            return f"Invalid filters: {filter_validation['error']}"
        
        update_validation = validate_column_filters(updates)
        if not update_validation["is_valid"]:
            return f"Invalid updates: {update_validation['error']}"
        
        if not filters or not updates:
            return "Both filters and updates must be provided."
        
        # Update records using Supabase
        client = supabase_manager.get_client()
        query = client.table(table_name).update(updates)
        
        # Apply filters
        for key, value in filters.items():
            query = query.eq(key, value)
        
        result = query.execute()
        
        if result.data:
            return f"**Records updated successfully:**\n```json\n{json.dumps(result.data, indent=2, default=str)}\n```"
        else:
            return "Update completed (no records matched the criteria)."
        
    except Exception as error:
        return f"Error updating records: {str(error)}"

if __name__ == "__main__":
    mcp.run()
```



## Local Development & Logging

**This project uses standard Python logging for development and debugging.**

### Logging Configuration

**Basic Python Logging Setup:**

```python
import logging
import sys
from datetime import datetime

# Configure logging for MCP server
def setup_logging(level: str = "INFO") -> logging.Logger:
    """Set up logging for the MCP server"""
    logger = logging.getLogger("postgresql-mcp")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Console handler with timestamps
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

# Usage in MCP server
logger = setup_logging("DEBUG")  # Use DEBUG for development
```

### Development Logging Patterns

**Database Operations:**

```python
import time
from typing import Any

async def execute_database_query(sql: str) -> Any:
    """Execute database query with logging"""
    start_time = time.time()
    logger.info(f"Executing SQL query: {sql[:100]}...")
    
    try:
        async with db_manager.get_connection() as conn:
            results = await conn.fetch(sql)
            duration = (time.time() - start_time) * 1000
            logger.info(f"Query completed successfully in {duration:.2f}ms")
            return results
            
    except Exception as error:
        duration = (time.time() - start_time) * 1000
        logger.error(f"Query failed after {duration:.2f}ms: {str(error)}")
        raise

# Tool execution logging
logger.info(f"MCP tool called: {tool_name}")
logger.debug(f"Tool parameters: {tool_params}")
```

### Error Handling for Local Development

```python
def format_database_error(error: Exception) -> str:
    """Format database errors for user-friendly display"""
    error_msg = str(error)
    
    if "password authentication failed" in error_msg.lower():
        return "Database authentication failed. Check your DATABASE_URL in .env"
    elif "timeout" in error_msg.lower():
        return "Database connection timed out. Check if PostgreSQL is running"
    elif "connection refused" in error_msg.lower():
        return "Cannot connect to database. Verify PostgreSQL is running and DATABASE_URL is correct"
    else:
        return f"Database error: {error_msg}"

# Usage in MCP tools
try:
    result = await execute_query(sql)
except Exception as error:
    logger.error(f"Database operation failed: {error}")
    return [TextContent(
        type="text",
        text=format_database_error(error)
    )]
```

## Python Development Standards

**CRITICAL: All MCP tools MUST follow Python best practices with pydantic validation and proper error handling.**

### Standard Response Format

**ALL tools MUST return properly formatted responses:**

```python
from pydantic import BaseModel, Field
from typing import Optional
import json
import time
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("database-server")

class QueryRequest(BaseModel):
    sql: str = Field(..., min_length=1, description="SQL query to execute")
    limit: Optional[int] = Field(None, ge=1, le=1000, description="Result limit")

@mcp.tool()
async def standardized_tool(name: str, options: Optional[dict] = None) -> str:
    """Tool following standard response format.
    
    Args:
        name: Name to process
        options: Optional processing options
    """
    start_time = time.time()
    
    try:
        # Validate inputs
        if not name or not name.strip():
            return "**Error**\n\nName cannot be empty"
        
        # Process the request
        result = await process_name(name, options or {})
        duration = (time.time() - start_time) * 1000
        
        # Return standardized success response
        return f"**Success**\n\nProcessed: {name}\n\n**Result:**\n```json\n{json.dumps(result, indent=2, default=str)}\n```\n\n**Processing time:** {duration:.1f}ms"
        
    except Exception as error:
        logger.error(f"Tool execution failed: {error}")
        return f"**Error**\n\nProcessing failed: {str(error)}"

# For structured output, return dictionaries or Pydantic models
@mcp.tool()
async def get_user_data(user_id: str) -> dict[str, Any]:
    """Get user data with structured output."""
    return {
        "user_id": user_id,
        "name": "Alice Smith",
        "email": "alice@example.com",
        "created_at": "2024-01-01T00:00:00Z"
    }
```

### Input Validation with Pydantic

**ALL tool inputs are automatically validated using type hints:**

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("database-server")

# Option 1: Use type hints for automatic validation (recommended)
@mcp.tool()
async def query_table(table_name: str, limit: Optional[int] = None, filters: Optional[Dict[str, Any]] = None) -> str:
    """Query a Supabase table with optional filters.
    
    Args:
        table_name: Name of the table to query
        limit: Maximum number of results (1-1000)
        filters: Optional filters as key-value pairs
    """
    try:
        # Manual validation for business rules
        table_validation = validate_table_name(table_name)
        if not table_validation["is_valid"]:
            return f"Error: {table_validation['error']}"
        
        if limit is not None and (limit < 1 or limit > 1000):
            return "Error: Limit must be between 1 and 1000"
        
        filter_validation = validate_column_filters(filters or {})
        if not filter_validation["is_valid"]:
            return f"Error: {filter_validation['error']}"
        
        # Execute validated query
        client = supabase_manager.get_client()
        query = client.table(table_name).select("*")
        
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        
        if limit:
            query = query.limit(limit)
                
        result = query.execute()
        
        return f"**Query Results:**\n```json\n{json.dumps(result.data, indent=2, default=str)}\n```"
            
    except Exception as e:
        return f"Database error: {str(e)}"

# Option 2: Use Pydantic models for complex validation
class TableQueryRequest(BaseModel):
    table_name: str = Field(..., min_length=1, description="Table name to query")
    limit: Optional[int] = Field(None, ge=1, le=1000, description="Maximum number of results")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters as key-value pairs")
    
    @field_validator('table_name')
    @classmethod
    def validate_table_name(cls, v: str) -> str:
        """Validate table name format"""
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError("Invalid table name format")
        return v.strip()

class RecordInsertRequest(BaseModel):
    table_name: str = Field(..., min_length=1, description="Table name for insertion")
    data: Dict[str, Any] = Field(..., description="Record data to insert")
    
    @field_validator('table_name')
    @classmethod
    def validate_table_name(cls, v: str) -> str:
        """Validate table name format"""
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError("Invalid table name format")
        return v.strip()

@mcp.tool()
async def advanced_query(request: TableQueryRequest) -> str:
    """Execute a validated table query using Pydantic model."""
    try:
        # request is automatically validated by FastMCP
        client = supabase_manager.get_client()
        query = client.table(request.table_name).select("*")
        
        if request.filters:
            for key, value in request.filters.items():
                query = query.eq(key, value)
        
        if request.limit:
            query = query.limit(request.limit)
                
        result = query.execute()
        
        return f"**Query Results:**\n```json\n{json.dumps(result.data, indent=2, default=str)}\n```"
            
    except Exception as e:
        return f"Database error: {str(e)}"

@mcp.tool()
async def validated_insert(request: RecordInsertRequest) -> str:
    """Insert a record using validated Pydantic model."""
    try:
        client = supabase_manager.get_client()
        result = client.table(request.table_name).insert(request.data).execute()
        
        if result.data:
            return f"**Record inserted:**\n```json\n{json.dumps(result.data, indent=2, default=str)}\n```"
        else:
            return "Record insertion completed."
            
    except Exception as e:
        return f"Database error: {str(e)}"
```

### Error Handling Patterns

**Standardized error responses:**

```python
from typing import Dict, Any, Optional
import json

def create_error_response(message: str, details: Optional[Dict[str, Any]] = None) -> str:
    """Create standardized error response"""
    error_text = f"**Error**\n\n{message}"
    
    if details:
        error_text += f"\n\n**Details:**\n```json\n{json.dumps(details, indent=2, default=str)}\n```"
    
    return error_text

def create_success_response(message: str, data: Any = None) -> str:
    """Create standardized success response"""
    success_text = f"**Success**\n\n{message}"
    
    if data is not None:
        success_text += f"\n\n**Data:**\n```json\n{json.dumps(data, indent=2, default=str)}\n```"
    
    return success_text

# Validation error
if not is_read_only_query(sql):
    return create_error_response(
        "Write operations not allowed with this tool",
        {
            "operation": "write", 
            "allowed_operations": ["select", "show", "describe", "explain"]
        }
    )

# Database operation with error handling
try:
    result = await execute_query(sql)
    return create_success_response("Query executed successfully", result)
except Exception as error:
    return create_error_response(
        "Database operation failed",
        {"error": format_database_error(error)}
    )
```

### Type Safety Rules

**MANDATORY Python patterns:**

1. **Strict Types**: All parameters and return types explicitly typed with Python type hints
2. **Pydantic Validation**: All inputs validated with Pydantic schemas
3. **Error Handling**: All async operations wrapped in try/except blocks
4. **User Context**: Function parameters typed with Supabase user information
5. **Environment**: Supabase client types and environment variables properly typed
6. **Async/Await**: Consistent use of async/await for I/O operations
7. **Logging**: Comprehensive logging for debugging and monitoring

## Code Style Preferences

### Python Style

- Use explicit type annotations for all function parameters and return types
- Use docstrings for all exported functions and classes following Google style
- Prefer async/await for all asynchronous operations
- **MANDATORY**: Use Pydantic schemas for all input validation
- **MANDATORY**: Use proper error handling with try/except blocks
- Keep functions small and focused (single responsibility principle)
- Follow PEP 8 style guidelines and use type hints consistently

### File Organization

- Each MCP server should be self-contained in a single Python file
- Import statements organized: standard library, third-party packages, local imports
- Use relative imports within the src/ directory
- **Import Pydantic for validation and proper types for all modules**
- **Import Supabase types and client classes consistently**

### Testing Conventions

- Use MCP Inspector for integration testing: `uv run mcp dev src/mcp_server.py`
- Test with local development server: `uv run python src/mcp_server.py`
- Use descriptive tool names and descriptions
- **Test both authentication and permission scenarios with Supabase RLS**
- **Test input validation with invalid data using Pydantic**
- **Test Supabase connection and error scenarios**

## Important Notes

### What NOT to do

- **NEVER** commit secrets or environment variables to the repository (use .env files)
- **NEVER** build complex solutions when simple ones will work
- **NEVER** skip input validation with Pydantic schemas
- **NEVER** use blocking I/O operations (use async/await)
- **NEVER** bypass Supabase Row Level Security (RLS) policies
- **NEVER** use raw SQL without proper validation

### What TO do

- **ALWAYS** use Python strict typing and proper type annotations
- **ALWAYS** validate inputs with Pydantic schemas
- **ALWAYS** follow the core principles (KISS, YAGNI, etc.)
- **ALWAYS** use uv CLI for all development and package management
- **ALWAYS** use async/await for Supabase operations
- **ALWAYS** leverage Supabase RLS for security
- **ALWAYS** use Supabase client methods instead of raw SQL when possible

## Local Development Workflow

```bash
# Before committing, always run:
uv run ruff check              # Lint Python code
uv run python -m py_compile src/*.py  # Check syntax

# Test the MCP server with inspector
uv run mcp dev src/mcp_server.py

# Install in Claude Desktop for testing
uv run mcp install src/mcp_server.py --name "Supabase Database"

# Commit with descriptive messages
git add .
git commit -m "feat: add new MCP tool for table introspection"
```

## Quick Reference

### Adding a New MCP Tool

1. Add `@mcp.tool()` decorated function to your FastMCP server (`src/mcp_server.py`)
2. Use type hints for automatic input validation
3. Implement tool handler with proper error handling
4. Test with `uv run mcp dev src/mcp_server.py`
5. Install in Claude Desktop with `uv run mcp install src/mcp_server.py`

### 📚 Documentation & Explainability
- **Update `README.md`** when new features are added, dependencies change, or setup steps are modified.
- **Comment non-obvious code** and ensure everything is understandable to a mid-level developer.
- When writing complex logic, **add an inline `# Reason:` comment** explaining the why, not just the what.

### 🧠 AI Behavior Rules
- **Never assume missing context. Ask questions if uncertain.**
- **Never hallucinate libraries or functions** – only use known, verified Python packages.
- **Always confirm file paths and module names** exist before referencing them in code or tests.
- **Never delete or overwrite existing code** unless explicitly instructed to or if part of a task from `TASK.md`.