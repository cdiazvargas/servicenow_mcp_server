# ServiceNow Knowledge Management Roles

This document outlines the correct ServiceNow roles for knowledge management functionality.

## Standard ServiceNow Knowledge Management Roles

### Core Knowledge Roles

| Role | Purpose | Capabilities |
|------|---------|-------------|
| `knowledge` | Basic knowledge access | View published knowledge articles |
| `knowledge_contributor` | Content creation | Create, edit, and submit articles for approval |
| `knowledge_manager` | Knowledge base management | Manage knowledge bases, categories, and approve articles |
| `knowledge_admin` | Full administration | Full knowledge management capabilities, configure knowledge system |

### Additional Roles (Common in Enterprise)

| Role | Purpose | Capabilities |
|------|---------|-------------|
| `employee` | Basic employee access | General employee permissions |
| `manager` | Management access | Manager-level permissions and access |
| `admin` | System administration | Full system administration |
| `itil` | ITIL process access | Access to ITIL processes and procedures |

## Role-Based Article Access

### Public Articles
- **No roles required** - Accessible to all authenticated users
- **Field**: `roles` field is empty or NULL

### Role-Restricted Articles
- **Specific roles required** - Only users with matching roles can access
- **Field**: `roles` field contains comma-separated role names

## Updated Implementation

### Before (Incorrect)
```javascript
// ❌ These roles don't exist in standard ServiceNow
roles: ["knowledge_reader", "knowledge_admin"]
```

### After (Correct)
```javascript
// ✅ Using standard ServiceNow roles
roles: ["knowledge", "knowledge_admin"]
```

## Common Role Combinations

### Regular Employee
```json
{
  "roles": ["employee", "knowledge"]
}
```

### Knowledge Contributor
```json
{
  "roles": ["employee", "knowledge", "knowledge_contributor"]
}
```

### Knowledge Manager
```json
{
  "roles": ["employee", "knowledge", "knowledge_manager"]
}
```

### Knowledge Administrator
```json
{
  "roles": ["employee", "knowledge", "knowledge_admin"]
}
```

## Testing Roles

For testing purposes, the following roles are used:

- `employee` - Basic employee permissions
- `knowledge` - Basic knowledge article access
- `manager` - Manager-level access for testing role-based filtering
- `admin` - Administrative access for testing privileged operations

## Migration Notes

### Changed Roles
- `knowledge_reader` → `knowledge` (standard ServiceNow role)
- `knowledge_admin` → `knowledge_admin` (already correct)

### Files Updated
- `servicenow_mcp_server/auth.py`
- `tests/conftest.py`
- `tests/unit/test_search_functionality.py`
- Documentation files (to be updated)

## Validation

To verify roles are working correctly:

1. **Check ServiceNow Instance**: Verify these roles exist in your ServiceNow instance
2. **Test Role Assignment**: Ensure users have appropriate roles assigned
3. **Test Article Access**: Verify role-based filtering works correctly
4. **Review Logs**: Check authentication logs for role validation

## References

- [ServiceNow Knowledge Management Roles Documentation](https://docs.servicenow.com/bundle/washingtondc-servicenow-platform/page/product/knowledge-management/reference/r_KnowledgeRoles.html)
- [ServiceNow Role-Based Access Control](https://docs.servicenow.com/bundle/washingtondc-platform-administration/page/administer/roles/concept/c_Roles.html)
