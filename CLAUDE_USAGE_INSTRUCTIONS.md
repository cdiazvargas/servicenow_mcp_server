# 🤖 How to Use ServiceNow with Claude Desktop

Your ServiceNow MCP server is working perfectly! Here's how to use it with Claude Desktop.

## 🔑 Authentication Instructions

When Claude asks for ServiceNow credentials, you have **three options**:

### Option 1: JWT Token (Recommended - Most Secure)
If your company has JWT integration:
1. **Method**: Use `jwt_token` in authentication call
2. **Token**: Your JWT token from the existing corporate auth system
3. **Benefits**: Single sign-on, role inheritance, audit trail

**Example JWT payload:**
```json
{
  "sub": "user-sys-id",
  "username": "user.name", 
  "roles": ["employee", "knowledge_reader"],
  "iat": 1640995200,
  "exp": 1641081600,
  "iss": "your-company"
}
```

### Option 2: OAuth Token (Service Account)
For system-level access:
1. **Username**: Enter `oauth_token`
2. **Password**: Enter your OAuth bearer token
3. **Use Case**: Service accounts, system integrations

### Option 3: OAuth Credentials (Individual User)
For direct user authentication:
1. **Username**: Your ServiceNow username
2. **Password**: Your ServiceNow password
3. **Use Case**: Individual user access, development/testing

## 💬 Example Conversations

### Getting Started
**You**: "What ServiceNow tools do you have available?"
**Claude**: Lists the 5 tools and explains authentication options.

### JWT Authentication Flow
**You**: "Help me find our company's vacation policy in ServiceNow"
**Claude**: Will request JWT token, then search the knowledge base with your role-based access.

### OAuth Authentication Flow
**You**: "Search ServiceNow for password requirements"
**Claude**: Will prompt for OAuth credentials, then search based on your permissions.

### Specific Queries
**You**: "What are the steps to submit an expense report?"
**Claude**: Searches and returns synthesized step-by-step procedures from your knowledge base.

## 🎯 What Works Now

✅ **JWT-First Authentication**: Primary auth method with role inheritance  
✅ **OAuth Fallback**: Works with existing OAuth tokens and credentials  
✅ **Tool Discovery**: Claude can see all 5 ServiceNow tools  
✅ **Knowledge API**: Full access to your ServiceNow knowledge base  
✅ **MCP Protocol**: Complete compliance with Claude Desktop  
✅ **Role-Based Access**: Automatic enforcement of ServiceNow permissions  

## 🔄 Authentication Workflow

### JWT Flow (Recommended)
1. **Ask a ServiceNow question** to Claude
2. **Claude prompts for JWT token** 
3. **Provide JWT token** from your corporate auth system
4. **Claude authenticates and searches** your knowledge base
5. **Role-based access** is automatically enforced based on JWT claims

### OAuth Flow (Fallback)
1. **Ask a ServiceNow question** to Claude
2. **Claude prompts for credentials**
3. **Choose OAuth method** (token or username/password)
4. **Claude authenticates with ServiceNow** directly
5. **Search with ServiceNow permissions** applied

## 🔧 Advanced Features

### Smart Knowledge Synthesis
- **Multi-article responses**: Combines information from multiple knowledge articles
- **Step-by-step procedures**: Extracts and formats procedural information
- **Follow-up suggestions**: Provides contextual next questions
- **Related topics**: Suggests additional areas to explore

### Session Management
- **Automatic session handling**: No need to re-authenticate for follow-up questions
- **Session expiry**: Graceful handling when tokens expire
- **Context preservation**: Maintains conversation context across requests

### Error Handling
- **Helpful error messages**: Clear guidance when authentication fails
- **Fallback options**: Alternative authentication methods when primary fails
- **Retry mechanisms**: Automatic retry for transient network issues

## 🎪 Real-World Examples

### HR Policy Questions
**You**: "What's our company's maternity leave policy?"
**Claude**: 
- Authenticates with your JWT token
- Searches HR knowledge articles
- Returns comprehensive policy with procedures
- Suggests related topics (paternity leave, FMLA, etc.)

### IT Support Requests
**You**: "How do I set up two-factor authentication?"
**Claude**:
- Uses your IT role permissions
- Finds technical documentation
- Provides step-by-step setup instructions
- Links to original ServiceNow articles

### Manager-Level Queries
**You**: "What are the disciplinary procedures for employees?"
**Claude**:
- Validates manager role in JWT
- Accesses management-only knowledge articles
- Returns sensitive HR procedures
- Maintains audit trail in ServiceNow

## 🚨 Troubleshooting

### JWT Token Issues
```
Error: "JWT token verification failed"
Solution: Check token format and ensure JWT_SECRET_KEY matches
```

### OAuth Authentication Problems
```
Error: "OAuth authentication failed"
Solution: Verify ServiceNow credentials and instance URL
```

### Permission Denied
```
Error: "Access denied to knowledge article"
Solution: Check user roles in ServiceNow - may need additional permissions
```

### No Results Found
```
Response: "No relevant knowledge articles found"
Solution: Try different search terms or check if articles are published
```

## 🎉 You're Ready!

Your ServiceNow MCP server is fully operational with:

- **🔐 Multi-method authentication** (JWT primary, OAuth fallback)
- **📚 Comprehensive knowledge search** with role-based access
- **🤖 Intelligent response synthesis** from multiple articles
- **⚡ High-performance async operations** for fast responses
- **🛡️ Enterprise security** with proper audit trails

Start asking ServiceNow questions in Claude Desktop - your corporate knowledge base is now available through natural language conversations!
