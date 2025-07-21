#!/usr/bin/env python3
"""Simple MCP client to test the server."""

import json
import subprocess
import sys
from typing import Any, Dict

def send_request(process: subprocess.Popen, request: Dict[str, Any]) -> Dict[str, Any]:
    """Send a JSON-RPC request to the MCP server."""
    request_json = json.dumps(request) + '\n'
    process.stdin.write(request_json.encode())
    process.stdin.flush()
    
    # Read response
    response_line = process.stdout.readline().decode().strip()
    return json.loads(response_line)

def main():
    # Start the MCP server
    cmd = [sys.executable, "-m", "src.mcp_server"]
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False
    )
    
    try:
        # Initialize the connection
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        print("Sending initialize request...")
        response = send_request(process, init_request)
        print(f"Initialize response: {json.dumps(response, indent=2)}")
        
        # List available tools
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        print("\nSending tools/list request...")
        response = send_request(process, tools_request)
        print(f"Tools response: {json.dumps(response, indent=2)}")
        
    except Exception as e:
        print(f"Error: {e}")
        stderr_output = process.stderr.read().decode()
        if stderr_output:
            print(f"Server stderr: {stderr_output}")
    finally:
        process.terminate()
        process.wait()

if __name__ == "__main__":
    main()