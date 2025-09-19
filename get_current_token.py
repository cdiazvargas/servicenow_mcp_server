#!/usr/bin/env python3
"""
Get a current OAuth token for Claude Desktop usage
"""

import asyncio
import os
import httpx
from dotenv import load_dotenv

async def get_fresh_token():
    """Get a fresh OAuth token"""
    load_dotenv()
    
    instance_url = os.getenv("SERVICENOW_INSTANCE_URL")
    client_id = os.getenv("SERVICENOW_CLIENT_ID")
    client_secret = os.getenv("SERVICENOW_CLIENT_SECRET")
    
    oauth_url = f"{instance_url.rstrip('/')}/oauth_token.do"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            oauth_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30.0
        )
        
        if response.status_code == 200:
            token_data = response.json()
            return token_data["access_token"]
        else:
            raise Exception(f"OAuth failed: {response.status_code}")

if __name__ == "__main__":
    token = asyncio.run(get_fresh_token())
    print(f"🔑 Current OAuth Token (valid for 30 minutes):")
    print(f"{token}")
    print(f"\n📋 For Claude Desktop, when prompted for credentials, use:")
    print(f"Username: oauth_token")
    print(f"Password: {token}")
