#!/usr/bin/env python3
"""
Fix user_id references in executions API.
"""

# Read the file
with open('app/api/executions.py', 'r') as f:
    content = f.read()

# Replace all instances
content = content.replace('current_user["id"]', 'current_user["user_id"]')

# Write back
with open('app/api/executions.py', 'w') as f:
    f.write(content)

print("Fixed user_id references in executions API")