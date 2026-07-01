from backend.tools.report_lookup import find_matching_reports
from backend.llm_extractor import _extract_search_terms, _extract_status_search_terms

queries = [
    'tell me the status',
    'status of a missing report',
    'what is the status of Atharv',
    'status of Atharv',
    'please check status',
    'i want status of cims raq'
]
for q in queries:
    stripped = _extract_search_terms(q)
    status_terms = _extract_status_search_terms(q)
    matches_stripped = find_matching_reports(stripped) if stripped else []
    matches_raw = find_matching_reports(q)
    print('Q:', q)
    print('  stripped:', repr(stripped), 'status_terms:', repr(status_terms))
    print('  matches_stripped:', [r.get('Name') for r in matches_stripped])
    print('  matches_raw:', [r.get('Name') for r in matches_raw])
    print('---')
