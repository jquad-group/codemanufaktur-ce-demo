name: "Supabase MCP Server Implementation"
description: |

## Purpose
Complete implementation of a Model Context Protocol (MCP) server for Supabase database integration, enabling Claude and other AI assistants to interact securely with Supabase databases through high-level tools with built-in Row Level Security and Pydantic validation.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in GUIDELINES.md

---

## Goal
Build a production-ready MCP server that provides secure, validated access to Supabase databases with tools for querying, inserting, updating, and introspecting database structures. The server must integrate with Claude Desktop and follow all security best practices.

## Why
- **AI Database Integration**: Enable AI assistants to interact with databases through natural language
- **Security First**: Leverage Supabase RLS and Pydantic validation for safe operations
- **Developer Productivity**: Provide high-level tools that abstract database complexity
- **Standardization**: Use MCP protocol for interoperability with various AI clients

## What
A complete MCP server implementation with the following user-visible behavior:

### Core Tools
1. **`query_table`** - Query tables with filters, pagination, and type safety
2. **`insert_record`** - Insert new records with validation
3. **`update_record`** - Update records with filter validation
4. **`describe_table`** - Get table schema and metadata
5. **`list_tables`** - Discover available tables

### Success Criteria
- [ ] All 5 core tools implemented and functional
- [ ] Pydantic validation for all inputs
- [ ] Supabase RLS integration working
- [ ] Claude Desktop integration configured
- [ ] Comprehensive error handling
- [ ] Environment variable management with .env
- [ ] Complete project documentation
- [ ] All validation tests passing

## All Needed Context

### Documentation & References (list all context needed to implement the feature)
```yaml
# MUST READ - Include these in your context window

# Project Documentation
- file: GUIDELINES.md
  why: Technical implementation standards for this project
  critical: Type safety rules, security patterns, code style, FastMCP patterns

- file: THIS_PROJECT.md  
  why: Project overview, gotchas, and setup requirements
  critical: Supabase-specific considerations and fallsticks, environment setup

# MCP Framework Documentation
- url: https://modelcontextprotocol.io/introduction
  why: Core MCP concepts and architecture
  section: Tools, Resources, Transport protocols
  key_insight: MCP standardizes AI-application data connections like "USB-C for AI"
  
- url: https://github.com/modelcontextprotocol/python-sdk
  why: FastMCP patterns and examples
  section: Tool implementation, server setup
  critical: Use FastMCP, not low-level server APIs, leverage type hints for validation
  pattern: "@mcp.tool() decorator with automatic validation"

- url: https://modelcontextprotocol.io/quickstart/server
  why: Server development patterns
  critical: Logging restrictions (never stdout), Claude Desktop integration, development workflow
  gotcha: "Never write to standard output (stdout)" - use stderr logging only

# Supabase Documentation  
- url: https://supabase.com/docs/reference/python/introduction
  why: Python client usage patterns
  section: Query methods, error handling
  patterns: "supabase.table().select().execute()" fluent API
  
- url: https://supabase.com/docs/guides/auth/row-level-security
  why: RLS security implementation
  critical: Must enable RLS policies for security, test with different user contexts
  pattern: "ALTER TABLE profiles ENABLE ROW LEVEL SECURITY"

# Validation Framework
- url: https://docs.pydantic.dev/latest/concepts/validators/
  why: Input validation patterns
  critical: Field validators, custom validation, security filtering
  pattern: "@field_validator with mode='after' for post-processing validation"

```

### Current Codebase Tree
```bash
context-engineering-mcp-db/
├── src/                          # Future Python source code
├── PRPs/                        # Product Requirement Prompts
│   └── templates/
│       └── prp_base.md
├── GUIDELINES.md                # Technical implementation standards
├── THIS_PROJECT.md             # Project overview and gotchas
├── README.md                   # Project documentation
├── main.py                     # Basic placeholder
├── pyproject.toml              # Python dependencies (needs MCP deps)
├── .env                        # Environment variables (to be created)
├── .env.example                # Environment template (to be created)
└── .gitignore                  # Git ignore rules (to be created)
```

### Desired Codebase Tree with Files to be Added
```bash
context-engineering-mcp-db/
├── src/                          
│   ├── __init__.py              # Package initialization
│   ├── mcp_server.py            # Main FastMCP server implementation
│   └── database.py              # Supabase client management and utilities
├── tests/                       # Pytest test suite
│   ├── __init__.py              
│   ├── test_mcp_server.py       # MCP server tool tests
│   └── test_database.py         # Database utility tests
├── PRPs/                        
├── GUIDELINES.md                
├── THIS_PROJECT.md             
├── README.md                    # Complete setup and usage documentation
├── main.py                     
├── pyproject.toml               # Updated with MCP, Supabase, Pydantic deps
├── .env.example                 # Environment template with all variables
├── .env                         # Local environment variables
└── .gitignore                   # Updated to exclude .env and other files
```

### Known Gotchas of our codebase & Library Quirks
```python
# MCP-SPECIFIC GOTCHAS:
# CRITICAL: Never use print() statements in stdio-based MCP servers (corrupts JSON-RPC)
# CRITICAL: FastMCP auto-converts strings to TextContent - don't return List[TextContent]
# CRITICAL: Always use type hints for automatic validation in FastMCP
# CRITICAL: Use @mcp.tool() decorator, not manual tool registration
# CRITICAL: Use logging to stderr only - "Never write to standard output (stdout)"

# SUPABASE-SPECIFIC GOTCHAS:
# CRITICAL: Supabase RLS policies must be enabled and tested with different user contexts
# CRITICAL: Environment variables MUST be loaded with load_dotenv() before Supabase client init
# GOTCHA: Anon Key vs Service Role Key - use anon for normal ops, service role for admin
# GOTCHA: RLS policies act like implicit WHERE clauses - test thoroughly
# GOTCHA: API rate limits especially in free tier - implement reasonable pagination

# PYDANTIC GOTCHAS:
# CRITICAL: Use Pydantic v2 patterns, not v1
# GOTCHA: Field validators run after type conversion - use mode='before' for pre-processing
# GOTCHA: ValidationError must be caught and handled gracefully in MCP tools

# DEVELOPMENT GOTCHAS:
# GOTCHA: Claude Desktop requires absolute paths in --directory argument
# GOTCHA: uv must be used for package management, not pip
# GOTCHA: Test with 'uv run mcp dev' before Claude Desktop integration
# CRITICAL: Never commit .env files - always use .env.example template
```

## Implementation Blueprint

### Data Models and Structure

Create the core data models to ensure type safety and consistency:
```python
# src/database.py - Core Pydantic models for validation
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
import re

class TableQueryRequest(BaseModel):
    table_name: str = Field(..., min_length=1, description="Table name to query")
    limit: Optional[int] = Field(None, ge=1, le=1000, description="Maximum results (default: 100)")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters as key-value pairs")
    
    @field_validator('table_name')
    @classmethod
    def validate_table_name(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError("Invalid table name format")
        return v.strip()

class RecordInsertRequest(BaseModel):
    table_name: str = Field(..., min_length=1, description="Table name for insertion")
    data: Dict[str, Any] = Field(..., description="Record data to insert")
    
class RecordUpdateRequest(BaseModel):
    table_name: str = Field(..., min_length=1, description="Table name to update")
    filters: Dict[str, Any] = Field(..., description="Conditions to identify records")
    updates: Dict[str, Any] = Field(..., description="New values to set")

# Security validation functions
def validate_column_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Validate filter parameters for SQL injection protection"""
    if not filters:
        return {"is_valid": True}
    
    dangerous_patterns = [
        r';\s*drop\s+', r';\s*delete\s+', r';\s*update\s+',
        r'--.*', r'/\*.*\*/', r'\bor\b.*\b1\s*=\s*1\b',
        r'\bunion\b.*\bselect\b'
    ]
    
    for key, value in filters.items():
        if isinstance(value, str):
            for pattern in dangerous_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    return {"is_valid": False, "error": f"Dangerous pattern in {key}"}
    
    return {"is_valid": True}
```

### List of tasks to be completed to fulfill the PRP in order

```yaml
Task 1: Environment and Dependencies Setup
CREATE .env.example:
  - Template with SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
  - LOG_LEVEL, MCP_SERVER_NAME, MCP_MAX_QUERY_LIMIT defaults

UPDATE pyproject.toml:
  - ADD dependencies: "mcp[cli]", "supabase", "python-dotenv", "pydantic"
  - SET requires-python = ">=3.13"

CREATE .gitignore:
  - EXCLUDE .env, __pycache__/, .pytest_cache/, *.pyc

Task 2: Core Database Management Module  
CREATE src/__init__.py:
  - EMPTY file for package structure

CREATE src/database.py:
  - IMPLEMENT SupabaseManager class with connection management
  - IMPLEMENT validation functions (validate_table_name, validate_column_filters)
  - IMPLEMENT Pydantic models (TableQueryRequest, RecordInsertRequest, etc.)
  - INCLUDE comprehensive error handling and security patterns

Task 3: Main MCP Server Implementation
CREATE src/mcp_server.py:
  - IMPORT FastMCP, supabase, pydantic, logging setup
  - INITIALIZE FastMCP server with name "supabase-mcp"
  - IMPLEMENT load_dotenv() and environment validation
  - IMPLEMENT SupabaseManager initialization
  - IMPLEMENT all 5 MCP tools with @mcp.tool() decorator
  - INCLUDE proper logging to stderr (never stdout)

Task 4: Tool Implementation Details
IMPLEMENT @mcp.tool() functions in mcp_server.py:
  - list_tables() -> str: Query information_schema for accessible tables
  - query_table(table_name, limit, filters) -> str: Execute filtered queries
  - describe_table(table_name) -> str: Get table schema information
  - insert_record(table_name, data) -> str: Insert with validation
  - update_record(table_name, filters, updates) -> str: Update with validation

Task 5: Testing Infrastructure
CREATE tests/__init__.py:
  - EMPTY file for test package

CREATE tests/test_database.py:
  - TEST SupabaseManager initialization
  - TEST validation functions with valid/invalid inputs
  - TEST Pydantic models with edge cases

CREATE tests/test_mcp_server.py:
  - TEST MCP server startup
  - TEST tool registration and availability
  - MOCK Supabase client for isolated testing

Task 6: Documentation and Setup
UPDATE README.md:
  - COMPLETE setup instructions following THIS_PROJECT.md structure
  - INCLUDE troubleshooting section
  - DOCUMENT all available tools and examples
  - INCLUDE Claude Desktop integration instructions

Task 7: Local Development Testing
TEST with MCP Inspector:
  - RUN 'uv run mcp dev src/mcp_server.py'
  - VERIFY all tools are visible and functional
  - TEST error cases and validation

Task 8: Claude Desktop Integration
CONFIGURE Claude Desktop:
  - CREATE claude_desktop_config.json entry
  - TEST absolute path configuration
  - VERIFY tools appear in Claude interface
```

### Per Task Pseudocode

```python
# Task 1: Environment Setup Pseudocode
# .env.example structure
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
LOG_LEVEL=INFO
MCP_SERVER_NAME=supabase-mcp
MCP_MAX_QUERY_LIMIT=1000

# Task 2: Database Module Pseudocode
class SupabaseManager:
    def __init__(self, supabase_url: str, supabase_key: str):
        # PATTERN: Validate required environment variables first
        self.validate_credentials(supabase_url, supabase_key)
        self.client = create_client(supabase_url, supabase_key)
    
    def get_client(self) -> Client:
        # PATTERN: Lazy initialization with connection health check
        if not self.client:
            self.initialize()
        return self.client

# Task 3: MCP Server Pseudocode  
from mcp.server.fastmcp import FastMCP
import logging
import sys

# CRITICAL: Configure logging to stderr only
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("supabase-mcp")

# PATTERN: Load environment before any client initialization
load_dotenv()
required_vars = ["SUPABASE_URL", "SUPABASE_ANON_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {missing_vars}")

mcp = FastMCP("supabase-mcp")
supabase_manager = SupabaseManager(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

# Task 4: Tool Implementation Pseudocode
@mcp.tool()
async def query_table(table_name: str, limit: Optional[int] = None, filters: Optional[Dict[str, Any]] = None) -> str:
    """Query a Supabase table with optional filters."""
    try:
        # PATTERN: Always validate inputs first
        request = TableQueryRequest(table_name=table_name, limit=limit, filters=filters)
        
        # PATTERN: Security validation
        filter_validation = validate_column_filters(request.filters or {})
        if not filter_validation["is_valid"]:
            return f"Error: {filter_validation['error']}"
        
        # PATTERN: Apply reasonable defaults
        limit = request.limit or 100
        
        # PATTERN: Supabase fluent API usage
        client = supabase_manager.get_client()
        query = client.table(request.table_name).select("*")
        
        if request.filters:
            for key, value in request.filters.items():
                query = query.eq(key, value)
        
        query = query.limit(limit)
        result = query.execute()
        
        # PATTERN: Standardized response format
        if result.data:
            return f"**Query Results:**\n```json\n{json.dumps(result.data, indent=2, default=str)}\n```"
        else:
            return f"No data found in table '{request.table_name}' with given criteria."
            
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return f"Input validation failed: {str(e)}"
    except Exception as e:
        logger.error(f"Database error: {e}")
        return f"Database error: {str(e)}"
```

### Integration Points
```yaml
ENVIRONMENT:
  - create: .env file with Supabase credentials
  - pattern: "load_dotenv() before any client initialization"
  
DEPENDENCIES:
  - add to: pyproject.toml
  - pattern: "uv add 'mcp[cli]' supabase python-dotenv pydantic"
  
LOGGING:
  - configure: stderr logging only
  - pattern: "logging.basicConfig(stream=sys.stderr)"
  
CLAUDE_DESKTOP:
  - configure: absolute path in claude_desktop_config.json
  - pattern: "command: 'uv', args: ['--directory', '/absolute/path', 'run', 'python', 'src/mcp_server.py']"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Install dependencies first
uv sync

# Run these FIRST - fix any errors before proceeding
uv run ruff check src/ --fix       # Auto-fix style issues
uv run mypy src/                   # Type checking

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests
```python
# CREATE tests/test_database.py with these test cases:
def test_supabase_manager_initialization():
    """Test SupabaseManager initializes correctly"""
    manager = SupabaseManager("https://test.supabase.co", "test-key")
    assert manager.get_client() is not None

def test_table_name_validation():
    """Test table name validation catches invalid patterns"""
    with pytest.raises(ValueError):
        TableQueryRequest(table_name="'; DROP TABLE users; --")

def test_filter_validation():
    """Test SQL injection prevention in filters"""
    result = validate_column_filters({"name": "'; DROP TABLE users; --"})
    assert not result["is_valid"]

def test_query_request_model():
    """Test Pydantic model validation"""
    request = TableQueryRequest(table_name="users", limit=50)
    assert request.table_name == "users"
    assert request.limit == 50
```

```bash
# Run and iterate until passing:
uv run pytest tests/ -v
# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: MCP Server Integration Test
```bash
# Start MCP server
uv run python src/mcp_server.py

# Test with MCP Inspector (in another terminal)
uv run mcp dev src/mcp_server.py

# Expected output:
# - Server starts without errors
# - All 5 tools listed (list_tables, query_table, describe_table, insert_record, update_record)
# - Tools can be invoked through inspector
# - No JSON-RPC errors in output
# - Supabase connection successful

# Manual tool testing in inspector:
# 1. Call list_tables() - should return available tables
# 2. Call query_table("users", 10) - should return up to 10 user records
# 3. Call describe_table("users") - should return table schema
# 4. Test validation with invalid inputs
```

### Level 4: Claude Desktop Integration Test
```bash
# Install in Claude Desktop
uv run mcp install src/mcp_server.py --name "Supabase Database"

# Or manually configure claude_desktop_config.json:
{
  "mcpServers": {
    "supabase-database": {
      "command": "uv",
      "args": [
        "--directory", 
        "/absolute/path/to/context-engineering-mcp-db",
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

# Test in Claude Desktop:
# 1. Check tool settings icon appears
# 2. Test natural language queries: "Show me all users in the database"
# 3. Test data insertion: "Add a new user with name 'Test' and email 'test@example.com'"
# 4. Verify error handling with invalid requests

# Expected: Tools visible in Claude, successful database operations, proper error messages
# If error: Check logs at ~/Library/Logs/Claude/mcp*.log
```

## Final Validation Checklist
- [ ] All dependencies installed: `uv sync`
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `uv run ruff check src/`
- [ ] No type errors: `uv run mypy src/`
- [ ] MCP server starts: `uv run python src/mcp_server.py`
- [ ] MCP inspector works: `uv run mcp dev src/mcp_server.py`
- [ ] All 5 tools visible in inspector
- [ ] Claude Desktop integration: Tools appear and function
- [ ] Supabase connection working with real database
- [ ] RLS policies respected (if enabled on test database)
- [ ] Input validation preventing SQL injection
- [ ] Error cases handled gracefully
- [ ] No print() statements in server code
- [ ] Environment variables loaded with load_dotenv()
- [ ] Logging configured to stderr only
- [ ] Documentation complete and accurate

---

## Anti-Patterns to Avoid
- ❌ Don't use print() statements - corrupts MCP JSON-RPC protocol
- ❌ Don't return List[TextContent] - FastMCP auto-converts strings
- ❌ Don't skip Pydantic validation - security critical
- ❌ Don't bypass RLS policies - defeats security purpose
- ❌ Don't hardcode credentials - use environment variables
- ❌ Don't ignore type hints - FastMCP depends on them
- ❌ Don't skip error handling - causes poor user experience
- ❌ Don't use service role key for normal operations - security risk

## Confidence Score: 9/10

This PRP provides comprehensive context for one-pass implementation with:
- ✅ Complete technical specifications
- ✅ All required documentation links and patterns
- ✅ Detailed implementation blueprint with pseudocode
- ✅ Executable validation loops
- ✅ Security considerations and gotchas
- ✅ Real-world integration examples
- ✅ Progressive testing approach

The only risk (reducing score by 1) is the dependency on a real Supabase instance for full testing, but the implementation provides sufficient mocking strategies and validation to ensure success.