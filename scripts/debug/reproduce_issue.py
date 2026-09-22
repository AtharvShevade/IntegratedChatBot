import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root, after move to scripts/debug/

from backend.agent import decide

async def test(q, login_id=None):
    try:
        r = await decide(q, session_id=None, asp_session=None, login_id=login_id, user_id=None, role_id=None, conversation_history=None)
    except Exception as e:
        print('QUERY:', q, 'LOGIN:', login_id, 'ERROR:', repr(e))
        return
    print('QUERY:', q, 'LOGIN:', login_id)
    print(r)
    print('---')

async def main():
    await test('what is the status of Atharv', login_id=None)
    await test('what is the status of Atharv', login_id='john.doe')
    await test('status of this report does not exist', login_id='john.doe')
    await test('hello, how are you', login_id='john.doe')
    await test('tell me the status', login_id='john.doe')
    await test('status of a missing report', login_id=None)

asyncio.run(main())
