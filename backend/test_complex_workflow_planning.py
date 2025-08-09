"""
Test Complex Workflow Planning - N8N Level Complexity

This test verifies that the agent can handle complex, multi-step workflows
similar to what you'd build in n8n with 15+ connectors and complex logic.
"""
import asyncio
import logging
from app.services.true_react_agent import TrueReActAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_complex_youtube_digest_workflow():
    """Test the complex YouTube digest workflow with 15+ steps."""
    
    print("🧪 Testing Complex N8N-Level Workflow Planning")
    print("=" * 60)
    
    # Initialize the agent
    agent = TrueReActAgent()
    await agent.initialize()
    
    # The complex workflow request
    complex_request = """Every week, check the last 7 days' emails from Gmail with subject lines containing the word 'YouTube Report'. For each email, extract the YouTube video links mentioned. Download each video using YouTube connector and store them in a specific folder on Google Drive titled 'Weekly_Reports'. Then, extract the transcript of each video, summarize the content into a concise paragraph using a text summarizer, and log the video title, link, and summary into an Airtable base called 'Weekly YouTube Digest'. Finally, send me a compiled digest of all summaries for the week in an email with the subject 'Weekly YouTube Digest Summary' to shreyashbarca10@gmail.com."""
    
    print(f"📝 Complex Request:")
    print(f"   {complex_request[:100]}...")
    print()
    
    try:
        # Process the complex request
        result = await agent.process_user_request(complex_request, "test_user")
        
        if result.get("success"):
            plan = result.get("plan", {})
            
            print(f"✅ Plan Created Successfully")
            print(f"🧠 Enhanced Planning: {plan.get('enhanced_planning', False)}")
            print(f"📋 Summary: {plan.get('summary', 'N/A')}")
            print(f"🔗 Sequence: {plan.get('sequence_description', 'N/A')}")
            print(f"📊 Total Tasks: {len(plan.get('tasks', []))}")
            print(f"⏱️  Estimated Duration: {sum(task.get('estimated_duration', 5) for task in plan.get('tasks', []))}s")
            print()
            
            # Analyze the workflow complexity
            tasks = plan.get('tasks', [])
            connectors_used = set(task['suggested_tool'] for task in tasks)
            
            print(f"🔧 Connectors Used ({len(connectors_used)}):")
            for connector in sorted(connectors_used):
                count = sum(1 for task in tasks if task['suggested_tool'] == connector)
                print(f"   - {connector} ({count} times)")
            print()
            
            print(f"📋 Detailed Workflow Steps:")
            for i, task in enumerate(tasks, 1):
                deps = task.get('dependencies', [])
                deps_str = f" → depends on: {deps}" if deps else ""
                duration = task.get('estimated_duration', 5)
                print(f"   {i:2d}. {task['description']}")
                print(f"       Tool: {task['suggested_tool']} | Duration: {duration}s{deps_str}")
            print()
            
            # Analyze workflow characteristics
            print(f"📊 Workflow Analysis:")
            print(f"   - Complexity Level: {'High' if len(tasks) >= 10 else 'Medium' if len(tasks) >= 5 else 'Low'}")
            print(f"   - Parallel Opportunities: {len([t for t in tasks if not t.get('dependencies')])}")
            print(f"   - Sequential Chains: {len([t for t in tasks if t.get('dependencies')])}")
            print(f"   - Data Processing Steps: {len([t for t in tasks if 'process' in t.get('description', '').lower() or 'extract' in t.get('description', '').lower()])}")
            print(f"   - Storage Operations: {len([t for t in tasks if any(word in t.get('description', '').lower() for word in ['save', 'store', 'log'])])}")
            print()
            
            # Check if it meets n8n-level complexity
            n8n_criteria = {
                "Multiple Data Sources": len([t for t in tasks if any(word in t.get('description', '').lower() for word in ['gmail', 'email', 'fetch'])]) > 0,
                "Data Processing": len([t for t in tasks if any(word in t.get('description', '').lower() for word in ['extract', 'process', 'summarize'])]) > 0,
                "Multiple Storage": len([t for t in tasks if any(word in t.get('description', '').lower() for word in ['drive', 'airtable', 'store'])]) > 0,
                "Communication": len([t for t in tasks if any(word in t.get('description', '').lower() for word in ['send', 'email', 'notify'])]) > 0,
                "Complex Logic": len(tasks) >= 8,
                "Multiple Connectors": len(connectors_used) >= 4
            }
            
            print(f"🎯 N8N-Level Complexity Assessment:")
            for criterion, met in n8n_criteria.items():
                status = "✅" if met else "❌"
                print(f"   {status} {criterion}")
            
            complexity_score = sum(n8n_criteria.values()) / len(n8n_criteria) * 100
            print(f"   📈 Complexity Score: {complexity_score:.1f}%")
            
            if complexity_score >= 80:
                print(f"   🏆 EXCELLENT: Meets n8n-level complexity!")
            elif complexity_score >= 60:
                print(f"   👍 GOOD: Approaching n8n-level complexity")
            else:
                print(f"   ⚠️  NEEDS IMPROVEMENT: Below n8n-level complexity")
            
        else:
            print(f"❌ Plan Creation Failed: {result.get('error', 'Unknown error')}")
            print(f"   Message: {result.get('message', 'No message')}")
            
    except Exception as e:
        print(f"❌ Test Failed with Exception: {e}")
        import traceback
        traceback.print_exc()

async def test_workflow_scalability():
    """Test if the agent can handle multiple complex workflows."""
    
    print("\n" + "=" * 60)
    print("🔬 Testing Workflow Scalability")
    print("=" * 60)
    
    agent = TrueReActAgent()
    await agent.initialize()
    
    # Test multiple complex scenarios
    test_scenarios = [
        {
            "name": "E-commerce Analytics Pipeline",
            "request": "Daily, fetch sales data from Airtable, analyze trends using AI, create visualizations, save reports to Google Drive, update dashboard in Notion, and send summary to team via email."
        },
        {
            "name": "Content Moderation Workflow", 
            "request": "Monitor social media mentions, extract content, analyze sentiment, flag inappropriate content, log results in database, notify moderators, and generate weekly reports."
        },
        {
            "name": "Customer Support Automation",
            "request": "Check support emails, categorize by urgency, extract key information, search knowledge base, generate responses, log interactions in CRM, and escalate complex issues."
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🧪 Scenario {i}: {scenario['name']}")
        print("-" * 40)
        
        try:
            result = await agent.process_user_request(scenario['request'], f"test_user_{i}")
            
            if result.get("success"):
                plan = result.get("plan", {})
                tasks = plan.get('tasks', [])
                connectors = set(task['suggested_tool'] for task in tasks)
                
                print(f"   ✅ Success: {len(tasks)} steps, {len(connectors)} connectors")
                print(f"   🔗 Sequence: {plan.get('sequence_description', 'N/A')[:80]}...")
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown')}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")

async def main():
    """Run all complex workflow tests."""
    try:
        await test_complex_youtube_digest_workflow()
        await test_workflow_scalability()
        
        print("\n" + "=" * 60)
        print("🎉 COMPLEX WORKFLOW PLANNING TESTS COMPLETED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())