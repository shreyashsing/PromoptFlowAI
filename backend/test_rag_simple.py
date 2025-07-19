#!/usr/bin/env python3
"""
Simple test for RAG system structure and imports without external dependencies.
"""
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test that all RAG modules can be imported."""
    print("🧪 Testing RAG module imports...")
    
    try:
        # Test model imports
        from app.models.connector import ConnectorMetadata, ConnectorResult, AuthRequirements
        from app.models.base import AuthType
        print("✅ Connector models import successfully")
        
        # Test exception imports
        from app.core.exceptions import RAGError, EmbeddingError
        print("✅ RAG exceptions import successfully")
        
        # Test sample data
        from app.data.sample_connectors import SAMPLE_CONNECTORS
        print(f"✅ Sample connectors loaded: {len(SAMPLE_CONNECTORS)} connectors")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_sample_connectors_structure():
    """Test the structure of sample connectors."""
    print("🧪 Testing sample connectors structure...")
    
    try:
        from app.data.sample_connectors import SAMPLE_CONNECTORS
        from app.models.base import AuthType
        
        # Test that we have connectors
        assert len(SAMPLE_CONNECTORS) > 0, "No sample connectors found"
        print(f"✅ Found {len(SAMPLE_CONNECTORS)} sample connectors")
        
        # Test connector structure
        for i, connector in enumerate(SAMPLE_CONNECTORS):
            assert hasattr(connector, 'name'), f"Connector {i} missing name"
            assert hasattr(connector, 'description'), f"Connector {i} missing description"
            assert hasattr(connector, 'category'), f"Connector {i} missing category"
            assert hasattr(connector, 'parameter_schema'), f"Connector {i} missing parameter_schema"
            assert hasattr(connector, 'auth_type'), f"Connector {i} missing auth_type"
            assert isinstance(connector.auth_type, AuthType), f"Connector {i} has invalid auth_type"
        
        print("✅ All connectors have valid structure")
        
        # Test categories
        categories = set(conn.category for conn in SAMPLE_CONNECTORS)
        print(f"✅ Categories: {', '.join(sorted(categories))}")
        
        # Test auth types
        auth_types = set(conn.auth_type.value for conn in SAMPLE_CONNECTORS)
        print(f"✅ Auth types: {', '.join(sorted(auth_types))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Sample connectors test failed: {e}")
        return False


def test_connector_schemas():
    """Test that connector schemas are valid JSON schemas."""
    print("🧪 Testing connector schemas...")
    
    try:
        from app.data.sample_connectors import SAMPLE_CONNECTORS
        
        for connector in SAMPLE_CONNECTORS:
            schema = connector.parameter_schema
            
            # Basic schema validation
            assert isinstance(schema, dict), f"Schema for {connector.name} is not a dict"
            assert 'type' in schema, f"Schema for {connector.name} missing 'type'"
            assert schema['type'] == 'object', f"Schema for {connector.name} type is not 'object'"
            
            if 'properties' in schema:
                assert isinstance(schema['properties'], dict), f"Properties for {connector.name} is not a dict"
            
            if 'required' in schema:
                assert isinstance(schema['required'], list), f"Required for {connector.name} is not a list"
        
        print("✅ All connector schemas are valid")
        return True
        
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False


def test_exceptions():
    """Test custom exceptions."""
    print("🧪 Testing custom exceptions...")
    
    try:
        from app.core.exceptions import RAGError, EmbeddingError, RAGException
        
        # Test exception hierarchy
        assert issubclass(RAGError, RAGException), "RAGError should inherit from RAGException"
        assert issubclass(EmbeddingError, RAGException), "EmbeddingError should inherit from RAGException"
        
        # Test exception creation
        rag_error = RAGError("Test RAG error")
        assert str(rag_error) == "Test RAG error"
        
        embedding_error = EmbeddingError("Test embedding error")
        assert str(embedding_error) == "Test embedding error"
        
        print("✅ Custom exceptions work correctly")
        return True
        
    except Exception as e:
        print(f"❌ Exception test failed: {e}")
        return False


def run_all_tests():
    """Run all simple tests."""
    print("🚀 Starting RAG System Structure Tests")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_sample_connectors_structure,
        test_connector_schemas,
        test_exceptions
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All structure tests passed!")
        print("✅ RAG system structure is valid")
        return True
    else:
        print("❌ Some tests failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)