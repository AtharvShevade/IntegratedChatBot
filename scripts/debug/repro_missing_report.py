import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root, after move to scripts/debug/

from backend.agent import decide

async def main():
    res = await decide(
        'what is the status of Atharv',
        session_id=None,
        asp_session=None,
        login_id=None,
        user_id=None,
        role_id=None,
        conversation_history=[],
    )
    print(res)

asyncio.run(main())
