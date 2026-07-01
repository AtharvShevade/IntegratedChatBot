from backend.tools.report_lookup import find_matching_reports, fuzzy_report_suggestions, get_report_status_fast
for q in ['Atharv', 'mongo', 'status of Atharv', 'status of mongo', 'CIMS RAQ', 'CRILC', 'ror']:
    print('QUERY:', q)
    print('MATCHES:', [m.get('Name') for m in find_matching_reports(q)])
    print('STATUS:', get_report_status_fast(q))
    print('---')
