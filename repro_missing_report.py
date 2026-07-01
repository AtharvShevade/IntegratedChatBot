import asyncio
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
