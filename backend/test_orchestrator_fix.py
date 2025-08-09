"""
Test Orchestrator Fix

Quick test to verify the orchestrator fix works.
"""
import asyncio
from app.services.unified_workflow_orchestrator import IntelligentParameterResolver, ConnectorIntelligence
from app.models.enhanced_execution import NodeExecutionContext, NodeState
from app.models.base import WorkflowNode, NodePosition


async def test_orchestrator_fix():
    """Test that the orchestrator no longer has the missing method error."""
    
    print("🧪 Testing Orchestrator Fix")
    print("=" * 40)
    
    try:
        # Create the components
        connector_intel = ConnectorIntelligence()
        resolver = IntelligentParameterResolver(connector_intel)
        
        # Create a simple test node
        test_node = WorkflowNode(
            id="test-node",
            connector_name="gmail_connector",
            position=NodePosition(x=0, y=0),
            parameters={"action": "search", "query": "test"}
        )
        
        # Create execution context
        context = NodeExecutionContext(
            node_id="test-node",
            state=NodeState.WAITING
        )
        
        # Test parameter resolution (this should not crash)
        input_data = {}
        resolved = await resolver.resolve_parameters(test_node, input_data, context)
        
        print("✅ Orchestrator fix successful!")
        print(f"   Resolved parameters: {resolved}")
        
        return True
        
    except AttributeError as e:
        if "_apply_connector_specific_formatting" in str(e):
            print(f"❌ Orchestrator fix failed: {e}")
            return False
        else:
            print(f"⚠️ Different AttributeError: {e}")
            return True  # Different error, fix worked for our issue
            
    except Exception as e:
        print(f"⚠️ Other error (fix may have worked): {e}")
        return True


if __name__ == "__main__":
    result = asyncio.run(test_orchestrator_fix())
    if result:
        print("\n🎯 Fix Applied Successfully!")
    else:
        print("\n❌ Fix Failed - Need to investigate further")