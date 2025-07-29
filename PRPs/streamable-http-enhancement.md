name: "Streamable HTTP Protocol Enhancement for Supabase MCP Server"
description: |

## Purpose
Enhance the existing Supabase MCP server to support the streamable HTTP protocol as an alternative to STDIO transport, enabling web-based, streaming interactions with Claude Desktop and remote deployment capabilities while maintaining backward compatibility.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in GUIDELINES.md

---

## Goal
Transform the existing STDIO-based Supabase MCP server into a dual-mode server that supports both STDIO (current) and streamable HTTP transport protocols, enabling web deployment, remote access, and bidirectional streaming while preserving all existing functionality and security features.

## Why
- **Scalability**: Enable horizontal scaling through web-based deployment
- **Remote Access**: Allow MCP server deployment on cloud infrastructure
- **Modern Protocol**: Adopt MCP's recommended streamable HTTP transport (2025-03-26 spec)
- **Bidirectional Streaming**: Support real-time database operations and notifications
- **Future-Proofing**: Prepare for deprecation of STDIO-only implementations
- **Integration Flexibility**: Enable integration with web services and remote Claude Desktop instances

## What
Implement streamable HTTP transport following MCP specification 2025-03-26 while maintaining complete backward compatibility with existing STDIO functionality.

### Success Criteria
- [ ] Server supports both `--mode=stdio` (default) and `--mode=http` command-line options
- [ ] All existing @mcp.tool() functions work identically in both modes
- [ ] HTTP mode supports single endpoint `/mcp` with JSON-RPC 2.0 over HTTP
- [ ] Bidirectional streaming implemented using Server-Sent Events (SSE)
- [ ] Session management with `Mcp-Session-Id` header support
- [ ] All existing security validations (RLS, Pydantic, SQL injection protection) preserved
- [ ] Complete test coverage for HTTP mode matching existing STDIO tests
- [ ] Claude Desktop integration working with HTTP configuration
- [ ] Remote deployment capability demonstrated

## All Needed Context

### Documentation & References (list all context needed to implement the feature)
```yaml
# MUST READ - Include these in your context window

# Project Documentation
- file: GUIDELINES.md
  why: Technical implementation standards for this project
  critical: Type safety rules, security patterns, code style, MCP development patterns

- file: README.md  
  why: Project overview, Claude Desktop integration patterns, troubleshooting
  critical: Current MCP server architecture, environment setup, testing commands

- file: FEATURE_STREAMABLE_HTTP.md
  why: Detailed feature requirements and examples
  critical: CLI interface, configuration patterns, deployment requirements

# Current Implementation Files
- file: src/mcp_server.py
  why: Main MCP server implementation using FastMCP
  critical: Tool implementations, error handling patterns, environment validation
  
- file: src/database.py
  why: SupabaseManager and security validation patterns
  critical: Pydantic models, SQL injection prevention, connection management

- file: tests/test_mcp_server.py
  why: Comprehensive test patterns and mocking strategies
  critical: Tool testing patterns, error scenario handling, validation tests

- file: pyproject.toml
  why: Current dependencies and project configuration
  critical: Need to add FastAPI, uvicorn for HTTP mode

# MCP Framework Documentation
- url: https://modelcontextprotocol.io/specification/2025-03-26/basic/transports
  why: Official MCP streamable HTTP transport specification
  section: Protocol requirements, message format, security considerations
  critical: Single endpoint pattern, SSE streaming, session management
  
- url: https://github.com/modelcontextprotocol/python-sdk
  why: FastMCP patterns and HTTP transport examples
  section: Server setup, transport configuration, tool registration
  critical: Use FastMCP, not low-level server APIs

- url: https://blog.cloudflare.com/streamable-http-mcp-servers-python/
  why: Implementation patterns and best practices
  section: Single endpoint design, bidirectional communication
  critical: Connection upgrade patterns, error handling

# FastAPI Documentation  
- url: https://fastapi.tiangolo.com/
  why: Web framework for HTTP transport implementation
  section: SSE endpoints, middleware, CORS configuration
  critical: Async request handling, response streaming
  
- url: https://fastapi.tiangolo.com/advanced/server-sent-events/
  why: Server-Sent Events implementation patterns
  section: Streaming responses, event formatting
  critical: EventSource compatibility, connection management

# Supabase Documentation  
- url: https://supabase.com/docs/reference/python/introduction
  why: Maintain existing client usage patterns
  section: Query methods, error handling, async operations
  critical: No changes to existing database operations needed
  
- url: https://supabase.com/docs/guides/auth/row-level-security
  why: Ensure RLS security maintained in HTTP mode
  critical: User context passing in HTTP requests, JWT handling

```

### Current Codebase Tree
```bash
context-engineering-mcp-db/
├── src/
│   ├── __init__.py
│   ├── mcp_server.py      # Main FastMCP server (STDIO only)
│   └── database.py        # SupabaseManager + validation
├── tests/
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_mcp_server.py # Comprehensive tool tests
│   └── test_client.py
├── PRPs/
│   ├── templates/prp_base.md
│   └── supabase-mcp-server.md
├── .env.example           # Environment variables template
├── pyproject.toml         # uv dependencies (needs FastAPI added)
└── README.md              # Setup and usage instructions
```

### Desired Codebase Tree with Files to be Added
```bash
context-engineering-mcp-db/
├── src/
│   ├── __init__.py
│   ├── mcp_server.py      # ENHANCED: Dual-mode server with CLI args
│   ├── database.py        # UNCHANGED: Existing patterns preserved
│   ├── http_transport.py  # NEW: FastAPI HTTP transport implementation
│   └── transport_base.py  # NEW: Abstract transport interface
├── tests/
│   ├── __init__.py
│   ├── test_database.py   # UNCHANGED: Existing tests preserved
│   ├── test_mcp_server.py # ENHANCED: Tests for both modes
│   ├── test_http_transport.py # NEW: HTTP-specific tests
│   └── test_client.py
├── examples/
│   └── claude_desktop_http_config.json # NEW: HTTP mode Claude config
├── .env.example           # ENHANCED: Add HTTP_PORT, HTTP_HOST variables
├── pyproject.toml         # ENHANCED: Add fastapi, uvicorn, httpx
└── README.md              # ENHANCED: HTTP mode documentation
```

### Known Gotchas of Our Codebase & Library Quirks
```python
# CRITICAL: Current project patterns that MUST be preserved
# FastMCP: Uses @mcp.tool() decorators, returns strings/objects (not TextContent)
# Database: SupabaseManager with comprehensive validation must be reused
# Security: Pydantic models, SQL injection prevention, RLS policies maintained
# Testing: Mock patterns with supabase_manager fixture must be extended
# Environment: load_dotenv() pattern must work in both modes

# MCP STREAMABLE HTTP SPECIFIC GOTCHAS:
# CRITICAL: MCP 2025-03-26 spec uses single endpoint /mcp (not /api or /tools)
# CRITICAL: JSON-RPC 2.0 messages over HTTP POST (not REST endpoints)
# CRITICAL: Server-Sent Events for streaming, not WebSockets
# CRITICAL: Must include Accept: application/json,text/event-stream header
# CRITICAL: Session management via Mcp-Session-Id header (optional)
# CRITICAL: Origin header validation required for security
# CRITICAL: Must bind to localhost by default to prevent attacks

# FASTAPI INTEGRATION GOTCHAS:
# CRITICAL: FastMCP tools return strings - FastAPI must wrap in proper JSON-RPC
# CRITICAL: SSE endpoint separate from main MCP endpoint for streaming responses
# CRITICAL: CORS configuration needed for web-based Claude Desktop
# CRITICAL: Async context managers needed for streaming database operations
# GOTCHA: Claude Desktop requires absolute paths in HTTP URL configuration
# GOTCHA: Environment variables must be passed correctly in HTTP mode
# GOTCHA: HTTP server must handle graceful shutdown to close database connections

# SUPABASE + HTTP GOTCHAS:
# GOTCHA: RLS policies must work with HTTP requests (user context via headers)
# GOTCHA: Connection pooling behavior different in HTTP vs STDIO mode
# GOTCHA: Database timeouts need different handling in streaming context
```

## Implementation Blueprint

### Data Models and Structure

Preserve existing Pydantic models and create transport abstraction:
```python
# src/transport_base.py - New abstract interface
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class TransportBase(ABC):
    """Abstract base class for MCP transport implementations."""
    
    @abstractmethod
    async def run(self) -> None:
        """Start the transport server."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the transport server."""
        pass

# Existing models in src/database.py PRESERVED:
# - TableQueryRequest, RecordInsertRequest, RecordUpdateRequest
# - validate_table_name(), validate_column_filters()
# - SupabaseManager class (unchanged)
```

### List of Tasks to be Completed in Order

```yaml
Task 1: Environment and Dependencies Setup
MODIFY pyproject.toml:
  - ADD dependencies: "fastapi>=0.104.0", "uvicorn[standard]>=0.24.0", "httpx>=0.25.0"
  - PRESERVE existing mcp, supabase, pydantic dependencies
  - ENSURE uv sync works after changes

MODIFY .env.example:
  - ADD: HTTP_HOST=127.0.0.1
  - ADD: HTTP_PORT=8000  
  - ADD: HTTP_CORS_ORIGINS=http://localhost:3000
  - PRESERVE existing SUPABASE_* variables

Task 2: Create Transport Abstraction Layer
CREATE src/transport_base.py:
  - IMPLEMENT abstract TransportBase class
  - DEFINE common interface for STDIO and HTTP transports
  - INCLUDE proper error handling and lifecycle management

Task 3: Implement HTTP Transport
CREATE src/http_transport.py:
  - IMPLEMENT FastAPI-based HTTP transport class
  - USE single /mcp endpoint following MCP 2025-03-26 spec
  - SUPPORT JSON-RPC 2.0 message format
  - IMPLEMENT Server-Sent Events for streaming responses
  - INCLUDE session management with Mcp-Session-Id header
  - ADD proper CORS and Origin validation
  - INTEGRATE with existing SupabaseManager (no changes to database.py)

Task 4: Enhance Main Server with Dual-Mode Support
MODIFY src/mcp_server.py:
  - ADD argparse for --mode=stdio|http, --port, --host CLI options
  - PRESERVE existing FastMCP server creation for STDIO mode
  - ADD conditional HTTP transport instantiation
  - MAINTAIN all existing @mcp.tool() functions unchanged
  - PRESERVE existing validation and error handling patterns
  - ENSURE environment validation works in both modes

Task 5: Create Comprehensive HTTP Tests
CREATE tests/test_http_transport.py:
  - MIRROR existing test patterns from test_mcp_server.py
  - TEST all MCP tools via HTTP requests (not just STDIO)
  - INCLUDE SSE streaming tests for long-running operations
  - TEST session management and reconnection scenarios
  - VALIDATE JSON-RPC 2.0 compliance
  - TEST error handling matches STDIO behavior
  - INCLUDE security tests (CORS, Origin validation, rate limiting)

Task 6: Enhance Existing Tests for Dual-Mode
MODIFY tests/test_mcp_server.py:
  - ADD parameterized tests for both STDIO and HTTP modes
  - PRESERVE existing mock patterns and test cases
  - ENSURE test coverage for mode switching functionality
  - VALIDATE that tool behavior identical in both modes

Task 7: Update Documentation and Examples
MODIFY README.md:
  - ADD HTTP mode usage examples
  - INCLUDE Claude Desktop HTTP configuration
  - ADD troubleshooting section for HTTP-specific issues
  - PRESERVE existing STDIO documentation

CREATE examples/claude_desktop_http_config.json:
  - PROVIDE sample Claude Desktop configuration for HTTP mode
  - INCLUDE proper URL formatting and environment variables
  - ADD comments explaining key differences from STDIO config

Task 8: Integration Testing and Validation
TEST manual integration scenarios:
  - VALIDATE uv run python src/mcp_server.py --mode=http works
  - CONFIRM mcp dev compatibility maintained
  - TEST Claude Desktop integration with HTTP configuration
  - VERIFY remote deployment capability (different host/port)
  - ENSURE graceful degradation when HTTP dependencies missing
```

### Per Task Pseudocode with Critical Details

```python
# Task 3: HTTP Transport Implementation (src/http_transport.py)
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import json
import asyncio
from typing import AsyncGenerator

class HttpTransport(TransportBase):
    def __init__(self, mcp_server, host: str = "127.0.0.1", port: int = 8000):
        self.mcp_server = mcp_server  # FastMCP instance
        self.app = FastAPI()
        self.host = host
        self.port = port
        self._setup_routes()
    
    def _setup_routes(self):
        @self.app.post("/mcp")
        async def mcp_endpoint(request: Request):
            # PATTERN: Validate Origin header (security requirement)
            origin = request.headers.get("origin")
            if origin and not self._is_valid_origin(origin):
                raise HTTPException(403, "Invalid origin")
            
            # PATTERN: Parse JSON-RPC 2.0 message
            body = await request.json()
            method = body.get("method")
            params = body.get("params", {})
            id = body.get("id")
            
            # PATTERN: Route to existing MCP tool (preserved from STDIO)
            if method in self.mcp_server._tools:
                try:
                    # CRITICAL: Reuse existing tool implementation
                    result = await self.mcp_server._tools[method](**params)
                    
                    # PATTERN: Check if response should be streamed
                    if self._should_stream(method, result):
                        return self._create_sse_response(result, id)
                    else:
                        # PATTERN: Standard JSON-RPC response
                        return {"jsonrpc": "2.0", "id": id, "result": result}
                        
                except Exception as e:
                    # PATTERN: Preserve existing error handling
                    return {"jsonrpc": "2.0", "id": id, "error": {"code": -32603, "message": str(e)}}
    
    def _create_sse_response(self, result: Any, request_id: str) -> StreamingResponse:
        """Create Server-Sent Events response for streaming."""
        async def event_generator() -> AsyncGenerator[str, None]:
            # CRITICAL: Follow SSE format for MCP compatibility
            yield f"data: {json.dumps({'jsonrpc': '2.0', 'id': request_id, 'result': result})}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )

# Task 4: Enhanced Main Server (src/mcp_server.py modifications)
async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    
    # PATTERN: Preserve existing validation and setup
    validate_environment()
    config = get_config()
    
    # PATTERN: Initialize existing MCP server (unchanged)
    mcp = FastMCP(config["server_name"])
    # ... existing @mcp.tool() registrations unchanged ...
    
    if args.mode == "stdio":
        # PATTERN: Existing STDIO behavior preserved
        mcp.run()
    elif args.mode == "http":
        # PATTERN: New HTTP transport using existing tools
        from src.http_transport import HttpTransport
        transport = HttpTransport(mcp, args.host, args.port)
        await transport.run()
```

### Integration Points
```yaml
CLI_INTERFACE:
  - modify: src/mcp_server.py main() function
  - pattern: "argparse with --mode, --host, --port arguments"
  - preserve: "existing mcp.run() for STDIO mode"
  
FASTAPI_INTEGRATION:
  - add to: pyproject.toml dependencies
  - pattern: "fastapi>=0.104.0, uvicorn[standard]>=0.24.0"
  - mount: "HTTP transport at /mcp endpoint"
  
ENVIRONMENT_CONFIG:
  - add to: .env.example
  - pattern: "HTTP_HOST=127.0.0.1, HTTP_PORT=8000"
  - preserve: "existing SUPABASE_* variables"
  
CLAUDE_DESKTOP:
  - add to: examples/claude_desktop_http_config.json  
  - pattern: '{"mcpServers": {"supabase-http": {"url": "http://localhost:8000/mcp"}}}'
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
uv sync                             # Install new FastAPI dependencies
uv run ruff check src/ --fix        # Auto-fix style issues
uv run mypy src/                    # Type checking with new modules

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests for Each New Feature/File
```bash
# Test new HTTP transport module
uv run pytest tests/test_http_transport.py -v

# Test enhanced dual-mode server
uv run pytest tests/test_mcp_server.py -v

# Test that database functionality unchanged
uv run pytest tests/test_database.py -v

# Expected: All tests pass, no regression in existing functionality
# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test - Both Modes
```bash
# Test STDIO mode (existing behavior)
uv run python src/mcp_server.py --mode=stdio &
uv run mcp dev src/mcp_server.py
# Expected: Existing tools work, no changes in behavior

# Test HTTP mode (new functionality) 
uv run python src/mcp_server.py --mode=http --port=8000 &
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json,text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"list_tables","params":{},"id":1}'
# Expected: Valid JSON-RPC response with table list

# Test streaming capability
curl -X POST http://localhost:8000/mcp \
  -H "Accept: text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"query_table","params":{"table_name":"large_table"},"id":2}'
# Expected: Server-Sent Events stream with data
```

### Level 4: Claude Desktop Integration Test - HTTP Mode
```bash
# Create HTTP configuration
cat > ~/.claude_desktop_config_http.json << EOF
{
  "mcpServers": {
    "supabase-http": {
      "url": "http://localhost:8000/mcp",
      "env": {
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_ANON_KEY": "your-anon-key"
      }
    }
  }
}
EOF

# Start HTTP server
uv run python src/mcp_server.py --mode=http &

# Test in Claude Desktop with HTTP configuration
# Expected: Tools visible, database operations work, streaming responses function
# If error: Check Claude logs, verify URL format, confirm server accessibility
```

## Final Validation Checklist
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `uv run ruff check src/`
- [ ] No type errors: `uv run mypy src/`
- [ ] STDIO mode unchanged: `uv run python src/mcp_server.py --mode=stdio`
- [ ] HTTP mode starts: `uv run python src/mcp_server.py --mode=http`
- [ ] HTTP endpoint responds: `curl http://localhost:8000/mcp`
- [ ] JSON-RPC 2.0 compliance: Valid request/response format
- [ ] SSE streaming works: Long-running operations stream properly
- [ ] Claude Desktop STDIO: Existing configuration still works
- [ ] Claude Desktop HTTP: New HTTP configuration works
- [ ] All tools identical behavior: STDIO vs HTTP tool responses match
- [ ] Security maintained: RLS, validation, SQL injection prevention
- [ ] Error cases graceful: HTTP errors return proper JSON-RPC error responses
- [ ] Session management: Mcp-Session-Id header handling
- [ ] CORS and Origin validation: Security headers properly enforced
- [ ] Database connections: Proper cleanup in both transport modes
- [ ] Environment variables: Both modes read configuration correctly
- [ ] Remote deployment: Server accessible from different host/port
- [ ] Backward compatibility: Existing STDIO usage unchanged

---

## Anti-Patterns to Avoid
- ❌ Don't modify existing database.py - reuse SupabaseManager as-is
- ❌ Don't change @mcp.tool() function signatures - maintain compatibility  
- ❌ Don't create REST endpoints - use single /mcp with JSON-RPC 2.0
- ❌ Don't use WebSockets - use Server-Sent Events for streaming
- ❌ Don't skip Origin header validation - security requirement
- ❌ Don't hardcode ports/hosts - use environment variables and CLI args
- ❌ Don't break STDIO mode - maintain backward compatibility
- ❌ Don't change error response format - preserve existing patterns
- ❌ Don't modify test mocking patterns - extend existing mock strategies
- ❌ Don't skip session management - implement Mcp-Session-Id header support

---

## Quality Score: 9/10

**Confidence Level**: High confidence for one-pass implementation success due to:
✅ Comprehensive codebase analysis with existing patterns identified  
✅ Complete external documentation research including MCP 2025-03-26 spec  
✅ Detailed FastAPI + MCP integration patterns from multiple sources  
✅ Existing security and validation patterns well understood  
✅ Test patterns clearly established with mock strategies  
✅ Environment setup and configuration patterns documented  
✅ Claude Desktop integration requirements specified  
✅ Progressive validation loops with specific commands  
✅ Anti-patterns identified to prevent common pitfalls  

**Potential challenges**: 
- SSE streaming implementation complexity (mitigated by detailed examples)
- JSON-RPC 2.0 compliance edge cases (mitigated by specification references)
- Session management implementation details (mitigated by optional implementation)