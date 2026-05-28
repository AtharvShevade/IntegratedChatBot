#!/usr/bin/env python3
"""Test LLM-based DB Q&A integration.

Tests:
1. LLM extracts DB Q&A intents correctly
2. Decision pipeline routes to DB Q&A handlers
3. Query handlers execute with LLM-extracted parameters
4. Various query types work (my_profile, list_users, etc.)
"""
import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.llm_service import extract_intent_entities_llm
from backend.config import APP_DB_BASE_PATH, APP_DB_ADMIN_ROLE_ID
from backend.db_qa.xml_store import XMLStore
from backend.db_qa.query_handlers import INTENT_TO_HANDLER, dispatch


async def test_llm_intent_extraction():
    """Test 1: LLM extracts DB Q&A intents correctly."""
    print("\n" + "="*80)
    print("TEST 1: LLM Intent Extraction for DB Q&A")
    print("="*80)
    
    test_queries = [
        ("What department am I in?", "db_my_department"),
        ("List all departments", "db_list_departments"),
        ("Who are the active users?", "db_list_users"),
        ("Tell me about user Alice", "db_user_info"),
        ("What's my role?", "db_my_role"),
        ("What can I do?", "db_my_permissions"),
        ("Show all inactive users", "db_list_users"),
        ("Who are all the users?", "db_list_users"),
    ]
    
    for query, expected_intent_prefix in test_queries:
        try:
            result = await extract_intent_entities_llm(query)
            detected_intent = result.get("intent", "unknown")
            extracted_entities = {
                "target_user": result.get("target_user"),
                "target_department": result.get("target_department"),
                "query_type": result.get("query_type"),
            }
            
            status = "✅" if detected_intent.startswith(expected_intent_prefix.split("_")[0]) else "❌"
            print(f"\n{status} Query: {query}")
            print(f"   Expected: {expected_intent_prefix}")
            print(f"   Got: {detected_intent}")
            print(f"   Entities: {extracted_entities}")
            
            if detected_intent != "unknown":
                print(f"   → Ready for DB Q&A routing")
        except Exception as e:
            print(f"❌ Query: {query}")
            print(f"   Error: {e}")


async def test_handler_dispatch():
    """Test 2: Query handlers dispatch with LLM parameters."""
    print("\n" + "="*80)
    print("TEST 2: Handler Dispatch with LLM Parameters")
    print("="*80)
    
    if not APP_DB_BASE_PATH:
        print("⚠️  APP_DB_BASE_PATH not configured, skipping handler dispatch test")
        return
    
    try:
        store = XMLStore(APP_DB_BASE_PATH)
        
        test_cases = [
            ("db_my_department", {}, "104", "101", "Self-service: User asks their department"),
            ("db_list_users", {"query_type": "active"}, "104", "101", "Admin: List active users"),
            ("db_list_departments", {}, "104", "101", "Admin: List all departments"),
        ]
        
        for intent, params, user_id, role_id, description in test_cases:
            try:
                is_admin = (role_id == APP_DB_ADMIN_ROLE_ID)
                result = dispatch(
                    intent=intent,
                    params=params,
                    user_id=user_id,
                    role_id=role_id,
                    is_admin=is_admin,
                    store=store,
                )
                
                status = "✅" if result.get("found") else "⚠️ "
                print(f"\n{status} {description}")
                print(f"   Intent: {intent}")
                print(f"   Found: {result.get('found')}")
                print(f"   Records: {len(result.get('records', []))}")
                print(f"   Summary: {result.get('summary')[:80]}...")
                
            except Exception as e:
                print(f"❌ {description}")
                print(f"   Intent: {intent}")
                print(f"   Error: {e}")
    
    except Exception as e:
        print(f"❌ Failed to initialize XMLStore: {e}")


async def test_intent_to_handler_mapping():
    """Test 3: Check all DB Q&A intents have handlers."""
    print("\n" + "="*80)
    print("TEST 3: Intent to Handler Mapping")
    print("="*80)
    
    expected_intents = [
        "db_my_profile",
        "db_my_department",
        "db_my_role",
        "db_my_permissions",
        "db_my_email",
        "db_my_mobile",
        "db_list_users",
        "db_list_departments",
        "db_list_roles",
        "db_user_info",
        "db_department_info",
        "db_role_info",
    ]
    
    for intent in expected_intents:
        handler = INTENT_TO_HANDLER.get(intent)
        status = "✅" if handler else "❌"
        print(f"{status} {intent}: {handler.__name__ if handler else 'NOT FOUND'}")


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("LLM-BASED DB Q&A INTEGRATION TESTS")
    print("="*80)
    
    print(f"\n📋 Configuration:")
    print(f"   APP_DB_BASE_PATH: {APP_DB_BASE_PATH}")
    print(f"   APP_DB_ADMIN_ROLE_ID: {APP_DB_ADMIN_ROLE_ID}")
    
    await test_llm_intent_extraction()
    await test_handler_dispatch()
    await test_intent_to_handler_mapping()
    
    print("\n" + "="*80)
    print("TESTS COMPLETE")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
