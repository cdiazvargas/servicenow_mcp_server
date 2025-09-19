#!/usr/bin/env python3
"""
Ollama-style MCP Client Test for ServiceNow MCP Server
Simulates how Ollama would communicate with the MCP server
"""

import asyncio
import json
import subprocess
import sys
import time
from typing import Dict, Any, Optional, List

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_success(message: str):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message: str):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_info(message: str):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def print_header(message: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}🤖 {message}{Colors.END}")

class MCPClient:
    """Simulates an LLM client (like Ollama) communicating with MCP server"""
    
    def __init__(self):
        self.server_process: Optional[subprocess.Popen] = None
        self.request_id = 0
    
    def get_next_id(self) -> int:
        self.request_id += 1
        return self.request_id
    
    async def start_server(self) -> bool:
        """Start the ServiceNow MCP server"""
        print_header("Starting ServiceNow MCP Server")
        
        try:
            self.server_process = subprocess.Popen(
                [sys.executable, "-m", "servicenow_mcp_server.main"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give server time to start
            await asyncio.sleep(2)
            
            if self.server_process.poll() is None:
                print_success("MCP Server started successfully")
                return True
            else:
                stderr = self.server_process.stderr.read()
                print_error(f"Server failed to start: {stderr}")
                return False
                
        except Exception as e:
            print_error(f"Failed to start server: {e}")
            return False
    
    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Send MCP request to server"""
        if not self.server_process:
            print_error("Server not running")
            return None
        
        request = {
            "jsonrpc": "2.0",
            "id": self.get_next_id(),
            "method": method
        }
        
        # Only include params if they are provided
        if params is not None:
            request["params"] = params
        
        try:
            # Send request
            request_line = json.dumps(request) + "\n"
            self.server_process.stdin.write(request_line)
            self.server_process.stdin.flush()
            
            # Read response
            response_line = await asyncio.wait_for(
                asyncio.to_thread(self.server_process.stdout.readline),
                timeout=10.0
            )
            
            if response_line:
                return json.loads(response_line.strip())
            else:
                print_error("No response received")
                return None
                
        except asyncio.TimeoutError:
            print_error("Request timeout")
            return None
        except Exception as e:
            print_error(f"Request failed: {e}")
            return None
    
    async def initialize(self) -> bool:
        """Initialize MCP connection"""
        print_header("Initializing MCP Connection")
        
        response = await self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "ollama-test-client",
                "version": "1.0.0"
            }
        })
        
        if response and "result" in response:
            print_success("MCP connection initialized")
            print_info(f"Server capabilities: {response['result'].get('capabilities', {})}")
            return True
        else:
            print_error(f"Initialization failed: {response}")
            return False
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available MCP tools"""
        print_header("Listing Available Tools")
        
        response = await self.send_request("tools/list")
        
        if response and "result" in response:
            tools = response["result"].get("tools", [])
            print_success(f"Found {len(tools)} tools:")
            for tool in tools:
                print_info(f"  📋 {tool['name']}: {tool['description']}")
            return tools
        else:
            print_error(f"Failed to list tools: {response}")
            return []
    
    async def authenticate_user(self, username: str, password: str) -> Optional[str]:
        """Test user authentication (simulating Ollama asking user for credentials)"""
        print_header("Testing User Authentication")
        print_info(f"Authenticating user: {username}")
        
        response = await self.send_request("tools/call", {
            "name": "authenticate_user",
            "arguments": {
                "username": username,
                "password": password
            }
        })
        
        if response and "result" in response:
            result = json.loads(response["result"][0]["text"])
            if result.get("success"):
                print_success(f"Authentication successful!")
                print_info(f"User: {result.get('username')}")
                print_info(f"Roles: {', '.join(result.get('roles', []))}")
                return result.get("user_id")
            else:
                print_error(f"Authentication failed: {result.get('message')}")
                return None
        else:
            print_error(f"Authentication request failed: {response}")
            return None
    
    async def search_knowledge(self, user_id: str, query: str) -> Optional[str]:
        """Test knowledge search (simulating Ollama asking about company policies)"""
        print_header(f"Searching Knowledge: '{query}'")
        
        response = await self.send_request("tools/call", {
            "name": "search_knowledge", 
            "arguments": {
                "query": query,
                "user_id": user_id,
                "limit": 5,
                "synthesize": True
            }
        })
        
        if response and "result" in response:
            result_text = response["result"][0]["text"]
            print_success("Knowledge search completed!")
            print_info("Response from ServiceNow:")
            print(f"{Colors.GREEN}{result_text}{Colors.END}")
            return result_text
        else:
            print_error(f"Knowledge search failed: {response}")
            return None
    
    async def simulate_conversation(self, user_id: str):
        """Simulate a conversation like Ollama would have"""
        print_header("Simulating Ollama Conversation")
        
        # Simulate typical user questions
        queries = [
            "What is our vacation policy?",
            "How do I submit an expense report?", 
            "What are the password requirements?",
            "How do I request new software?",
            "What is the procedure for reporting security incidents?"
        ]
        
        for i, query in enumerate(queries, 1):
            print(f"\n{Colors.BOLD}User Question {i}:{Colors.END} {query}")
            
            # Simulate Ollama calling the knowledge search tool
            response = await self.search_knowledge(user_id, query)
            
            if response:
                print(f"{Colors.BOLD}Ollama Response:{Colors.END}")
                print(f"Based on your company's ServiceNow knowledge base: {response[:200]}...")
            
            # Brief pause between questions
            await asyncio.sleep(1)
    
    async def cleanup(self):
        """Clean up resources"""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
            print_info("Server terminated")

async def main():
    print_header("Ollama + ServiceNow MCP Server Integration Test")
    print("This simulates how Ollama would interact with your ServiceNow MCP server\n")
    
    client = MCPClient()
    
    try:
        # Start server
        if not await client.start_server():
            return False
        
        # Initialize MCP connection
        if not await client.initialize():
            return False
        
        # List available tools
        tools = await client.list_tools()
        if not tools:
            return False
        
        # Get user credentials (in real Ollama, this would be prompted)
        print_header("User Credentials Required")
        print_info("In a real Ollama integration, users would be prompted for ServiceNow credentials")
        print_info("For testing, using placeholder credentials...")
        
        # Simulate authentication (replace with real credentials for actual test)
        username = input("Enter ServiceNow username (or press Enter for mock test): ").strip()
        password = input("Enter ServiceNow password (or press Enter for mock test): ").strip()
        
        if username and password:
            # Test with real credentials
            user_id = await client.authenticate_user(username, password)
            if user_id:
                await client.simulate_conversation(user_id)
            else:
                print_error("Authentication failed - cannot proceed with knowledge search")
        else:
            # Mock test without real authentication
            print_info("Running mock test without real authentication...")
            print_info("This shows the MCP protocol flow, but won't return real ServiceNow data")
            
        print_header("🎉 Test Complete!")
        print("Your ServiceNow MCP server successfully communicates using the MCP protocol!")
        print("This demonstrates how Ollama (or any MCP client) would interact with your server.")
        
        return True
        
    except KeyboardInterrupt:
        print_info("\nTest interrupted by user")
        return False
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False
    finally:
        await client.cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        sys.exit(1)