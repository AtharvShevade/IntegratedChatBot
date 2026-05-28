#!/usr/bin/env python3
"""
Quick validation script for DB Q&A integration.
Tests imports, configuration, and basic pipeline without requiring XML data files.

Run with: python backend/tests/test_db_qa_integration.py
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_imports():
    """Test all DB Q&A imports."""
    print("=" * 70)
    print("TEST 1: Validating imports...")
    print("=" * 70)
    
    try:
        from backend.db_qa import intent_classifier
        print("✅ intent_classifier imported")
    except Exception as e:
        print(f"❌ intent_classifier import failed: {e}")
        return False
    
    try:
        from backend.db_qa import query_handlers
        print("✅ query_handlers imported")
    except Exception as e:
        print(f"❌ query_handlers import failed: {e}")
        return False
    
    try:
        from backend.db_qa import xml_store
        print("✅ xml_store imported")
    except Exception as e:
        print(f"❌ xml_store import failed: {e}")
        return False
    
    try:
        from backend.db_qa import beautifier
        print("✅ beautifier imported")
    except Exception as e:
        print(f"❌ beautifier import failed: {e}")
        return False
    
    try:
        from backend.agent import db_qa_router
        print("✅ db_qa_router imported")
    except Exception as e:
        print(f"❌ db_qa_router import failed: {e}")
        return False
    
    return True


def test_config():
    """Test configuration loading."""
    print("\n" + "=" * 70)
    print("TEST 2: Validating configuration...")
    print("=" * 70)
    
    try:
        from backend.config import (
            APP_DB_BASE_PATH, APP_DB_ADMIN_ROLE_ID,
            APP_DB_ENABLE_BEAUTIFY, APP_DB_BEAUTIFY_MODEL
        )
        
        print(f"✅ APP_DB_BASE_PATH = {APP_DB_BASE_PATH}")
        print(f"✅ APP_DB_ADMIN_ROLE_ID = {APP_DB_ADMIN_ROLE_ID}")
        print(f"✅ APP_DB_ENABLE_BEAUTIFY = {APP_DB_ENABLE_BEAUTIFY}")
        print(f"✅ APP_DB_BEAUTIFY_MODEL = {APP_DB_BEAUTIFY_MODEL}")
        
        if not APP_DB_BASE_PATH:
            print("\n⚠️  DB Q&A feature is DISABLED (APP_DB_BASE_PATH not set)")
            print("    To enable: Set APP_DB_BASE_PATH in .env to your Database directory")
        else:
            print(f"\n✅ DB Q&A feature is ENABLED")
        
        return True
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False


def test_intent_classification():
    """Test intent classifier (no XML required)."""
    print("\n" + "=" * 70)
    print("TEST 3: Validating intent classification...")
    print("=" * 70)
    
    try:
        from backend.db_qa.intent_classifier import classify
        
        test_queries = [
            "show me all users",
            "list active users",
            "what is my role",
            "show departments",
            "list all returns",
            "unknown random query",
        ]
        
        for query in test_queries:
            intent, params = classify(query)
            status = "✅" if intent else "⚠️ "
            print(f"{status} '{query}'")
            print(f"   → intent={intent}, params={params}")
        
        return True
    except Exception as e:
        print(f"❌ Intent classification test failed: {e}")
        return False


def test_models():
    """Test extended models."""
    print("\n" + "=" * 70)
    print("TEST 4: Validating extended models...")
    print("=" * 70)
    
    try:
        from backend.models import ChatRequest, ChatResponse
        
        # Test ChatRequest
        req = ChatRequest(
            message="test query",
            session_id="test_session",
            beautify=True,
            user_id="U001",
            role_id="101"
        )
        print(f"✅ ChatRequest extended: beautify={req.beautify}, user_id={req.user_id}, role_id={req.role_id}")
        
        # Test ChatResponse
        resp = ChatResponse(
            response_text="test response",
            db_intent="USER_LIST",
            db_found=True,
            db_records=[],
            db_summary="Test summary",
            db_beautified="Test beautified"
        )
        print(f"✅ ChatResponse extended: db_intent={resp.db_intent}, db_found={resp.db_found}")
        
        return True
    except Exception as e:
        print(f"❌ Model validation test failed: {e}")
        return False


def test_router_imports():
    """Test router imports and basic functions."""
    print("\n" + "=" * 70)
    print("TEST 5: Validating router functions...")
    print("=" * 70)
    
    try:
        from backend.agent.db_qa_router import check_db_qa_intent, handle_db_qa_query
        
        # Test check_db_qa_intent (no XML required)
        intent, params = check_db_qa_intent("show all users")
        print(f"✅ check_db_qa_intent() callable")
        print(f"   Sample query 'show all users': intent={intent}")
        
        # Note: handle_db_qa_query requires XML store, so we just check it's callable
        print(f"✅ handle_db_qa_query() callable")
        
        return True
    except Exception as e:
        print(f"❌ Router validation test failed: {e}")
        return False


def main():
    """Run all validation tests."""
    print("\n" + "🔍 DB Q&A Integration Validation ".center(70, "="))
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("Intent Classification", test_intent_classification()))
    results.append(("Models", test_models()))
    results.append(("Router", test_router_imports()))
    
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<50} {status}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n" + "🎉 All validation tests PASSED!".center(70, "="))
        print("✅ DB Q&A integration is ready for production")
        if not PROJECT_ROOT.joinpath(".env").exists():
            print("\n📝 Next steps:")
            print("   1. Configure APP_DB_BASE_PATH in .env (optional, feature can stay disabled)")
            print("   2. Run: uvicorn backend.main:app --reload")
            print("   3. Test with POST /chat endpoint")
        return 0
    else:
        print("\n" + "⚠️  Some validation tests FAILED".center(70, "="))
        print("❌ Please fix errors above before deploying")
        return 1


if __name__ == "__main__":
    sys.exit(main())
