"""
Test Parameter Preservation Fix

This test reproduces and fixes the issue where modifying one parameter
in a workflow node resets all other parameters.
"""
import asyncio
import json
from typing import Dict, Any

def test_parameter_preservation_issue():
    """Demonstrate the parameter preservation issue."""
    
    print("🧪 Testing Parameter Preservation Issue")
    print("=" * 50)
    
    # Original Gmail connector parameters (complete set)
    original_params = {
        "action": "search",
        "query": "from:manager@company.com",
        "max_results": 10,
        "include_spam_trash": False,
        "label_ids": ["INBOX"],
        "format": "full"
    }
    
    print("\n1. Original Parameters:")
    print(json.dumps(original_params, indent=2))
    
    # User modifies just one parameter (e.g., changes max_results to 20)
    # This simulates what happens when user updates a single field
    modified_params = {
        "max_results": 20  # Only the modified field
    }
    
    print("\n2. User Modification (only changed field):")
    print(json.dumps(modified_params, indent=2))
    
    # Current behavior: Complete replacement (WRONG)
    current_behavior_result = modified_params.copy()
    
    print("\n3. Current Behavior (WRONG - loses other fields):")
    print(json.dumps(current_behavior_result, indent=2))
    
    # Correct behavior: Merge with original (CORRECT)
    correct_behavior_result = original_params.copy()
    correct_behavior_result.update(modified_params)
    
    print("\n4. Correct Behavior (preserves other fields):")
    print(json.dumps(correct_behavior_result, indent=2))
    
    # Validation check
    required_fields = ["action", "query"]  # Gmail connector required fields
    
    print("\n5. Validation Results:")
    
    # Check current behavior
    missing_in_current = [field for field in required_fields if field not in current_behavior_result]
    if missing_in_current:
        print(f"   ❌ Current behavior missing required fields: {missing_in_current}")
    else:
        print("   ✅ Current behavior has all required fields")
    
    # Check correct behavior
    missing_in_correct = [field for field in required_fields if field not in correct_behavior_result]
    if missing_in_correct:
        print(f"   ❌ Correct behavior missing required fields: {missing_in_correct}")
    else:
        print("   ✅ Correct behavior has all required fields")
    
    print(f"\n🎯 Parameter Preservation Test Complete!")
    
    return correct_behavior_result


def create_parameter_merge_function():
    """Create a function to properly merge parameters."""
    
    def merge_parameters(original: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge parameter updates with original parameters, preserving existing values.
        
        Args:
            original: Original parameter set
            updates: Parameter updates to apply
            
        Returns:
            Merged parameters with updates applied
        """
        merged = original.copy()
        merged.update(updates)
        return merged
    
    return merge_parameters


def test_parameter_merge_scenarios():
    """Test various parameter merge scenarios."""
    
    print("\n" + "=" * 50)
    print("🧪 Testing Parameter Merge Scenarios")
    print("=" * 50)
    
    merge_params = create_parameter_merge_function()
    
    # Scenario 1: Simple field update
    print("\n1. Simple Field Update:")
    original = {"action": "search", "query": "test", "max_results": 10}
    updates = {"max_results": 20}
    result = merge_params(original, updates)
    print(f"   Original: {original}")
    print(f"   Updates:  {updates}")
    print(f"   Result:   {result}")
    
    # Scenario 2: Adding new field
    print("\n2. Adding New Field:")
    original = {"action": "search", "query": "test"}
    updates = {"max_results": 15, "include_spam_trash": True}
    result = merge_params(original, updates)
    print(f"   Original: {original}")
    print(f"   Updates:  {updates}")
    print(f"   Result:   {result}")
    
    # Scenario 3: Updating multiple fields
    print("\n3. Updating Multiple Fields:")
    original = {"action": "search", "query": "old query", "max_results": 10, "format": "minimal"}
    updates = {"query": "new query", "format": "full"}
    result = merge_params(original, updates)
    print(f"   Original: {original}")
    print(f"   Updates:  {updates}")
    print(f"   Result:   {result}")
    
    # Scenario 4: Complex nested updates
    print("\n4. Complex Nested Updates:")
    original = {
        "action": "send",
        "to": "user@example.com",
        "subject": "Original Subject",
        "body": "Original body",
        "attachments": []
    }
    updates = {"subject": "Updated Subject", "body": "Updated body"}
    result = merge_params(original, updates)
    print(f"   Original: {json.dumps(original, indent=4)}")
    print(f"   Updates:  {json.dumps(updates, indent=4)}")
    print(f"   Result:   {json.dumps(result, indent=4)}")


if __name__ == "__main__":
    test_parameter_preservation_issue()
    test_parameter_merge_scenarios()