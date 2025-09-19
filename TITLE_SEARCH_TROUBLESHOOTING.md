# Title Search Troubleshooting Guide

## Issue: Title search not working

The title search functionality has been implemented but may not be working as expected. This guide helps troubleshoot the issue.

## Current Implementation

The system supports these search types:
- `sys_id` - Exact system ID match
- `number` - Exact article number match  
- `title_exact` - Exact title match
- `title_partial` - Partial title match
- `content` - Search in title and content (default)

## Debugging Steps

### 1. Enable Debug Logging

Set log level to DEBUG to see the actual ServiceNow queries being generated:

```bash
export LOG_LEVEL=debug
./start_mcp_server_with_env.sh
```

### 2. Test with Simple Cases First

Start with simple test cases:

```json
{
  "query": "handbook",
  "user_id": "your-user-id",
  "search_type": "title_partial"
}
```

### 3. Verify ServiceNow Field Names

The implementation assumes these ServiceNow field names:
- `short_description` - article title
- `text` - article content
- `number` - article number
- `sys_id` - system ID

Verify these in your ServiceNow instance at: `System Definition > Tables > Knowledge [kb_knowledge]`

### 4. Common Issues and Solutions

#### Issue: No results for title search
**Possible causes:**
1. **Wrong field name** - ServiceNow might use different field names
2. **Case sensitivity** - ServiceNow might be case-sensitive
3. **Special characters** - Titles with spaces/punctuation
4. **Permissions** - User doesn't have access to articles

**Solutions:**
```javascript
// Test in ServiceNow directly with these queries:
// For exact match:
short_description=Employee Handbook

// For partial match:
short_descriptionLIKE%handbook%

// Case insensitive:
short_descriptionLIKE%HANDBOOK%
```

#### Issue: Query syntax errors
**Check the ServiceNow logs for:**
- Invalid field names
- Malformed query syntax
- Permission errors

### 5. Alternative Query Formats to Try

If current implementation doesn't work, try these alternatives:

1. **Use CONTAINS operator:**
   ```
   short_descriptionCONTAINSEmployee Handbook
   ```

2. **Use quoted strings:**
   ```
   short_description="Employee Handbook"
   ```

3. **Case insensitive search:**
   ```
   short_descriptionLIKE%employee handbook%
   ```

### 6. Verify with ServiceNow REST API Explorer

1. Go to ServiceNow > System Web Services > REST API Explorer
2. Select Table API > GET multiple records
3. Table: `kb_knowledge`
4. Test query: `short_description=YourTestTitle`

### 7. Manual Testing

Create a test script to verify the queries:

```python
# Test the query generation
from servicenow_mcp_server.servicenow_client import ServiceNowKnowledgeClient
# ... (see test files for complete example)
```

## Current Query Formats

The system generates these query formats:

### Title Exact Search
```
workflow_state=published^short_description=Employee Handbook^(role_filters)
```

### Title Partial Search  
```
workflow_state=published^short_descriptionLIKE%handbook%^(role_filters)
```

## Next Steps

1. **Test with ServiceNow directly** - Verify queries work in ServiceNow
2. **Check ServiceNow version** - Different versions may have different syntax
3. **Verify permissions** - Ensure user can access knowledge articles
4. **Review ServiceNow logs** - Check for detailed error messages

## Known Working Alternatives

If the current implementation doesn't work, consider these proven approaches:

1. Use only LIKE queries with wildcards for all searches
2. Implement client-side filtering for exact matches
3. Use ServiceNow's full-text search capabilities
4. Combine multiple query approaches as fallbacks

## Getting Help

If issues persist:
1. Check ServiceNow documentation for your version
2. Test queries in ServiceNow REST API Explorer
3. Contact ServiceNow support for query syntax verification
4. Review ServiceNow system logs for detailed error messages
