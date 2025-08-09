"""
Test Data Format Fix

This test identifies and fixes the data formatting issues between
Gmail and Google Sheets connectors.
"""
import json
from typing import Dict, Any, List


def test_data_format_issue():
    """Reproduce and fix the data format issue."""
    
    print("🧪 Testing Data Format Issue")
    print("=" * 50)
    
    # This is what Gmail connector is returning (correct format)
    gmail_output = {
        "result": [
            {
                "subject": "Amazon Job Opportunity - Software Development Engineer I",
                "from": "bpitplacementbatch2025@googlegroups.com", 
                "date": "2025-01-07T09:50:58.000Z",
                "snippet": "Dear Students, We are excited to share an excellent opportunity..."
            }
        ]
    }
    
    print("\n1. Gmail Connector Output (correct format):")
    print(json.dumps(gmail_output, indent=2))
    
    # This is what's being passed to Google Sheets (WRONG - stringified)
    stringified_data = str(gmail_output["result"])
    
    print("\n2. What's being passed to Google Sheets (WRONG):")
    print(f"Type: {type(stringified_data)}")
    print(f"Value: {stringified_data[:100]}...")
    
    # This is what Google Sheets expects for the values parameter
    expected_format = [
        ["Subject", "Sender", "Date", "Snippet"],
        [
            gmail_output["result"][0]["subject"],
            gmail_output["result"][0]["from"],
            gmail_output["result"][0]["date"],
            gmail_output["result"][0]["snippet"]
        ]
    ]
    
    print("\n3. What Google Sheets expects (correct format):")
    print(json.dumps(expected_format, indent=2))
    
    print(f"\n🎯 Data Format Issue Identified!")
    print("The issue is that data is being stringified instead of properly formatted as arrays.")


def create_data_formatter():
    """Create a data formatter to fix the issue."""
    
    def format_gmail_data_for_sheets(gmail_data: Dict[str, Any]) -> List[List[str]]:
        """
        Format Gmail connector output for Google Sheets values parameter.
        
        Args:
            gmail_data: Gmail connector output with 'result' array
            
        Returns:
            Properly formatted 2D array for Google Sheets
        """
        if not isinstance(gmail_data, dict) or "result" not in gmail_data:
            return [["No data available"]]
        
        emails = gmail_data["result"]
        if not isinstance(emails, list) or not emails:
            return [["No emails found"]]
        
        # Create header row
        formatted_data = [["Subject", "Sender", "Date", "Snippet"]]
        
        # Add email data rows
        for email in emails:
            if isinstance(email, dict):
                row = [
                    email.get("subject", ""),
                    email.get("from", ""),
                    email.get("date", ""),
                    email.get("snippet", "")
                ]
                formatted_data.append(row)
        
        return formatted_data
    
    return format_gmail_data_for_sheets


def test_data_formatter():
    """Test the data formatter function."""
    
    print("\n" + "=" * 50)
    print("🧪 Testing Data Formatter")
    print("=" * 50)
    
    formatter = create_data_formatter()
    
    # Test case 1: Normal Gmail data
    gmail_data = {
        "result": [
            {
                "subject": "Test Email 1",
                "from": "sender1@example.com",
                "date": "2025-01-07",
                "snippet": "This is test email 1"
            },
            {
                "subject": "Test Email 2", 
                "from": "sender2@example.com",
                "date": "2025-01-06",
                "snippet": "This is test email 2"
            }
        ]
    }
    
    formatted = formatter(gmail_data)
    
    print("\n1. Normal Gmail Data:")
    print("   Input:", json.dumps(gmail_data, indent=4))
    print("   Output:", json.dumps(formatted, indent=4))
    print(f"   ✅ Formatted as {len(formatted)} rows x {len(formatted[0])} columns")
    
    # Test case 2: Empty result
    empty_data = {"result": []}
    formatted_empty = formatter(empty_data)
    
    print("\n2. Empty Gmail Data:")
    print("   Input:", json.dumps(empty_data))
    print("   Output:", json.dumps(formatted_empty))
    
    # Test case 3: Invalid data
    invalid_data = {"invalid": "data"}
    formatted_invalid = formatter(invalid_data)
    
    print("\n3. Invalid Gmail Data:")
    print("   Input:", json.dumps(invalid_data))
    print("   Output:", json.dumps(formatted_invalid))


if __name__ == "__main__":
    test_data_format_issue()
    test_data_formatter()