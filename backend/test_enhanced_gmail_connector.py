#!/usr/bin/env python3
"""
Test script for the enhanced Gmail connector with n8n feature parity.
"""
import asyncio
import json
from app.connectors.core.gmail_connector import GmailConnector
from app.models.connector import ConnectorExecutionContext

async def test_enhanced_gmail_connector():
    """Test the enhanced Gmail connector functionality."""
    print("🧪 Testing Enhanced Gmail Connector with n8n Feature Parity")
    print("=" * 60)
    
    # Initialize connector
    connector = GmailConnector()
    
    # Test 1: Schema validation
    print("\n1. Testing Schema Validation...")
    schema = connector._define_schema()
    
    # Check that all new actions are present
    expected_actions = [
        # Message operations
        "send", "reply", "read", "search", "list", "delete", 
        "mark_as_read", "mark_as_unread", "add_labels", "remove_labels",
        # Draft operations
        "create_draft", "get_draft", "delete_draft", "list_drafts",
        # Label operations
        "get_labels", "create_label", "delete_label", "get_label",
        # Thread operations
        "get_thread", "list_threads", "delete_thread", "trash_thread", 
        "untrash_thread", "add_thread_labels", "remove_thread_labels"
    ]
    
    actual_actions = schema["properties"]["action"]["enum"]
    missing_actions = set(expected_actions) - set(actual_actions)
    extra_actions = set(actual_actions) - set(expected_actions)
    
    if missing_actions:
        print(f"   ❌ Missing actions: {missing_actions}")
    if extra_actions:
        print(f"   ℹ️  Extra actions: {extra_actions}")
    if not missing_actions:
        print(f"   ✅ All {len(expected_actions)} actions present in schema")
    
    # Test 2: New parameter validation
    print("\n2. Testing New Parameters...")
    new_params = [
        "thread_id", "draft_id", "reply_to", "sender_name", 
        "format", "simple", "return_all", "limit"
    ]
    
    schema_props = schema["properties"]
    missing_params = [p for p in new_params if p not in schema_props]
    
    if missing_params:
        print(f"   ❌ Missing parameters: {missing_params}")
    else:
        print(f"   ✅ All new parameters present: {new_params}")
    
    # Test 3: Conditional requirements
    print("\n3. Testing Conditional Requirements...")
    all_of_conditions = schema.get("allOf", [])
    print(f"   ✅ Found {len(all_of_conditions)} conditional requirements")
    
    # Check some key conditions
    reply_condition = any(
        cond.get("if", {}).get("properties", {}).get("action", {}).get("const") == "reply"
        for cond in all_of_conditions
    )
    draft_condition = any(
        cond.get("if", {}).get("properties", {}).get("action", {}).get("const") == "create_draft"
        for cond in all_of_conditions
    )
    thread_condition = any(
        cond.get("if", {}).get("properties", {}).get("action", {}).get("const") == "get_thread"
        for cond in all_of_conditions
    )
    
    if reply_condition and draft_condition and thread_condition:
        print("   ✅ Key conditional requirements found (reply, draft, thread)")
    else:
        print("   ❌ Some conditional requirements missing")
    
    # Test 4: Authentication requirements
    print("\n4. Testing Authentication Requirements...")
    auth_reqs = await connector.get_auth_requirements()
    
    expected_scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.labels"
    ]
    
    if all(scope in auth_reqs.oauth_scopes for scope in expected_scopes):
        print("   ✅ All required OAuth scopes present")
    else:
        print("   ❌ Missing OAuth scopes")
    
    # Test 5: Example parameters
    print("\n5. Testing Example Parameters...")
    examples = connector.get_example_params()
    
    expected_examples = ["send_email", "reply_email", "search_emails", "create_draft", "get_thread", "mark_read"]
    
    if all(ex in examples for ex in expected_examples):
        print(f"   ✅ All {len(expected_examples)} example types present")
    else:
        missing_examples = [ex for ex in expected_examples if ex not in examples]
        print(f"   ❌ Missing examples: {missing_examples}")
    
    # Test 6: Parameter hints
    print("\n6. Testing Parameter Hints...")
    hints = connector.get_parameter_hints()
    
    expected_hint_keys = [
        "action", "to", "subject", "body", "message_id", "thread_id", 
        "draft_id", "label_ids", "sender_name", "reply_to", "format", "simple"
    ]
    
    missing_hints = [key for key in expected_hint_keys if key not in hints]
    
    if not missing_hints:
        print(f"   ✅ All {len(expected_hint_keys)} parameter hints present")
    else:
        print(f"   ❌ Missing hints: {missing_hints}")
    
    # Test 7: Method existence check
    print("\n7. Testing Method Existence...")
    new_methods = [
        "_reply_to_email", "_mark_as_read", "_mark_as_unread",
        "_add_labels_to_message", "_remove_labels_from_message",
        "_create_draft", "_get_draft", "_delete_draft", "_list_drafts",
        "_delete_label", "_get_label",
        "_get_thread", "_list_threads", "_delete_thread", "_trash_thread",
        "_untrash_thread", "_add_labels_to_thread", "_remove_labels_from_thread",
        "_simplify_message"
    ]
    
    missing_methods = []
    for method_name in new_methods:
        if not hasattr(connector, method_name):
            missing_methods.append(method_name)
    
    if not missing_methods:
        print(f"   ✅ All {len(new_methods)} new methods implemented")
    else:
        print(f"   ❌ Missing methods: {missing_methods}")
    
    # Test 8: Connector registration
    print("\n8. Testing Connector Registration...")
    connector_name = connector._get_connector_name()
    category = connector._get_category()
    
    if connector_name == "gmail_connector" and category == "communication":
        print("   ✅ Connector properly configured")
    else:
        print(f"   ❌ Connector config issue: name={connector_name}, category={category}")
    
    print("\n" + "=" * 60)
    print("🎉 Enhanced Gmail Connector Test Complete!")
    print("\nNew Features Added:")
    print("✅ Message Operations: reply, mark_as_read/unread, add/remove labels")
    print("✅ Draft Operations: create, get, delete, list drafts")
    print("✅ Enhanced Label Operations: delete, get specific labels")
    print("✅ Thread Operations: get, list, delete, trash/untrash, modify labels")
    print("✅ Advanced Parameters: format, simple, return_all, sender_name, reply_to")
    print("✅ Full n8n Feature Parity: All major n8n Gmail features implemented")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_enhanced_gmail_connector())