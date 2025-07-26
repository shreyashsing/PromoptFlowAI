#!/usr/bin/env python3
"""
Test script to check if the registry import works.
"""
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.connectors.registry import get_connector_registry
    print('Import successful')
    registry = get_connector_registry()
    print(f'Registry has {registry.get_connector_count()} connectors')
except Exception as e:
    print(f'Import failed: {e}')
    import traceback
    traceback.print_exc()