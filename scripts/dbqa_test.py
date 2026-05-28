import os
import sys
# Ensure repo root is on sys.path when run from scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('APP_DB_BASE_PATH', 'D:/Repo/Repo5.5 3/Repo5.5/Database')
from backend.agent.db_qa_router import check_db_qa_intent, handle_db_qa_query

tests = [
    ('what is my department','what is my department'),
    ('what are all the departments in the system','what are all the departments in the system'),
]
for label, q in tests:
    intent, params = check_db_qa_intent(q)
    print('\nQuery:', q)
    print('Detected intent:', intent, 'params:', params)
    for case_label, uid in [('loginId as user_id','iris810'),('sentinel 0','0'),('numeric uid','104'),('empty','')]:
        r = handle_db_qa_query(q, intent, params, user_id=uid, role_id='0')
        found = r.get('db_found')
        text = r.get('response_text','')[:200].replace('\n',' ')
        print(f"  {case_label.ljust(20)}: found={found} | {text}")
