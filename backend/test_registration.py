#!/usr/bin/env python3
"""
Test script to check connector registration.
"""
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.connectors.core.register import register_core_connectors
    from app.connectors.registry import get_connector_registry
    
    print('Registering core connectors...')
    result = register_core_connectors()
    print(f'Registration result: {result}')
    
    registry = get_connector_registry()
    print(f'Registry now has {registry.get_connector_count()} connectors')
    
    connectors = registry.list_connectors()
    print('Available connectors:')
    for conn in connectors:
        metadata = registry.get_metadata(conn)
        print(f'  - {conn}: {metadata.description[:80]}...')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()