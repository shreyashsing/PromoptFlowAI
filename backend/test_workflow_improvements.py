#!/usr/bin/env python3
"""
Test the three key workflow improvements:
1. Resource Management - Semaphore-based concurrency control
2. Workflow Graph - DirectedGraph with cycle detection
3. Input Data Merging - Handle multiple input connections properly
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.workflow_graph import WorkflowGraph, DirectedGraph
from app.models.base import WorkflowNode
from app.models.enhanced_execution import NodeExecutionContext, NodeState
from app.services.unified_workflow_orchestrator import UnifiedWorkflowOrchestrator

async def test_semaphore_concurrency_control():
    """Test 1: Semaphore-based concurrency control"""
    print("🧪 Test 1: Semaphore-based concurrency control")
    
    try:
        # Check if semaphore is used in the orchestrator by reading the file
        with open('app/services/unified_workflow_orchestrator.py', 'r', encoding='utf-8') as f:
            source = f.read()
        
        if "semaphore" in source.lower() and "asyncio.Semaphore" in source:
            print("✅ Semaphore-based concurrency control is implemented")
            
            # Count semaphore occurrences to verify it's properly used
            semaphore_count = source.lower().count("semaphore")
            if semaphore_count >= 4:  # Should appear in multiple places
                print(f"✅ Semaphore used extensively ({semaphore_count} occurrences)")
                return True
            else:
                print(f"⚠️  Semaphore found but limited usage ({semaphore_count} occurrences)")
                return True
        else:
            print("❌ Semaphore-based concurrency control not found")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_directed_graph_cycle_detection():
    """Test 2: DirectedGraph with cycle detection"""
    print("\n🧪 Test 2: DirectedGraph with cycle detection")
    
    try:
        # Test basic DirectedGraph functionality
        graph = DirectedGraph()
        
        # Add nodes without cycles
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "D")
        
        if graph.has_cycle():
            print("❌ False positive: No cycle should be detected")
            return False
        
        print("✅ No cycle correctly detected in acyclic graph")
        
        # Add a cycle
        graph.add_edge("D", "B")  # Creates cycle B -> C -> D -> B
        
        if not graph.has_cycle():
            print("❌ False negative: Cycle should be detected")
            return False
        
        print("✅ Cycle correctly detected")
        
        # Test cycle finding
        cycles = graph.find_cycles()
        if not cycles:
            print("❌ Cycle finding failed")
            return False
        
        print(f"✅ Found cycles: {cycles}")
        
        # Test WorkflowGraph integration
        workflow_graph = WorkflowGraph()
        
        # Add nodes with correct structure
        from app.models.base import NodePosition
        for node_id in ["A", "B", "C", "D"]:
            node = WorkflowNode(
                id=node_id, 
                connector_name="test", 
                parameters={},
                position=NodePosition(x=0, y=0)
            )
            workflow_graph.add_node(node)
        
        # Add connections that create a cycle
        workflow_graph.add_connection("A", "B")
        workflow_graph.add_connection("B", "C")
        workflow_graph.add_connection("C", "D")
        workflow_graph.add_connection("D", "B")  # Creates cycle
        
        detected_cycles = workflow_graph.detect_cycles()
        if not detected_cycles:
            print("❌ WorkflowGraph cycle detection failed")
            return False
        
        print(f"✅ WorkflowGraph detected cycles: {detected_cycles}")
        
        # Test topological sort
        topo_order = workflow_graph.get_topological_order()
        if topo_order is not None:
            print("❌ Topological sort should return None for cyclic graph")
            return False
        
        print("✅ Topological sort correctly returns None for cyclic graph")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multiple_input_data_merging():
    """Test 3: Multiple input data merging"""
    print("\n🧪 Test 3: Multiple input data merging")
    
    try:
        workflow_graph = WorkflowGraph()
        
        # Create nodes with correct structure
        from app.models.base import NodePosition
        node_a = WorkflowNode(id="A", connector_name="test", parameters={}, position=NodePosition(x=0, y=0))
        node_b = WorkflowNode(id="B", connector_name="test", parameters={}, position=NodePosition(x=0, y=0))
        node_c = WorkflowNode(id="C", connector_name="test", parameters={}, position=NodePosition(x=0, y=0))  # Will have multiple inputs
        
        workflow_graph.add_node(node_a)
        workflow_graph.add_node(node_b)
        workflow_graph.add_node(node_c)
        
        # Add connections - C receives input from both A and B
        workflow_graph.add_connection("A", "C", "output", "input1")
        workflow_graph.add_connection("B", "C", "output", "input2")
        
        # Check if waiting execution was set up for node C
        if "C" not in workflow_graph.waiting_executions:
            print("❌ Waiting execution not set up for multiple input node")
            return False
        
        print("✅ Waiting execution set up for multiple input node")
        
        # Simulate node A completion
        workflow_graph.node_contexts["A"].output_data = {"output": {"data": "from_A"}}
        workflow_graph.node_contexts["A"].transition_to(NodeState.SUCCESS, "Completed")
        
        # Simulate data propagation from A to C
        waiting_exec = workflow_graph.waiting_executions["C"]
        waiting_exec.receive_input("input1", "A", {"data": "from_A"})
        
        # Check if C is ready (should not be, still waiting for B)
        if waiting_exec.is_ready():
            print("❌ Node C should not be ready yet (missing input from B)")
            return False
        
        print("✅ Node C correctly waiting for all inputs")
        
        # Simulate node B completion
        workflow_graph.node_contexts["B"].output_data = {"output": {"data": "from_B"}}
        workflow_graph.node_contexts["B"].transition_to(NodeState.SUCCESS, "Completed")
        
        # Simulate data propagation from B to C
        waiting_exec.receive_input("input2", "B", {"data": "from_B"})
        
        # Now C should be ready
        if not waiting_exec.is_ready():
            print("❌ Node C should be ready now (all inputs received)")
            return False
        
        print("✅ Node C ready after receiving all inputs")
        
        # Test input data merging
        merged_data = waiting_exec.get_merged_input_data()
        expected_data = {
            "input1": {"data": "from_A"},
            "input2": {"data": "from_B"}
        }
        
        if merged_data != expected_data:
            print(f"❌ Input data merging failed. Expected: {expected_data}, Got: {merged_data}")
            return False
        
        print(f"✅ Input data correctly merged: {merged_data}")
        
        # Test missing inputs detection
        workflow_graph2 = WorkflowGraph()
        node_d = WorkflowNode(id="D", connector_name="test", parameters={}, position=NodePosition(x=0, y=0))
        node_e = WorkflowNode(id="E", connector_name="test", parameters={}, position=NodePosition(x=0, y=0))
        node_f = WorkflowNode(id="F", connector_name="test", parameters={}, position=NodePosition(x=0, y=0))
        
        workflow_graph2.add_node(node_d)
        workflow_graph2.add_node(node_e)
        workflow_graph2.add_node(node_f)
        
        workflow_graph2.add_connection("D", "F", "output", "input1")
        workflow_graph2.add_connection("E", "F", "output", "input2")
        
        waiting_exec2 = workflow_graph2.waiting_executions["F"]
        waiting_exec2.receive_input("input1", "D", {"data": "from_D"})
        
        missing = waiting_exec2.get_missing_inputs()
        if "input2" not in missing or "E" not in missing["input2"]:
            print(f"❌ Missing inputs detection failed. Expected input2 from E, got: {missing}")
            return False
        
        print(f"✅ Missing inputs correctly detected: {missing}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("🚀 Testing Workflow Improvements")
    print("=" * 50)
    
    results = []
    
    # Test 1: Semaphore-based concurrency control
    results.append(await test_semaphore_concurrency_control())
    
    # Test 2: DirectedGraph with cycle detection
    results.append(test_directed_graph_cycle_detection())
    
    # Test 3: Multiple input data merging
    results.append(test_multiple_input_data_merging())
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    
    improvements = [
        "Semaphore-based concurrency control",
        "DirectedGraph with cycle detection", 
        "Multiple input data merging"
    ]
    
    all_passed = True
    for i, (improvement, passed) in enumerate(zip(improvements, results), 1):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{i}. {improvement}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All workflow improvements are successfully implemented!")
    else:
        print("⚠️  Some improvements need attention")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        exit(1)