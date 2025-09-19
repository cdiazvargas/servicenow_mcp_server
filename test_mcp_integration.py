#!/usr/bin/env python3
"""
Comprehensive Test Script for ServiceNow MCP Server
Tests the full integration flow before connecting to OI
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add color output for better readability
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

def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_info(message: str):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def print_header(message: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}🧪 {message}{Colors.END}")

class MCPServerTester:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.server_process: Optional[subprocess.Popen] = None
        
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        print_header("ServiceNow MCP Server Integration Test Suite")
        print("This will verify your server is ready for OI integration\n")
        
        # Test 1: Environment Check
        if not await self.test_environment():
            return False
            
        # Test 2: Configuration Check  
        if not await self.test_configuration():
            return False
            
        # Test 3: Server Startup
        if not await self.test_server_startup():
            return False
            
        # Test 4: MCP Protocol Tests
        if not await self.test_mcp_protocol():
            return False
            
        # Test 5: ServiceNow Integration
        if not await self.test_servicenow_integration():
            return False
            
        # Test 6: Tool Functionality
        if not await self.test_tools():
            return False
            
        print_header("🎉 All Tests Passed!")
        print("Your ServiceNow MCP Server is ready for OI integration!")
        return True
    
    async def test_environment(self) -> bool:
        """Test environment setup"""
        print_header("Testing Environment Setup")
        
        # Check Python version
        python_version = sys.version_info
        if python_version >= (3, 9):
            print_success(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
        else:
            print_error(f"Python {python_version.major}.{python_version.minor} is too old. Requires Python 3.9+")
            return False
            
        # Check virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print_success("Virtual environment is active")
        else:
            print_warning("Virtual environment not detected. Recommended to use venv.")
            
        # Check .env file
        env_file = self.project_root / ".env"
        if env_file.exists():
            print_success(f".env file found: {env_file}")
        else:
            print_error(".env file not found. Please create one with your ServiceNow credentials.")
            return False
            
        # Check required packages
        try:
            import mcp
            import httpx
            import structlog
            import pydantic
            print_success("All required packages are installed")
        except ImportError as e:
            print_error(f"Missing required package: {e}")
            print_info("Run: pip install -r requirements.txt")
            return False
            
        return True
    
    async def test_configuration(self) -> bool:
        """Test configuration loading"""
        print_header("Testing Configuration")
        
        try:
            # Test environment variable loading
            from servicenow_mcp_server.config import load_settings
            
            settings = load_settings()
            print_success("Configuration loaded successfully")
            
            # Validate required settings
            if settings.servicenow_instance_url:
                print_success(f"ServiceNow URL: {settings.servicenow_instance_url}")
            else:
                print_error("ServiceNow instance URL not configured")
                return False
                
            auth_method = settings.auth_method
            print_success(f"Authentication method: {auth_method.value}")
            
            if auth_method.value == "oauth":
                if settings.servicenow_client_id and settings.servicenow_client_secret:
                    print_success("OAuth credentials configured")
                else:
                    print_error("OAuth credentials incomplete")
                    return False
            elif auth_method.value == "jwt":
                if settings.jwt_secret_key:
                    print_success("JWT secret key configured")
                else:
                    print_error("JWT secret key not configured")
                    return False
                    
            print_success(f"Log level: {settings.log_level.value}")
            return True
            
        except Exception as e:
            print_error(f"Configuration test failed: {e}")
            return False
    
    async def test_server_startup(self) -> bool:
        """Test server can start"""
        print_header("Testing Server Startup")
        
        try:
            # Start server as subprocess
            self.server_process = subprocess.Popen(
                [sys.executable, "-m", "servicenow_mcp_server.main"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.project_root
            )
            
            # Give server time to start
            await asyncio.sleep(2)
            
            if self.server_process.poll() is None:
                print_success("Server started successfully")
                return True
            else:
                stderr_output = self.server_process.stderr.read()
                print_error(f"Server failed to start: {stderr_output}")
                return False
                
        except Exception as e:
            print_error(f"Server startup test failed: {e}")
            return False
    
    async def test_mcp_protocol(self) -> bool:
        """Test MCP protocol communication"""
        print_header("Testing MCP Protocol")
        
        if not self.server_process:
            print_error("Server not running")
            return False
            
        try:
            # Test initialization
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
            
            print_info("Sending initialization request...")
            self.server_process.stdin.write(json.dumps(init_request) + "\n")
            self.server_process.stdin.flush()
            
            # Read response with timeout
            response_line = await asyncio.wait_for(
                asyncio.to_thread(self.server_process.stdout.readline),
                timeout=10.0
            )
            
            if response_line:
                response = json.loads(response_line.strip())
                if "result" in response:
                    print_success("Server initialization successful")
                    return True
                else:
                    print_error(f"Initialization failed: {response}")
                    return False
            else:
                print_error("No response from server")
                return False
                
        except asyncio.TimeoutError:
            print_error("Server response timeout")
            return False
        except Exception as e:
            print_error(f"MCP protocol test failed: {e}")
            return False
    
    async def test_servicenow_integration(self) -> bool:
        """Test ServiceNow API connectivity"""
        print_header("Testing ServiceNow Integration")
        
        try:
            # This would require actual ServiceNow credentials
            # For now, we'll test the client initialization
            from servicenow_mcp_server.config import load_settings
            from servicenow_mcp_server.auth import AuthenticationManager
            from servicenow_mcp_server.servicenow_client import ServiceNowKnowledgeClient
            
            settings = load_settings()
            config = settings.to_servicenow_config()
            
            auth_manager = AuthenticationManager(config)
            client = ServiceNowKnowledgeClient(config, auth_manager)
            
            print_success("ServiceNow client initialized")
            
            # Clean up
            await client.close()
            
            print_warning("ServiceNow connectivity test requires valid credentials")
            print_info("Manual test: Try authenticating with real credentials later")
            
            return True
            
        except Exception as e:
            print_error(f"ServiceNow integration test failed: {e}")
            return False
    
    async def test_tools(self) -> bool:
        """Test MCP tools availability"""
        print_header("Testing MCP Tools")
        
        if not self.server_process:
            print_error("Server not running")
            return False
            
        try:
            # Test tools listing
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            }
            
            print_info("Requesting available tools...")
            self.server_process.stdin.write(json.dumps(tools_request) + "\n")
            self.server_process.stdin.flush()
            
            response_line = await asyncio.wait_for(
                asyncio.to_thread(self.server_process.stdout.readline),
                timeout=10.0
            )
            
            if response_line:
                response = json.loads(response_line.strip())
                if "result" in response and "tools" in response["result"]:
                    tools = response["result"]["tools"]
                    print_success(f"Found {len(tools)} available tools:")
                    
                    expected_tools = [
                        "authenticate_user",
                        "search_knowledge", 
                        "get_article",
                        "get_user_context",
                        "clear_user_session"
                    ]
                    
                    available_tools = [tool["name"] for tool in tools]
                    
                    for expected_tool in expected_tools:
                        if expected_tool in available_tools:
                            print_success(f"  ✓ {expected_tool}")
                        else:
                            print_error(f"  ✗ {expected_tool} - Missing!")
                            return False
                            
                    return True
                else:
                    print_error("Invalid tools response")
                    return False
            else:
                print_error("No tools response")
                return False
                
        except Exception as e:
            print_error(f"Tools test failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up test resources"""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
            print_info("Server process terminated")

async def main():
    """Main test runner"""
    tester = MCPServerTester()
    
    try:
        success = await tester.run_all_tests()
        
        if success:
            print_header("🚀 Integration Ready!")
            print("\nYour ServiceNow MCP Server is ready for OI integration!")
            print("\nNext steps:")
            print("1. Share the MCP configuration with your OI administrators")
            print("2. Test with real ServiceNow credentials")
            print("3. Monitor logs when OI connects")
            
            # Generate configuration for OI team
            print_header("Configuration for OI Team")
            config_template = {
                "mcpServers": {
                    "servicenow-knowledge": {
                        "command": "python",
                        "args": ["-m", "servicenow_mcp_server.main"],
                        "cwd": str(Path.cwd()),
                        "env": {
                            "SERVICENOW_INSTANCE_URL": "https://your-company.service-now.com",
                            "SERVICENOW_CLIENT_ID": "your-oauth-client-id", 
                            "SERVICENOW_CLIENT_SECRET": "your-oauth-client-secret",
                            "LOG_LEVEL": "info",
                            "LOG_FORMAT": "json"
                        }
                    }
                }
            }
            print(json.dumps(config_template, indent=2))
            
        else:
            print_error("Tests failed. Please fix issues before OI integration.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print_info("\nTest interrupted by user")
    except Exception as e:
        print_error(f"Test suite failed: {e}")
        sys.exit(1)
    finally:
        tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())