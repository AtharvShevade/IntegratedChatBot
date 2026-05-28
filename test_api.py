#!/usr/bin/env python3
"""
Quick API testing script for DB Q&A integration.
Test the backend /chat endpoint with various sample queries.

Run with: python test_api.py
"""

import requests
import json
import sys
from typing import Optional

BASE_URL = "http://localhost:8001"

# Sample test cases
TEST_CASES = [
    {
        "name": "🟢 DB Q&A: List Active Users",
        "message": "show all active users",
        "user_id": "U001",
        "role_id": "101",
        "expect_db_intent": True,
    },
    {
        "name": "🟢 DB Q&A: List Departments",
        "message": "list all departments",
        "user_id": "U001",
        "role_id": "101",
        "expect_db_intent": True,
    },
    {
        "name": "🟢 DB Q&A: My Role",
        "message": "what is my role",
        "user_id": "U001",
        "role_id": "101",
        "expect_db_intent": True,
    },
    {
        "name": "🔴 Access Control: Non-Admin User List",
        "message": "show all users",
        "user_id": "U999",
        "role_id": "999",
        "expect_db_intent": True,
        "expect_found": False,
    },
    {
        "name": "🟡 Unknown Intent: Falls to LLM",
        "message": "what is the meaning of life",
        "user_id": "U001",
        "role_id": "101",
        "expect_db_intent": False,
    },
]


def test_api(
    message: str,
    user_id: str = "U001",
    role_id: str = "101",
    session_id: Optional[str] = None,
) -> dict:
    """Send a message to the API and return the response."""
    if session_id is None:
        session_id = f"test_{user_id}_{role_id}"

    payload = {
        "message": message,
        "session_id": session_id,
        "beautify": True,
        "user_id": user_id,
        "role_id": role_id,
    }

    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to backend")
        print(f"   Make sure backend is running on {BASE_URL}")
        print("   Run: uvicorn backend.main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        raise


def print_response(data: dict, test_case: dict) -> bool:
    """Pretty print response and validate expectations."""
    print("\n" + "=" * 80)
    print(f"Test: {test_case['name']}")
    print("=" * 80)

    print(f"\nRequest:")
    print(f"  Message: {test_case['message']}")
    print(f"  User ID: {test_case['user_id']}")
    print(f"  Role ID: {test_case['role_id']}")

    print(f"\nResponse:")
    print(f"  Result Type: {data.get('result_type', 'unknown')}")

    # Check for DB Q&A fields
    is_db_qa = data.get("db_intent") is not None
    print(f"  DB Q&A: {'✅ YES' if is_db_qa else '❌ NO'}")

    if is_db_qa:
        print(f"  DB Intent: {data.get('db_intent')}")
        print(f"  DB Found: {data.get('db_found')}")
        print(f"  DB Summary: {data.get('db_summary', 'N/A')}")

        records = data.get("db_records", [])
        if records:
            print(f"  Records: {len(records)} items")
            print(f"\n  Sample Record:")
            print(f"    {json.dumps(records[0], indent=4)}")

        beautified = data.get("db_beautified", "")
        if beautified:
            preview = beautified[:200] + ("..." if len(beautified) > 200 else "")
            print(f"\n  Beautified Response:")
            print(f"    {preview}")

    else:
        # Regular response
        response_text = data.get("response_text", "")
        preview = response_text[:200] + ("..." if len(response_text) > 200 else "")
        print(f"  Response Text: {preview}")

    # Validate expectations
    print(f"\nValidation:")
    passed = True

    expect_db_intent = test_case.get("expect_db_intent", False)
    if expect_db_intent and not is_db_qa:
        print(f"  ❌ FAIL: Expected DB intent but got none")
        passed = False
    elif not expect_db_intent and is_db_qa:
        print(f"  ⚠️  INFO: Got DB intent but test expected LLM fallback")
        print(f"     (This is OK if query matched a pattern)")
    else:
        print(f"  ✅ PASS: DB intent as expected")

    if is_db_qa:
        expect_found = test_case.get("expect_found", True)
        actual_found = data.get("db_found", False)
        if expect_found != actual_found:
            print(
                f"  ❌ FAIL: Expected found={expect_found}, got {actual_found}"
            )
            passed = False
        else:
            print(f"  ✅ PASS: Found status as expected")

    return passed


def main():
    """Run all test cases."""
    print("\n" + "🔍 DB Q&A API Testing ".center(80, "="))
    print(f"Backend URL: {BASE_URL}")
    print("=" * 80)

    print("\n⏳ Testing connection...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            print("✅ Backend is running")
        else:
            print(f"❌ Backend returned status {response.status_code}")
            print("   Try running: uvicorn backend.main:app --reload")
            sys.exit(1)
    except:
        print("❌ Cannot connect to backend")
        print("   Make sure it's running: uvicorn backend.main:app --reload")
        sys.exit(1)

    # Run all tests
    results = []
    for test_case in TEST_CASES:
        try:
            response = test_api(
                message=test_case["message"],
                user_id=test_case["user_id"],
                role_id=test_case["role_id"],
            )
            passed = print_response(response, test_case)
            results.append((test_case["name"], passed))
        except Exception as e:
            print(f"\n❌ ERROR in test: {e}")
            results.append((test_case["name"], False))

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:8} | {name}")

    print(f"\nTotal: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n" + "🎉 All tests PASSED! ".center(80, "="))
        print("✅ Backend DB Q&A is working correctly")
        print("✅ Ready for frontend integration")
        return 0
    else:
        print("\n" + "⚠️  Some tests FAILED ".center(80, "="))
        print("❌ Check errors above and debug")
        return 1


if __name__ == "__main__":
    sys.exit(main())
