name: "Base PRP Template (Context-Rich with Validation Loops)"
description: |

## Purpose
Template optimized for AI agents to implement features with sufficient context and self-validation capabilities to achieve working code through iterative refinement.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in GUIDELINES.md

---

## Goal
[What needs to be built - be specific about the end state and desires]

## Why
- [Business value and user impact]
- [Integration with existing features]
- [Problems this solves and for whom]

## What
[User-visible behavior and technical requirements]

### Success Criteria
- [ ] [Specific measurable outcomes]

## All Needed Context

### Documentation & References (list all context needed to implement the feature)
```yaml
# MUST READ - Include these in your context window

# Project Documentation
- file: GUIDELINES.md
  why: Technical implementation standards for this project
  critical: Type safety rules, security patterns, code style

- file: THIS_PROJECT.md  
  why: Project overview, gotchas, and setup requirements
  critical: Supabase-specific considerations and fallsticks

# MCP Framework Documentation
- url: https://modelcontextprotocol.io/introduction
  why: Core MCP concepts and architecture
  section: Tools, Resources, Transport protocols
  
- url: https://github.com/modelcontextprotocol/python-sdk
  why: FastMCP patterns and examples
  section: Tool implementation, server setup
  critical: Use FastMCP, not low-level server APIs

- url: https://modelcontextprotocol.io/quickstart/server
  why: Server development patterns
  critical: Logging restrictions, Claude Desktop integration

# Supabase Documentation  
- url: https://supabase.com/docs/reference/python/introduction
  why: Python client usage patterns
  section: Query methods, error handling
  
- url: https://supabase.com/docs/guides/auth/row-level-security
  why: RLS security implementation
  critical: Must enable RLS policies for security

# Code Examples
- file: [path/to/example.py]
  why: [Pattern to follow, gotchas to avoid]

# Additional Context
- docfile: [PRPs/ai_docs/file.md]
  why: [docs that the user has pasted in to the project]

```

### Current Codebase tree (run `tree` in the root of the project) to get an overview of the codebase
```bash

```

### Desired Codebase tree with files to be added and responsibility of file
```bash

```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: [Library name] requires [specific setup]
# Example: FastAPI requires async functions for endpoints
# Example: This ORM doesn't support batch inserts over 1000 records
# Example: We use pydantic v2 and FastMCP patterns

# MCP-SPECIFIC GOTCHAS:
# CRITICAL: Never use print() statements in stdio-based MCP servers (corrupts JSON-RPC)
# CRITICAL: FastMCP auto-converts strings to TextContent - don't return List[TextContent]
# CRITICAL: Always use type hints for automatic validation in FastMCP
# CRITICAL: Use @mcp.tool() decorator, not manual tool registration
# CRITICAL: Supabase RLS policies must be enabled and tested with different user contexts
# GOTCHA: Environment variables MUST be loaded with load_dotenv() before Supabase client init
# GOTCHA: Claude Desktop requires absolute paths in --directory argument
```

## Implementation Blueprint

### Data models and structure

Create the core data models, we ensure type safety and consistency.
```python
Examples: 
 - orm models
 - pydantic models
 - pydantic schemas
 - pydantic validators

```

### list of tasks to be completed to fullfill the PRP in the order they should be completed

```yaml
Task 1:
MODIFY src/existing_module.py:
  - FIND pattern: "class OldImplementation"
  - INJECT after line containing "def __init__"
  - PRESERVE existing method signatures

CREATE src/new_feature.py:
  - MIRROR pattern from: src/similar_feature.py
  - MODIFY class name and core logic
  - KEEP error handling pattern identical

...(...)

Task N:
...

```


### Per task pseudocode as needed added to each task
```python

# Task 1
# Pseudocode with CRITICAL details dont write entire code
async def new_feature(param: str) -> Result:
    # PATTERN: Always validate input first (see src/validators.py)
    validated = validate_input(param)  # raises ValidationError
    
    # GOTCHA: This library requires connection pooling
    async with get_connection() as conn:  # see src/db/pool.py
        # PATTERN: Use existing retry decorator
        @retry(attempts=3, backoff=exponential)
        async def _inner():
            # CRITICAL: API returns 429 if >10 req/sec
            await rate_limiter.acquire()
            return await external_api.call(validated)
        
        result = await _inner()
    
    # PATTERN: Standardized response format
    return format_response(result)  # see src/utils/responses.py
```

### Integration Points
```yaml
DATABASE:
  - migration: "Add column 'feature_enabled' to users table"
  - index: "CREATE INDEX idx_feature_lookup ON users(feature_id)"
  
CONFIG:
  - add to: config/settings.py
  - pattern: "FEATURE_TIMEOUT = int(os.getenv('FEATURE_TIMEOUT', '30'))"
  
ROUTES:
  - add to: src/api/routes.py  
  - pattern: "router.include_router(feature_router, prefix='/feature')"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
ruff check src/new_feature.py --fix  # Auto-fix what's possible
mypy src/new_feature.py              # Type checking

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests each new feature/file/function use existing test patterns
```python
# CREATE test_new_feature.py with these test cases:
def test_happy_path():
    """Basic functionality works"""
    result = new_feature("valid_input")
    assert result.status == "success"

def test_validation_error():
    """Invalid input raises ValidationError"""
    with pytest.raises(ValidationError):
        new_feature("")

def test_external_api_timeout():
    """Handles timeouts gracefully"""
    with mock.patch('external_api.call', side_effect=TimeoutError):
        result = new_feature("valid")
        assert result.status == "error"
        assert "timeout" in result.message
```

```bash
# Run and iterate until passing:
uv run pytest test_new_feature.py -v
# If failing: Read error, understand root cause, fix code, re-run (never mock to pass)
```

### Level 3: Integration Test
```bash
# MCP Server Testing
uv run mcp dev src/mcp_server.py

# Test with MCP Inspector (in another terminal)
# Should show available tools and allow testing

# Manual tool testing
# Test each @mcp.tool() function with valid/invalid inputs

# Expected: Tools listed, no JSON-RPC errors, proper responses
# If error: Check stderr output for Python exceptions
```

### Level 4: Claude Desktop Integration Test
```bash
# Install in Claude Desktop
uv run mcp install src/mcp_server.py --name "Test Server"

# Test in Claude Desktop
# 1. Check tool settings icon appears
# 2. Test each tool with natural language
# 3. Verify Supabase connections work

# Expected: Tools visible in Claude, successful database operations
# If error: Check Claude logs at ~/Library/Logs/Claude/mcp*.log
```

## Final validation Checklist
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `uv run ruff check src/`
- [ ] No type errors: `uv run mypy src/`
- [ ] MCP server starts: `uv run python src/mcp_server.py`
- [ ] MCP inspector works: `uv run mcp dev src/mcp_server.py`
- [ ] Claude Desktop integration: `uv run mcp install src/mcp_server.py --name "Test"`
- [ ] All tools visible and functional in Claude Desktop
- [ ] Supabase connections working (if applicable)
- [ ] RLS policies tested with different user contexts (if applicable)
- [ ] Error cases handled gracefully
- [ ] No print() statements in MCP server code
- [ ] Environment variables properly loaded with load_dotenv()
- [ ] Documentation updated if needed

---

## Anti-Patterns to Avoid
- ❌ Don't create new patterns when existing ones work
- ❌ Don't skip validation because "it should work"  
- ❌ Don't ignore failing tests - fix them
- ❌ Don't use sync functions in async context
- ❌ Don't hardcode values that should be config
- ❌ Don't catch all exceptions - be specific