## FEATURE:

> **📋 Feature Overview:** This file describes WHAT needs to be built. For technical implementation details, see [GUIDELINES.md](./GUIDELINES.md)

**Enhance MCP Server to Support Streamable HTTP Protocol**

Enhance the existing Supabase MCP server to support the streamable HTTP protocol as an alternative to the current STDIO transport. This will enable web-based, streaming interactions with Claude Desktop and other MCP clients, improving scalability, remote access, and integration with web services while preserving backward compatibility with STDIO mode.

**Key Enhancements:**
- Implement streamable HTTP endpoint for MCP communications.
- Support bidirectional streaming for real-time database operations (e.g., queries, inserts, updates).
- Maintain security features like Row Level Security (RLS) and Pydantic validation.
- Add configuration options to switch between STDIO and HTTP modes.
- Ensure compatibility with existing tools (e.g., query_table, insert_record).
- (Planned) Enable remote deployment options for the HTTP server.

## EXAMPLES:

**Enhanced MCP Server Usage with HTTP:**

1. **Starting the Server in HTTP Mode**
   ```bash
   # Run in HTTP mode with port configuration
   uv run python src/mcp_server.py --mode=http --port=8000
   ```

2. **Claude Desktop Integration for HTTP**
   ```json
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
   ```

3. **Streaming Query Example (Client-Side)**
   ```python
   # Example client interaction with streaming HTTP
   import requests
   response = requests.post("http://localhost:8000/mcp", json={"method": "query_table", "params": {"table_name": "users", "limit": 50}}, stream=True)
   for chunk in response.iter_content(chunk_size=1024):
       print(chunk.decode('utf-8'))  # Streams results in real-time
   ```

> **💡 Full Code Examples:** Detailed implementations for HTTP mode will follow patterns in [GUIDELINES.md - Streamable HTTP Implementation](./GUIDELINES.md#streamable-http-implementation)

## DOCUMENTATION:

**Required Documentation for Development:**

📖 **Project Documentation:**
- **[GUIDELINES.md](./GUIDELINES.md)** - Updated technical guidelines including streamable HTTP patterns.

🌐 **External Documentation:**

1. **Streamable HTTP Protocol for MCP**
   - https://www.claudemcp.com/docs/streamable-http
   - https://modelcontextprotocol.io/quickstart/server (for general MCP server quickstart)

2. **Supabase Python Client Documentation** (unchanged from core project)
   - https://supabase.com/docs/reference/python/introduction
   - https://github.com/supabase/supabase-py

3. **Model Context Protocol (MCP) Documentation**
   - https://modelcontextprotocol.io/introduction
   - https://github.com/modelcontextprotocol/python-sdk

4. **FastMCP Framework with HTTP Support**
   - https://github.com/modelcontextprotocol/python-sdk (FastMCP examples, check for HTTP extensions)

5. **Supabase Row Level Security (RLS)**
   - https://supabase.com/docs/guides/auth/row-level-security

6. **Pydantic Validation and Async HTTP (e.g., with FastAPI)**
   - https://docs.pydantic.dev/latest/
   - https://fastapi.tiangolo.com/ (for HTTP server implementation)

## OTHER CONSIDERATIONS:

**Important Considerations and Common Pitfalls:**

1. **Security (CRITICAL):**
   - ❌ **Pitfall:** Exposing HTTP endpoints without proper authentication.
   - ✅ **Solution:** Implement API key or JWT validation on HTTP routes; integrate with Supabase auth.
   - ❌ **Pitfall:** Streaming large datasets without limits.
   - ✅ **Solution:** Enforce pagination and rate limiting in streams.

2. **MCP-Specific Gotchas for HTTP:**
   - ❌ **Pitfall:** Assuming STDIO patterns work directly in HTTP (e.g., no direct stdin/stdout).
   - ✅ **Solution:** Use FastAPI or similar for HTTP handling; adapt tool decorators for streaming responses.
   - ❌ **Pitfall:** Non-streaming responses blocking real-time use cases.
   - ✅ **Solution:** Use Server-Sent Events (SSE) or WebSockets for bidirectional streaming.

3. **Supabase-Specific Considerations:**
   - ❌ **Pitfall:** HTTP mode introducing latency in real-time operations.
   - ✅ **Solution:** Leverage Supabase real-time subscriptions over HTTP streams.
   - ❌ **Pitfall:** RLS not applying in remote HTTP contexts.
   - ✅ **Solution:** Pass user context (e.g., JWT) in HTTP requests to enforce RLS.

4. **Development Workflow:**
   - ✅ **Testing:** Test HTTP mode with `uv run mcp dev src/mcp_server.py --mode=http`; use tools like curl or Postman for streaming.
   - ✅ **Installation:** Update Claude Desktop config for HTTP URLs.
   - ❌ **Pitfall:** Forgetting to handle CORS for web clients.
   - ✅ **Dependencies:** `uv add fastapi uvicorn` for HTTP server.
   - 📖 **Full Workflow Details:** See [GUIDELINES.md - Local Development Workflow](./GUIDELINES.md#local-development-workflow)

5. **Performance & Limits:**
   - ⚠️ **Note:** HTTP streaming may increase overhead vs STDIO.
   - ✅ **Solution:** Implement chunked streaming and connection pooling.

6. **Error Handling:**
   - ❌ **Pitfall:** Streams failing silently on errors.
   - ✅ **Solution:** Send error events in the stream with specific messages.

7. **Environment & Deployment:**
   - ❌ **Pitfall:** Hardcoding HTTP ports or hosts.
   - ✅ **Solution:** Use environment variables (e.g., HTTP_PORT).

8. **Project Setup & Documentation (CRITICAL):**
   - ✅ **Required:** Update `.env.example` with HTTP-related vars (e.g., HTTP_PORT=8000).
   - ✅ **Required:** Enhance README.md with HTTP setup instructions.
   - ❌ **Pitfall:** Breaking STDIO compatibility.
   - ✅ **Solution:** Make HTTP mode optional via CLI flags or env vars.