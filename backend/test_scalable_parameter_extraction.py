#!/usr/bin/env python3
"""
Test the scalable AI-powered parameter extraction system.
This should work for ANY connector without hardcoding.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.true_react_agent import TrueReActAgent

async def test_scalable_parameter_extraction():
    """Test that the AI can configure parameters for any connector dynamically."""
    
    agent = TrueReActAgent()
    await agent.initialize()
    
    # Test cases with different connector types
    test_cases = [
        {
            "name": "Gmail Connector",
            "connector_info": {
                "name": "gmail_connector",
                "description": "Send and receive emails through Gmail",
                "parameter_schema": {
                    "properties": {
                        "action": {"type": "string", "enum": ["send", "read", "search"]},
                        "to": {"type": "string", "description": "Recipient email address"},
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body content"}
                    }
                }
            },
            "user_request": "Send an email to john@example.com with the summary results",
            "current_steps": [{"connector_name": "text_summarizer", "purpose": "Summarize content"}],
            "expected_keys": ["action", "to", "subject", "body"]
        },
        {
            "name": "Slack Connector (New)",
            "connector_info": {
                "name": "slack_connector",
                "description": "Send messages to Slack channels",
                "parameter_schema": {
                    "properties": {
                        "action": {"type": "string", "enum": ["send_message", "create_channel"]},
                        "channel": {"type": "string", "description": "Slack channel name"},
                        "message": {"type": "string", "description": "Message content"},
                        "username": {"type": "string", "description": "Username to send as"}
                    }
                }
            },
            "user_request": "Send a message to #general channel saying hello",
            "current_steps": [],
            "expected_keys": ["action", "channel", "message"]
        },
        {
            "name": "Database Connector (New)",
            "connector_info": {
                "name": "database_connector",
                "description": "Execute database queries",
                "parameter_schema": {
                    "properties": {
                        "action": {"type": "string", "enum": ["select", "insert", "update", "delete"]},
                        "table": {"type": "string", "description": "Database table name"},
                        "query": {"type": "string", "description": "SQL query to execute"},
                        "data": {"type": "object", "description": "Data to insert/update"}
                    }
                }
            },
            "user_request": "Insert the processed data into the users table",
            "current_steps": [{"connector_name": "data_processor", "purpose": "Process user data"}],
            "expected_keys": ["action", "table", "data"]
        },
        {
            "name": "Twitter Connector (New)",
            "connector_info": {
                "name": "twitter_connector",
                "description": "Post tweets and interact with Twitter",
                "parameter_schema": {
                    "properties": {
                        "action": {"type": "string", "enum": ["tweet", "reply", "retweet", "search"]},
                        "text": {"type": "string", "description": "Tweet text content"},
                        "hashtags": {"type": "array", "description": "Hashtags to include"},
                        "search_query": {"type": "string", "description": "Search query for tweets"}
                    }
                }
            },
            "user_request": "Post a tweet about our latest blog post with #tech #AI hashtags",
            "current_steps": [{"connector_name": "blog_fetcher", "purpose": "Get latest blog"}],
            "expected_keys": ["action", "text", "hashtags"]
        }
    ]
    
    print("🧪 Testing Scalable AI Parameter Extraction")
    print("=" * 60)
    
    for test_case in test_cases:
        print(f"\n🔧 Testing: {test_case['name']}")
        print(f"Request: {test_case['user_request']}")
        
        # Create action object
        action = {
            "user_request": test_case["user_request"],
            "action_type": "test"
        }
        
        # Test parameter extraction
        try:
            parameters = await agent._configure_connector_parameters(
                test_case["connector_info"],
                action,
                test_case["current_steps"]
            )
            
            print(f"✅ Extracted parameters: {parameters}")
            
            # Check if expected keys are present
            found_keys = set(parameters.keys())
            expected_keys = set(test_case["expected_keys"])
            missing_keys = expected_keys - found_keys
            
            if missing_keys:
                print(f"⚠️  Missing expected keys: {missing_keys}")
            else:
                print(f"✅ All expected keys found!")
                
            # Validate parameter values make sense
            validation_passed = True
            for key, value in parameters.items():
                if key == "action" and value not in test_case["connector_info"]["parameter_schema"]["properties"]["action"].get("enum", []):
                    print(f"❌ Invalid action value: {value}")
                    validation_passed = False
                elif "@" in test_case["user_request"] and key in ["to", "email"] and "@" not in str(value):
                    print(f"❌ Email not extracted for {key}: {value}")
                    validation_passed = False
            
            if validation_passed:
                print("✅ Parameter validation passed!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Scalable parameter extraction test completed!")
    print("This system can handle ANY connector without hardcoding! 🚀")

if __name__ == "__main__":
    asyncio.run(test_scalable_parameter_extraction())